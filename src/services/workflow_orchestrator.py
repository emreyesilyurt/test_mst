"""
Workflow Orchestrator Service for master_electronics.

This service orchestrates the workflow for getting data from BigQuery and delegating
tasks to either automation or manual processes based on configurable criteria.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from src.db.connections import get_supabase_async_engine
from src.db.services.bigquery_service import BigQueryService
from src.db.models import (
    Product, PartNumber, Manufacturer, Category, Attribute,
    ProductAttribute, ProductExtra, DocumentMedia, ProductSeller,
    ManualTask, AutomationTask
)
from src.tasks.automation.automate_tasks import TaskAutomator
from src.services.manual_imputation_service import ManualImputationService


class TaskType(Enum):
    """Task type enumeration."""
    AUTOMATION = "automation"
    MANUAL = "manual"


class TaskPriority(Enum):
    """Task priority enumeration."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class WorkflowConfig:
    """Configuration for workflow orchestration."""
    # Automation criteria
    automation_priority_threshold: float = 0.8
    automation_max_concurrent: int = 5
    automation_retry_attempts: int = 3
    
    # Manual task criteria
    manual_priority_threshold: float = 0.5
    manual_batch_size: int = 50
    
    # Fallback criteria
    automation_failure_to_manual: bool = True
    max_automation_failures: int = 3
    
    # Processing limits
    max_daily_tasks: int = 1000
    max_batch_size: int = 100


@dataclass
class TaskDecision:
    """Decision result for task delegation."""
    task_type: TaskType
    priority: TaskPriority
    reason: str
    confidence: float
    metadata: Dict[str, Any]


class WorkflowOrchestrator:
    """
    Main orchestrator for workflow management.
    
    This class handles:
    1. Fetching data from BigQuery
    2. Analyzing and deciding task delegation
    3. Creating automation or manual tasks
    4. Monitoring and fallback handling
    """
    
    def __init__(self, config: Optional[WorkflowConfig] = None):
        self.config = config or WorkflowConfig()
        self.async_engine = get_supabase_async_engine()
        self.AsyncSessionLocal = async_sessionmaker(bind=self.async_engine, expire_on_commit=False)
        self.bq_service = BigQueryService()
        self.task_automator = TaskAutomator(silent=True)
        self.manual_service = ManualImputationService()
        
    async def orchestrate_workflow(
        self,
        batch_id: Optional[str] = None,
        limit: int = 100,
        priority_threshold: Optional[float] = None,
        force_task_type: Optional[TaskType] = None
    ) -> Dict[str, Any]:
        """
        Main workflow orchestration method.
        
        Args:
            batch_id: Optional batch identifier
            limit: Maximum number of records to process
            priority_threshold: Override priority threshold
            force_task_type: Force all tasks to specific type (for testing)
            
        Returns:
            Dictionary with workflow results
        """
        if not batch_id:
            batch_id = f"workflow_{int(time.time())}"
        
        workflow_start = time.time()
        
        try:
            # Step 1: Fetch data from BigQuery
            print(f"🔄 Starting workflow orchestration (Batch: {batch_id})")
            bq_data = await self._fetch_bigquery_data(limit, priority_threshold)
            
            if not bq_data:
                return {
                    'status': 'no_data',
                    'message': 'No data found in BigQuery',
                    'batch_id': batch_id
                }
            
            print(f"📊 Fetched {len(bq_data)} records from BigQuery")
            
            # Step 2: Analyze and make task decisions
            task_decisions = await self._analyze_and_decide_tasks(bq_data, force_task_type)
            
            # Step 3: Group tasks by type
            automation_tasks = [d for d in task_decisions if d.task_type == TaskType.AUTOMATION]
            manual_tasks = [d for d in task_decisions if d.task_type == TaskType.MANUAL]
            
            print(f"📋 Task decisions: {len(automation_tasks)} automation, {len(manual_tasks)} manual")
            
            # Step 4: Execute tasks
            results = {
                'batch_id': batch_id,
                'total_records': len(bq_data),
                'automation_tasks': len(automation_tasks),
                'manual_tasks': len(manual_tasks),
                'automation_results': {},
                'manual_results': {},
                'processing_time': 0,
                'status': 'in_progress'
            }
            
            # Execute automation tasks
            if automation_tasks:
                automation_results = await self._execute_automation_tasks(
                    automation_tasks, batch_id
                )
                results['automation_results'] = automation_results
            
            # Execute manual tasks
            if manual_tasks:
                manual_results = await self._execute_manual_tasks(
                    manual_tasks, batch_id
                )
                results['manual_results'] = manual_results
            
            # Step 5: Handle fallbacks (automation failures to manual)
            if self.config.automation_failure_to_manual:
                fallback_results = await self._handle_automation_fallbacks(
                    results.get('automation_results', {}), batch_id
                )
                if fallback_results:
                    results['fallback_results'] = fallback_results
            
            # Calculate final results
            results['processing_time'] = time.time() - workflow_start
            results['status'] = 'completed'
            
            # Log summary
            await self._log_workflow_summary(results)
            
            return results
            
        except Exception as e:
            print(f"❌ Workflow orchestration failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'batch_id': batch_id,
                'processing_time': time.time() - workflow_start
            }
    
    async def _fetch_bigquery_data(
        self, 
        limit: int, 
        priority_threshold: Optional[float]
    ) -> List[Dict[str, Any]]:
        """Fetch data from BigQuery with filtering."""
        try:
            # Use priority threshold from config if not provided
            threshold = priority_threshold or self.config.automation_priority_threshold
            
            # Fetch data using BigQuery service
            df = self.bq_service.fetch_all_data_sorted(
                limit=limit,
                priority_threshold=threshold
            )
            
            if df.empty:
                return []
            
            # Convert DataFrame to list of dictionaries
            return df.to_dict('records')
            
        except Exception as e:
            print(f"Error fetching BigQuery data: {str(e)}")
            return []
    
    async def _analyze_and_decide_tasks(
        self, 
        bq_data: List[Dict[str, Any]], 
        force_task_type: Optional[TaskType] = None
    ) -> List[TaskDecision]:
        """
        Analyze BigQuery data and decide task delegation.
        
        Args:
            bq_data: List of BigQuery records
            force_task_type: Force all tasks to specific type
            
        Returns:
            List of task decisions
        """
        decisions = []
        
        async with self.AsyncSessionLocal() as session:
            for record in bq_data:
                try:
                    decision = await self._make_task_decision(record, session, force_task_type)
                    decisions.append(decision)
                except Exception as e:
                    print(f"Error making decision for record {record.get('pn', 'unknown')}: {str(e)}")
                    # Default to manual task on error
                    decisions.append(TaskDecision(
                        task_type=TaskType.MANUAL,
                        priority=TaskPriority.LOW,
                        reason=f"Error in decision making: {str(e)}",
                        confidence=0.0,
                        metadata={'record': record, 'error': str(e)}
                    ))
        
        return decisions
    
    async def _make_task_decision(
        self, 
        record: Dict[str, Any], 
        session: AsyncSession,
        force_task_type: Optional[TaskType] = None
    ) -> TaskDecision:
        """
        Make decision for a single record.
        
        Decision criteria (updated logic):
        1. Force type if specified
        2. Check if part number already exists with recent failures
        3. Check data completeness - HIGH completeness → Manual (needs human review)
        4. Check priority score and manufacturer reliability for automation
        5. Default to automation for incomplete data (automation fills gaps well)
        """
        if force_task_type:
            return TaskDecision(
                task_type=force_task_type,
                priority=TaskPriority.MEDIUM,
                reason="Forced task type",
                confidence=1.0,
                metadata={'record': record}
            )
        
        part_number = record.get('pn', '')
        manufacturer = record.get('manufacturer', '')
        priority_score = record.get('priority_score', {}).get('score', 0.0) if isinstance(record.get('priority_score'), dict) else 0.0
        
        # Check if part number already exists
        existing_pn = await session.scalar(
            select(PartNumber).where(PartNumber.name == part_number)
        )
        
        if existing_pn:
            # Check recent automation failures for this part number
            recent_failures = await session.scalar(
                select(func.count(AutomationTask.id)).where(
                    and_(
                        AutomationTask.product_id == existing_pn.product_id,
                        AutomationTask.current_status == 'failed',
                        AutomationTask.created_date >= datetime.now() - timedelta(days=7)
                    )
                )
            )
            
            if recent_failures >= self.config.max_automation_failures:
                return TaskDecision(
                    task_type=TaskType.MANUAL,
                    priority=TaskPriority.HIGH,
                    reason=f"Too many recent automation failures ({recent_failures})",
                    confidence=0.9,
                    metadata={'record': record, 'existing_pn': True, 'failures': recent_failures}
                )
        
        # Calculate data completeness first (primary decision factor)
        completeness_score = self._calculate_data_completeness(record)
        
        # HIGH completeness (≥0.8) → Manual (complex data needs human review)
        if completeness_score >= 0.8:
            return TaskDecision(
                task_type=TaskType.MANUAL,
                priority=TaskPriority.HIGH,
                reason=f"High data completeness ({completeness_score:.2f}) - needs human review",
                confidence=completeness_score,
                metadata={
                    'record': record,
                    'completeness_score': completeness_score,
                    'priority_score': priority_score,
                    'decision_factor': 'high_completeness'
                }
            )
        
        # MEDIUM completeness (0.5-0.8) → Check other factors
        elif completeness_score >= 0.5:
            # Check manufacturer reliability
            manufacturer_score = await self._get_manufacturer_reliability(manufacturer, session)
            
            # If manufacturer is unreliable OR priority is very low → Manual
            if manufacturer_score < 0.4 or priority_score < 0.3:
                return TaskDecision(
                    task_type=TaskType.MANUAL,
                    priority=TaskPriority.MEDIUM,
                    reason=f"Medium completeness ({completeness_score:.2f}) with low reliability/priority",
                    confidence=0.7,
                    metadata={
                        'record': record,
                        'completeness_score': completeness_score,
                        'manufacturer_score': manufacturer_score,
                        'priority_score': priority_score,
                        'decision_factor': 'medium_completeness_low_confidence'
                    }
                )
            else:
                # Good manufacturer and decent priority → Automation
                return TaskDecision(
                    task_type=TaskType.AUTOMATION,
                    priority=TaskPriority.MEDIUM,
                    reason=f"Medium completeness ({completeness_score:.2f}) with good manufacturer/priority",
                    confidence=0.6 + (manufacturer_score * 0.2) + (priority_score * 0.2),
                    metadata={
                        'record': record,
                        'completeness_score': completeness_score,
                        'manufacturer_score': manufacturer_score,
                        'priority_score': priority_score,
                        'decision_factor': 'medium_completeness_good_confidence'
                    }
                )
        
        # LOW completeness (<0.5) → Automation (automation is good at filling gaps)
        else:
            # Check if priority is extremely low
            if priority_score < 0.2:
                return TaskDecision(
                    task_type=TaskType.MANUAL,
                    priority=TaskPriority.LOW,
                    reason=f"Very low priority ({priority_score}) despite low completeness",
                    confidence=0.6,
                    metadata={
                        'record': record,
                        'completeness_score': completeness_score,
                        'priority_score': priority_score,
                        'decision_factor': 'very_low_priority'
                    }
                )
            else:
                # Low completeness → Perfect for automation
                return TaskDecision(
                    task_type=TaskType.AUTOMATION,
                    priority=TaskPriority.HIGH if priority_score >= 0.6 else TaskPriority.MEDIUM,
                    reason=f"Low completeness ({completeness_score:.2f}) - automation excels at filling gaps",
                    confidence=0.8,  # High confidence that automation can handle incomplete data
                    metadata={
                        'record': record,
                        'completeness_score': completeness_score,
                        'priority_score': priority_score,
                        'decision_factor': 'low_completeness_automation_preferred'
                    }
                )
    
    async def _get_manufacturer_reliability(
        self, 
        manufacturer: str, 
        session: AsyncSession
    ) -> float:
        """
        Calculate manufacturer reliability score based on historical success.
        
        Args:
            manufacturer: Manufacturer name
            session: Database session
            
        Returns:
            Reliability score between 0.0 and 1.0
        """
        try:
            # Get manufacturer record
            manufacturer_record = await session.scalar(
                select(Manufacturer).where(Manufacturer.name == manufacturer)
            )
            
            if not manufacturer_record:
                return 0.5  # Default score for unknown manufacturers
            
            # Count successful vs failed automation tasks for this manufacturer
            success_count = await session.scalar(
                select(func.count(AutomationTask.id)).where(
                    and_(
                        AutomationTask.product_id.in_(
                            select(Product.product_id).where(
                                Product.manufacturer_id == manufacturer_record.id
                            )
                        ),
                        AutomationTask.current_status == 'completed'
                    )
                )
            ) or 0
            
            failure_count = await session.scalar(
                select(func.count(AutomationTask.id)).where(
                    and_(
                        AutomationTask.product_id.in_(
                            select(Product.product_id).where(
                                Product.manufacturer_id == manufacturer_record.id
                            )
                        ),
                        AutomationTask.current_status == 'failed'
                    )
                )
            ) or 0
            
            total_tasks = success_count + failure_count
            
            if total_tasks == 0:
                return 0.6  # Default score for manufacturers with no history
            
            # Calculate success rate with smoothing
            success_rate = (success_count + 1) / (total_tasks + 2)  # Laplace smoothing
            
            return min(success_rate, 1.0)
            
        except Exception as e:
            print(f"Error calculating manufacturer reliability: {str(e)}")
            return 0.5
    
    def _calculate_data_completeness(self, record: Dict[str, Any]) -> float:
        """
        Calculate data completeness score for a record.
        
        Args:
            record: BigQuery record
            
        Returns:
            Completeness score between 0.0 and 1.0
        """
        try:
            # Define important fields and their weights
            important_fields = {
                'pn': 0.3,
                'manufacturer': 0.2,
                'category': 0.1,
                'description': 0.1,
                'specs': 0.15,
                'docs': 0.1,
                'images': 0.05
            }
            
            total_weight = 0.0
            present_weight = 0.0
            
            for field, weight in important_fields.items():
                total_weight += weight
                
                value = record.get(field)
                if value is not None:
                    if isinstance(value, str) and value.strip():
                        present_weight += weight
                    elif isinstance(value, (list, dict)) and len(value) > 0:
                        present_weight += weight
                    elif isinstance(value, (int, float)) and value != 0:
                        present_weight += weight
            
            return present_weight / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            print(f"Error calculating data completeness: {str(e)}")
            return 0.5
    
    async def _execute_automation_tasks(
        self, 
        automation_decisions: List[TaskDecision], 
        batch_id: str
    ) -> Dict[str, Any]:
        """Execute automation tasks with concurrency control."""
        results = {
            'total': len(automation_decisions),
            'successful': 0,
            'failed': 0,
            'task_ids': [],
            'errors': []
        }
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.config.automation_max_concurrent)
        
        async def process_single_automation(decision: TaskDecision):
            async with semaphore:
                try:
                    record = decision.metadata['record']
                    part_number = record.get('pn', '')
                    
                    # Use existing automation system
                    result = await self.task_automator.test_digikey_search(part_number, batch_id)
                    
                    if result.get('status') == 'success':
                        results['successful'] += 1
                        # Get the task ID if available
                        if hasattr(self.task_automator, 'current_task') and self.task_automator.current_task:
                            results['task_ids'].append(self.task_automator.current_task.id)
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'part_number': part_number,
                            'error': result.get('message', 'Unknown error')
                        })
                    
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'part_number': decision.metadata.get('record', {}).get('pn', 'unknown'),
                        'error': str(e)
                    })
        
        # Execute all automation tasks
        tasks = [process_single_automation(decision) for decision in automation_decisions]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def _execute_manual_tasks(
        self, 
        manual_decisions: List[TaskDecision], 
        batch_id: str
    ) -> Dict[str, Any]:
        """Execute manual tasks by creating manual task records."""
        results = {
            'total': len(manual_decisions),
            'successful': 0,
            'failed': 0,
            'task_ids': [],
            'errors': []
        }
        
        async with self.AsyncSessionLocal() as session:
            for decision in manual_decisions:
                try:
                    record = decision.metadata['record']
                    part_number = record.get('pn', '')
                    manufacturer = record.get('manufacturer', '')
                    
                    # Get or create part number record
                    pn_record = await session.scalar(
                        select(PartNumber).where(PartNumber.name == part_number)
                    )
                    
                    if not pn_record:
                        # Create new part number
                        pn_record = PartNumber(name=part_number)
                        session.add(pn_record)
                        await session.flush()
                        pn_record.product_id = pn_record.id
                    
                    # Get or create product record
                    product = await session.scalar(
                        select(Product).where(Product.part_number == pn_record.product_id)
                    )
                    
                    if not product:
                        # Create new product
                        product = Product(part_number=pn_record.product_id)
                        session.add(product)
                        await session.flush()
                    
                    # Create manual task
                    manual_task = ManualTask()
                    manual_task.initialize_task(
                        product_id=product.product_id,
                        editor='workflow_orchestrator',
                        batch_id=batch_id
                    )
                    manual_task.task_type = 'workflow_generated'
                    manual_task.note = f"Generated by workflow orchestrator. Reason: {decision.reason}"
                    
                    # Store BigQuery data in edited_fields for reference
                    manual_task.edited_fields = {
                        'bigquery_data': record,
                        'decision_metadata': decision.metadata,
                        'priority': decision.priority.value,
                        'confidence': decision.confidence
                    }
                    
                    session.add(manual_task)
                    await session.flush()
                    
                    results['successful'] += 1
                    results['task_ids'].append(manual_task.id)
                    
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'part_number': decision.metadata.get('record', {}).get('pn', 'unknown'),
                        'error': str(e)
                    })
            
            await session.commit()
        
        return results
    
    async def _handle_automation_fallbacks(
        self, 
        automation_results: Dict[str, Any], 
        batch_id: str
    ) -> Optional[Dict[str, Any]]:
        """Handle automation failures by creating manual tasks."""
        if not automation_results.get('errors'):
            return None
        
        fallback_results = {
            'total': len(automation_results['errors']),
            'successful': 0,
            'failed': 0,
            'task_ids': []
        }
        
        async with self.AsyncSessionLocal() as session:
            for error_info in automation_results['errors']:
                try:
                    part_number = error_info['part_number']
                    error_message = error_info['error']
                    
                    # Get or create part number record
                    pn_record = await session.scalar(
                        select(PartNumber).where(PartNumber.name == part_number)
                    )
                    
                    if not pn_record:
                        pn_record = PartNumber(name=part_number)
                        session.add(pn_record)
                        await session.flush()
                        pn_record.product_id = pn_record.id
                    
                    # Get or create product record
                    product = await session.scalar(
                        select(Product).where(Product.part_number == pn_record.product_id)
                    )
                    
                    if not product:
                        product = Product(part_number=pn_record.product_id)
                        session.add(product)
                        await session.flush()
                    
                    # Create fallback manual task
                    manual_task = ManualTask()
                    manual_task.initialize_task(
                        product_id=product.product_id,
                        editor='automation_fallback',
                        batch_id=f"{batch_id}_fallback"
                    )
                    manual_task.task_type = 'automation_fallback'
                    manual_task.note = f"Automation failed: {error_message}"
                    manual_task.edited_fields = {
                        'fallback_reason': error_message,
                        'original_batch_id': batch_id
                    }
                    
                    session.add(manual_task)
                    await session.flush()
                    
                    fallback_results['successful'] += 1
                    fallback_results['task_ids'].append(manual_task.id)
                    
                except Exception as e:
                    fallback_results['failed'] += 1
                    print(f"Error creating fallback task for {error_info.get('part_number', 'unknown')}: {str(e)}")
            
            await session.commit()
        
        return fallback_results
    
    async def _log_workflow_summary(self, results: Dict[str, Any]):
        """Log workflow summary for monitoring."""
        print(f"\n🎉 Workflow Summary (Batch: {results['batch_id']})")
        print(f"📊 Total Records: {results['total_records']}")
        print(f"🤖 Automation Tasks: {results['automation_tasks']}")
        print(f"👤 Manual Tasks: {results['manual_tasks']}")
        
        if results.get('automation_results'):
            auto_results = results['automation_results']
            print(f"   ✅ Automation Success: {auto_results['successful']}")
            print(f"   ❌ Automation Failed: {auto_results['failed']}")
        
        if results.get('manual_results'):
            manual_results = results['manual_results']
            print(f"   ✅ Manual Tasks Created: {manual_results['successful']}")
            print(f"   ❌ Manual Creation Failed: {manual_results['failed']}")
        
        if results.get('fallback_results'):
            fallback_results = results['fallback_results']
            print(f"🔄 Fallback Tasks Created: {fallback_results['successful']}")
        
        print(f"⏱️  Processing Time: {results['processing_time']:.2f} seconds")
        print(f"✅ Status: {results['status']}")
    
    async def get_workflow_status(self, batch_id: str) -> Dict[str, Any]:
        """Get status of a workflow batch."""
        async with self.AsyncSessionLocal() as session:
            try:
                # Get automation tasks for this batch
                automation_tasks = await session.execute(
                    select(AutomationTask).where(AutomationTask.batch_id == batch_id)
                )
                auto_tasks = automation_tasks.scalars().all()
                
                # Get manual tasks for this batch
                manual_tasks = await session.execute(
                    select(ManualTask).where(ManualTask.batch_id == batch_id)
                )
                manual_task_list = manual_tasks.scalars().all()
                
                # Count statuses
                auto_status_counts = {}
                for task in auto_tasks:
                    status = task.current_status
                    auto_status_counts[status] = auto_status_counts.get(status, 0) + 1
                
                manual_status_counts = {}
                for task in manual_task_list:
                    status = task.current_status
                    manual_status_counts[status] = manual_status_counts.get(status, 0) + 1
                
                return {
                    'batch_id': batch_id,
                    'automation_tasks': {
                        'total': len(auto_tasks),
                        'status_breakdown': auto_status_counts
                    },
                    'manual_tasks': {
                        'total': len(manual_task_list),
                        'status_breakdown': manual_status_counts
                    },
                    'overall_status': self._calculate_overall_status(auto_status_counts, manual_status_counts)
                }
                
            except Exception as e:
                return {
                    'batch_id': batch_id,
                    'error': str(e),
                    'status': 'error'
                }
    
    def _calculate_overall_status(
        self, 
        auto_status_counts: Dict[str, int], 
        manual_status_counts: Dict[str, int]
    ) -> str:
        """Calculate overall workflow status."""
        total_auto = sum(auto_status_counts.values())
        total_manual = sum(manual_status_counts.values())
        total_tasks = total_auto + total_manual
        
        if total_tasks == 0:
            return 'no_tasks'
        
        completed_auto = auto_status_counts.get('completed', 0)
        completed_manual = manual_status_counts.get('completed', 0)
        failed_auto = auto_status_counts.get('failed', 0)
        failed_manual = manual_status_counts.get('failed', 0)
        
        total_completed = completed_auto + completed_manual
        total_failed = failed_auto + failed_manual
        
        if total_completed == total_tasks:
            return 'completed'
        elif total_failed == total_tasks:
            return 'failed'
        elif total_completed + total_failed == total_tasks:
            return 'completed_with_failures'
        else:
            return 'in_progress'
    
    async def get_pending_manual_tasks(
        self, 
        limit: int = 50,
        priority: Optional[TaskPriority] = None
    ) -> List[Dict[str, Any]]:
        """Get pending manual tasks for processing."""
        async with self.AsyncSessionLocal() as session:
            try:
                query = select(ManualTask).where(
                    ManualTask.current_status.in_(['initialized', 'processing'])
                ).order_by(ManualTask.created_date.desc()).limit(limit)
                
                result = await session.execute(query)
                tasks = result.scalars().all()
                
                task_list = []
                for task in tasks:
                    # Get part number info
                    product = await session.scalar(
                        select(Product).where(Product.product_id == task.product_id)
                    )
                    
                    part_number = None
                    if product:
                        pn_record = await session.scalar(
                            select(PartNumber).where(PartNumber.product_id == product.part_number)
                        )
                        part_number = pn_record.name if pn_record else None
                    
                    task_info = {
                        'task_id': task.id,
                        'product_id': task.product_id,
                        'part_number': part_number,
                        'batch_id': task.batch_id,
                        'task_type': task.task_type,
                        'current_status': task.current_status,
                        'editor': task.editor,
                        'note': task.note,
                        'created_date': task.created_date,
                        'priority': task.edited_fields.get('priority', 'medium') if task.edited_fields else 'medium',
                        'confidence': task.edited_fields.get('confidence', 0.5) if task.edited_fields else 0.5
                    }
                    
                    # Filter by priority if specified
                    if priority is None or task_info['priority'] == priority.value:
                        task_list.append(task_info)
                
                return task_list
                
            except Exception as e:
                print(f"Error getting pending manual tasks: {str(e)}")
                return []


# Convenience functions for easy usage
async def run_workflow(
    limit: int = 100,
    priority_threshold: Optional[float] = None,
    force_automation: bool = False,
    force_manual: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to run the workflow orchestration.
    
    Args:
        limit: Maximum number of records to process
        priority_threshold: Override priority threshold
        force_automation: Force all tasks to automation
        force_manual: Force all tasks to manual
        
    Returns:
        Workflow results
    """
    orchestrator = WorkflowOrchestrator()
    
    force_type = None
    if force_automation:
        force_type = TaskType.AUTOMATION
    elif force_manual:
        force_type = TaskType.MANUAL
    
    return await orchestrator.orchestrate_workflow(
        limit=limit,
        priority_threshold=priority_threshold,
        force_task_type=force_type
    )


async def get_workflow_status(batch_id: str) -> Dict[str, Any]:
    """
    Convenience function to get workflow status.
    
    Args:
        batch_id: Batch ID to check status for
        
    Returns:
        Workflow status information
    """
    orchestrator = WorkflowOrchestrator()
    return await orchestrator.get_workflow_status(batch_id)


async def get_pending_manual_tasks(
    limit: int = 50,
    priority: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to get pending manual tasks.
    
    Args:
        limit: Maximum number of tasks to return
        priority: Filter by priority ('high', 'medium', 'low')
        
    Returns:
        List of pending manual tasks
    """
    orchestrator = WorkflowOrchestrator()
    
    priority_enum = None
    if priority:
        try:
            priority_enum = TaskPriority(priority.lower())
        except ValueError:
            print(f"Invalid priority: {priority}. Using None.")
    
    return await orchestrator.get_pending_manual_tasks(limit=limit, priority=priority_enum)


# Example usage and testing functions
if __name__ == "__main__":
    import asyncio
    
    async def test_workflow():
        """Test the workflow orchestration."""
        print("🧪 Testing Workflow Orchestration")
        
        # Test with small limit and force manual for testing
        result = await run_workflow(
            limit=10,
            force_manual=True
        )
        
        print(f"Workflow result: {result}")
        
        # Check status
        if result.get('batch_id'):
            status = await get_workflow_status(result['batch_id'])
            print(f"Workflow status: {status}")
        
        # Get pending manual tasks
        pending_tasks = await get_pending_manual_tasks(limit=5)
        print(f"Pending manual tasks: {len(pending_tasks)}")
        for task in pending_tasks[:3]:  # Show first 3
            print(f"  - Task {task['task_id']}: {task['part_number']} ({task['priority']})")
    
    # Run test
    asyncio.run(test_workflow())
