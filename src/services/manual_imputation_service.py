"""
Manual Imputation Service for handling manual data entry and updates.
This service provides comprehensive functionality for manual data imputation
with proper logging, validation, and traceability.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from src.db.connections import get_supabase_async_engine
from src.db.models import (
    Product, PartNumber, Manufacturer, Category, Attribute,
    ProductAttribute, ProductExtra, DocumentMedia, ProductSeller,
    ManualTask, CategoryAttribute
)
from src.db.repositories.async_repositories import (
    ProductRepository, PartNumberRepository, ManufacturerRepository,
    ProductAttributeRepository, ProductExtraRepository, DocumentMediaRepository,
    ProductSellerRepository, CategoryRepository
)


class ManualImputationService:
    """
    Service class for handling manual data imputation operations.
    Provides methods for creating, updating, and tracking manual data changes.
    """
    
    def __init__(self):
        self.async_engine = get_supabase_async_engine()
        self.AsyncSessionLocal = async_sessionmaker(bind=self.async_engine, expire_on_commit=False)
    
    async def create_manual_task(
        self,
        part_number: str,
        editor: str,
        data_updates: Dict[str, Any],
        notes: Optional[str] = None,
        source_url: Optional[str] = None,
        batch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new manual imputation task and apply the data updates.
        
        Args:
            part_number: The part number to update
            editor: Username/ID of the person making the changes
            data_updates: Dictionary containing the data to update
            notes: Optional notes about the changes
            source_url: Optional source URL for traceability
            batch_id: Optional batch identifier for grouping related tasks
            
        Returns:
            Dictionary with task information and results
        """
        async with self.AsyncSessionLocal() as session:
            try:
                # Create manual task record
                manual_task = ManualTask()
                manual_task.initialize_task(
                    product_id=None,  # Will be set after we get the product
                    editor=editor,
                    batch_id=batch_id or f"manual_{int(datetime.now().timestamp())}"
                )
                manual_task.task_type = 'manual_imputation'
                manual_task.edited_fields = data_updates
                manual_task.note = notes
                manual_task.source_url = source_url
                manual_task.start_processing()
                
                session.add(manual_task)
                await session.flush()  # Get the ID
                
                # Process the data updates
                results = await self._process_data_updates(
                    session, part_number, data_updates, manual_task, editor, notes, source_url
                )
                
                # Update manual task with results
                manual_task.affected_tables = results.get('affected_tables', [])
                manual_task.changes_summary = results.get('changes_summary', {})
                manual_task.mark_completed()
                
                await session.commit()
                
                return {
                    'status': 'success',
                    'task_id': manual_task.id,
                    'part_number': part_number,
                    'affected_tables': results.get('affected_tables', []),
                    'changes_count': results.get('changes_count', 0),
                    'message': f'Manual imputation completed for {part_number}'
                }
                
            except Exception as e:
                await session.rollback()
                if 'manual_task' in locals():
                    manual_task.mark_failed(str(e))
                    await session.commit()
                
                return {
                    'status': 'error',
                    'message': f'Failed to process manual imputation: {str(e)}',
                    'part_number': part_number
                }
    
    async def _process_data_updates(
        self,
        session: AsyncSession,
        part_number: str,
        data_updates: Dict[str, Any],
        manual_task: ManualTask,
        editor: str,
        notes: Optional[str],
        source_url: Optional[str]
    ) -> Dict[str, Any]:
        """
        Process the actual data updates for a part number.
        
        Args:
            session: Database session
            part_number: Part number to update
            data_updates: Data to update
            manual_task: Manual task record
            editor: Editor username
            notes: Optional notes
            source_url: Optional source URL
            
        Returns:
            Dictionary with processing results
        """
        affected_tables = []
        changes_summary = {}
        changes_count = 0
        
        # Get or create part number record
        part_number_repo = PartNumberRepository(session)
        pn_records = await part_number_repo.list(name=part_number)
        
        if not pn_records:
            # Create new part number
            pn_record = PartNumber(
                name=part_number,
                notes=notes,
                source_url=source_url,
                manual_editor=editor,
                last_manual_update=datetime.now()
            )
            session.add(pn_record)
            await session.flush()
            pn_record.product_id = pn_record.id
            affected_tables.append('part_numbers')
            changes_count += 1
        else:
            pn_record = pn_records[0]
            # Update part number with manual fields
            if notes:
                pn_record.notes = notes
            if source_url:
                pn_record.source_url = source_url
            pn_record.manual_editor = editor
            pn_record.last_manual_update = datetime.now()
            affected_tables.append('part_numbers')
        
        # Get or create product record
        product_repo = ProductRepository(session)
        products = await session.execute(
            select(Product).where(Product.part_number == pn_record.product_id)
        )
        product = products.scalar_one_or_none()
        
        if not product:
            # Create new product
            product = Product(part_number=pn_record.product_id)
            session.add(product)
            await session.flush()
            affected_tables.append('products')
            changes_count += 1
        
        # Process different types of updates
        if 'attributes' in data_updates:
            attr_results = await self._update_product_attributes(
                session, product, data_updates['attributes'], manual_task, editor, notes, source_url
            )
            affected_tables.extend(attr_results['affected_tables'])
            changes_summary['attributes'] = attr_results['changes']
            changes_count += attr_results['count']
        
        if 'extras' in data_updates:
            extra_results = await self._update_product_extras(
                session, product, data_updates['extras'], manual_task, editor, notes, source_url
            )
            affected_tables.extend(extra_results['affected_tables'])
            changes_summary['extras'] = extra_results['changes']
            changes_count += extra_results['count']
        
        if 'documents' in data_updates:
            doc_results = await self._update_document_media(
                session, product, data_updates['documents'], manual_task, editor, notes, source_url
            )
            affected_tables.extend(doc_results['affected_tables'])
            changes_summary['documents'] = doc_results['changes']
            changes_count += doc_results['count']
        
        if 'sellers' in data_updates:
            seller_results = await self._update_product_sellers(
                session, product, data_updates['sellers'], manual_task, editor, notes, source_url
            )
            affected_tables.extend(seller_results['affected_tables'])
            changes_summary['sellers'] = seller_results['changes']
            changes_count += seller_results['count']
        
        # Update manual task reference
        manual_task.part_number_id = pn_record.id
        
        return {
            'affected_tables': list(set(affected_tables)),
            'changes_summary': changes_summary,
            'changes_count': changes_count
        }
    
    async def _update_product_attributes(
        self,
        session: AsyncSession,
        product: Product,
        attributes: List[Dict[str, Any]],
        manual_task: ManualTask,
        editor: str,
        notes: Optional[str],
        source_url: Optional[str]
    ) -> Dict[str, Any]:
        """Update product attributes with manual data."""
        affected_tables = []
        changes = []
        count = 0
        
        for attr_data in attributes:
            attr_name = attr_data.get('name')
            attr_value = attr_data.get('value')
            attr_unit = attr_data.get('unit')
            
            if not attr_name or not attr_value:
                continue
            
            # Get or create attribute
            attribute = await session.scalar(
                select(Attribute).where(Attribute.name == attr_name)
            )
            if not attribute:
                attribute = Attribute(name=attr_name)
                session.add(attribute)
                await session.flush()
            
            # Create product attribute
            product_attr = ProductAttribute(
                product_id=product.product_id,
                attribute_id=attribute.id,
                value_text=str(attr_value),
                value_unit=attr_unit,
                source='manual',
                manual_task_id=manual_task.id,
                notes=notes,
                source_url=source_url
            )
            session.add(product_attr)
            
            affected_tables.extend(['attributes', 'product_attributes'])
            changes.append({
                'attribute': attr_name,
                'value': attr_value,
                'unit': attr_unit
            })
            count += 1
        
            return {
                'affected_tables': affected_tables,
                'changes': changes,
                'count': count
            }

    async def get_products_for_selection(
        self,
        search: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get products with part numbers for dropdown selection.
        
        Args:
            search: Search term for part numbers
            limit: Maximum number of products to return
            
        Returns:
            List of products with product_id and part_number for dropdown
        """
        async with self.AsyncSessionLocal() as session:
            # Join products with part_numbers to get both product_id and part_number
            query = select(Product, PartNumber)\
                .join(PartNumber, Product.part_number == PartNumber.product_id)\
                .order_by(PartNumber.name)\
                .limit(limit)
            
            if search:
                query = query.where(PartNumber.name.ilike(f"%{search}%"))
            
            result = await session.execute(query)
            products_with_parts = result.all()
            
            return [
                {
                    'product_id': product.product_id,
                    'part_number': part_number.name,
                    'display_text': f"{product.product_id} - {part_number.name}"
                }
                for product, part_number in products_with_parts
            ]

    # Category and Attribute management methods

    async def get_categories(
        self,
        parent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get categories, optionally filtered by parent.
        
        Args:
            parent_id: Parent category ID to get children, None for root categories
            
        Returns:
            List of categories
        """
        async with self.AsyncSessionLocal() as session:
            if parent_id is None:
                # Get root categories (assuming there's a root parent ID)
                ROOT_PARENT_ID = '11111111-1111-1111-1111-111111111111'
                query = select(Category).where(Category.parent_id == ROOT_PARENT_ID).order_by(Category.name)
            else:
                query = select(Category).where(Category.parent_id == parent_id).order_by(Category.name)
            
            result = await session.execute(query)
            categories = result.scalars().all()
            
            return [
                {
                    'id': str(cat.id),
                    'name': cat.name,
                    'fullname': cat.fullname,
                    'parent_id': str(cat.parent_id) if cat.parent_id else None,
                    'product_category': cat.product_category,
                    'depth': cat.depth,
                    'path': cat.path,
                    'created_date': cat.created_date,
                    'updated_date': cat.updated_date
                }
                for cat in categories
            ]

    async def create_category(
        self,
        name: str,
        parent_id: Optional[str] = None,
        product_category: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new category with proper hierarchy.
        
        Args:
            name: Category name
            parent_id: Parent category ID
            product_category: Whether this category can have products
            
        Returns:
            Created category information
        """
        async with self.AsyncSessionLocal() as session:
            try:
                # If no parent_id provided, use root
                if parent_id is None:
                    ROOT_PARENT_ID = '11111111-1111-1111-1111-111111111111'
                    parent_id = ROOT_PARENT_ID
                
                # Get parent category to build path and depth
                parent = await session.scalar(
                    select(Category).where(Category.id == parent_id)
                )
                
                if parent_id != '11111111-1111-1111-1111-111111111111' and not parent:
                    return {
                        'status': 'error',
                        'message': f'Parent category {parent_id} not found'
                    }
                
                # Build path and depth
                if parent:
                    path = (parent.path or []) + [str(parent.id)]
                    depth = (parent.depth or 0) + 1
                    fullname = f"{parent.fullname} > {name}" if parent.fullname else name
                else:
                    path = []
                    depth = 0
                    fullname = name
                
                # Create new category
                category = Category(
                    name=name,
                    fullname=fullname,
                    parent_id=parent_id,
                    path=path,
                    depth=depth,
                    product_category=product_category
                )
                
                session.add(category)
                await session.flush()
                await session.commit()
                
                return {
                    'status': 'success',
                    'category': {
                        'id': str(category.id),
                        'name': category.name,
                        'fullname': category.fullname,
                        'parent_id': str(category.parent_id),
                        'product_category': category.product_category,
                        'depth': category.depth,
                        'path': category.path
                    },
                    'message': f'Category "{name}" created successfully'
                }
                
            except Exception as e:
                await session.rollback()
                return {
                    'status': 'error',
                    'message': f'Failed to create category: {str(e)}'
                }

    async def get_attributes(
        self,
        category_id: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get attributes, optionally filtered by category or search term.
        
        Args:
            category_id: Category ID to get related attributes
            search: Search term for attribute names
            
        Returns:
            List of attributes
        """
        async with self.AsyncSessionLocal() as session:
            if category_id:
                # Get attributes linked to this category
                query = select(Attribute)\
                    .join(CategoryAttribute, Attribute.id == CategoryAttribute.attribute_id)\
                    .where(CategoryAttribute.category_id == category_id)\
                    .order_by(Attribute.name)
            else:
                # Get all attributes
                query = select(Attribute).order_by(Attribute.name)
            
            if search:
                query = query.where(Attribute.name.ilike(f"%{search}%"))
            
            result = await session.execute(query)
            attributes = result.scalars().all()
            
            return [
                {
                    'id': attr.id,
                    'name': attr.name,
                    'desc': attr.desc,
                    'unit': attr.unit,
                    'created_date': attr.created_date,
                    'updated_date': attr.updated_date
                }
                for attr in attributes
            ]

    async def create_attribute(
        self,
        name: str,
        desc: Optional[str] = None,
        category_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new attribute and optionally link it to a category.
        
        Args:
            name: Attribute name
            desc: Attribute description
            category_id: Category ID to link the attribute to
            
        Returns:
            Created attribute information
        """
        async with self.AsyncSessionLocal() as session:
            try:
                # Check if attribute already exists
                existing = await session.scalar(
                    select(Attribute).where(Attribute.name == name)
                )
                
                if existing:
                    # If category_id provided, link existing attribute to category
                    if category_id:
                        # Check if link already exists
                        existing_link = await session.scalar(
                            select(CategoryAttribute).where(
                                and_(
                                    CategoryAttribute.category_id == category_id,
                                    CategoryAttribute.attribute_id == existing.id
                                )
                            )
                        )
                        
                        if not existing_link:
                            cat_attr = CategoryAttribute(
                                category_id=category_id,
                                attribute_id=existing.id
                            )
                            session.add(cat_attr)
                            await session.commit()
                    
                    return {
                        'status': 'success',
                        'attribute': {
                            'id': existing.id,
                            'name': existing.name,
                            'desc': existing.desc,
                            'unit': existing.unit
                        },
                        'message': f'Attribute "{name}" already exists' + (f' and linked to category' if category_id else '')
                    }
                
                # Create new attribute
                attribute = Attribute(
                    name=name,
                    desc=desc
                )
                
                session.add(attribute)
                await session.flush()
                
                # Link to category if provided
                if category_id:
                    cat_attr = CategoryAttribute(
                        category_id=category_id,
                        attribute_id=attribute.id
                    )
                    session.add(cat_attr)
                
                await session.commit()
                
                return {
                    'status': 'success',
                    'attribute': {
                        'id': attribute.id,
                        'name': attribute.name,
                        'desc': attribute.desc,
                        'unit': attribute.unit
                    },
                    'message': f'Attribute "{name}" created successfully' + (f' and linked to category' if category_id else '')
                }
                
            except Exception as e:
                await session.rollback()
                return {
                    'status': 'error',
                    'message': f'Failed to create attribute: {str(e)}'
                }

    async def process_task_data(
        self,
        task_id: int,
        category_id: Optional[str] = None,
        attributes: Optional[List] = None,
        extras: Optional[List] = None,
        documents: Optional[List] = None,
        sellers: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Process a task with detailed data including category assignment and individual notes/sources.
        
        Args:
            task_id: Task ID to process
            category_id: Category ID to assign to product
            attributes: List of attributes with individual notes/sources
            extras: List of extras with individual notes/sources
            documents: List of documents with individual notes/sources
            sellers: List of sellers with individual notes/sources
            
        Returns:
            Dictionary with processing results
        """
        async with self.AsyncSessionLocal() as session:
            try:
                # Get the task
                task = await session.scalar(
                    select(ManualTask).where(ManualTask.id == task_id)
                )
                
                if not task:
                    return {
                        'status': 'error',
                        'message': f'Task {task_id} not found'
                    }
                
                # Get the product
                product = await session.scalar(
                    select(Product).where(Product.product_id == task.product_id)
                )
                
                if not product:
                    return {
                        'status': 'error',
                        'message': f'Product {task.product_id} not found'
                    }
                
                # Start processing
                task.start_processing()
                
                affected_tables = []
                changes_summary = {}
                changes_count = 0
                
                # Assign category to product if provided
                if category_id:
                    product.category_id = category_id
                    affected_tables.append('products')
                    changes_summary['category'] = {'category_id': category_id}
                    changes_count += 1
                
                # Process attributes with individual notes/sources and category linking
                if attributes:
                    attr_results = await self._process_attributes_with_meta_and_category(
                        session, product, attributes, task, category_id
                    )
                    affected_tables.extend(attr_results['affected_tables'])
                    changes_summary['attributes'] = attr_results['changes']
                    changes_count += attr_results['count']
                
                # Process extras with individual notes/sources
                if extras:
                    extra_results = await self._process_extras_with_meta(
                        session, product, extras, task
                    )
                    affected_tables.extend(extra_results['affected_tables'])
                    changes_summary['extras'] = extra_results['changes']
                    changes_count += extra_results['count']
                
                # Process documents with individual notes/sources
                if documents:
                    doc_results = await self._process_documents_with_meta(
                        session, product, documents, task
                    )
                    affected_tables.extend(doc_results['affected_tables'])
                    changes_summary['documents'] = doc_results['changes']
                    changes_count += doc_results['count']
                
                # Process sellers with individual notes/sources
                if sellers:
                    seller_results = await self._process_sellers_with_meta(
                        session, product, sellers, task
                    )
                    affected_tables.extend(seller_results['affected_tables'])
                    changes_summary['sellers'] = seller_results['changes']
                    changes_count += seller_results['count']
                
                # Update task with results
                task.affected_tables = list(set(affected_tables))
                task.changes_summary = changes_summary
                task.mark_completed()
                
                await session.commit()
                
                return {
                    'status': 'success',
                    'task_id': task_id,
                    'affected_tables': list(set(affected_tables)),
                    'changes_count': changes_count,
                    'changes_summary': changes_summary,
                    'message': f'Task {task_id} processed successfully'
                }
                
            except Exception as e:
                await session.rollback()
                if 'task' in locals():
                    task.mark_failed(str(e))
                    await session.commit()
                
                return {
                    'status': 'error',
                    'message': f'Failed to process task: {str(e)}'
                }

    async def _process_attributes_with_meta_and_category(
        self,
        session: AsyncSession,
        product: Product,
        attributes: List,
        task: ManualTask,
        category_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process attributes with individual metadata and category linking."""
        affected_tables = []
        changes = []
        count = 0
        
        for attr_data in attributes:
            attr_name = attr_data.get('name') if hasattr(attr_data, 'get') else getattr(attr_data, 'name', None)
            attr_value = attr_data.get('value') if hasattr(attr_data, 'get') else getattr(attr_data, 'value', None)
            attr_unit = attr_data.get('unit') if hasattr(attr_data, 'get') else getattr(attr_data, 'unit', None)
            attr_notes = attr_data.get('notes') if hasattr(attr_data, 'get') else getattr(attr_data, 'notes', None)
            attr_source = attr_data.get('source_url') if hasattr(attr_data, 'get') else getattr(attr_data, 'source_url', None)
            
            if not attr_name or not attr_value:
                continue
            
            # Get or create attribute
            attribute = await session.scalar(
                select(Attribute).where(Attribute.name == attr_name)
            )
            if not attribute:
                attribute = Attribute(name=attr_name)
                session.add(attribute)
                await session.flush()
            
            # Link attribute to category if category is provided
            if category_id and attribute:
                existing_link = await session.scalar(
                    select(CategoryAttribute).where(
                        and_(
                            CategoryAttribute.category_id == category_id,
                            CategoryAttribute.attribute_id == attribute.id
                        )
                    )
                )
                
                if not existing_link:
                    cat_attr = CategoryAttribute(
                        category_id=category_id,
                        attribute_id=attribute.id
                    )
                    session.add(cat_attr)
                    affected_tables.append('category_attributes')
            
            # Create product attribute with individual metadata
            product_attr = ProductAttribute(
                product_id=product.product_id,
                attribute_id=attribute.id,
                value_text=str(attr_value),
                value_unit=attr_unit,
                source='manual',
                manual_task_id=task.id,
                notes=attr_notes,
                source_url=attr_source
            )
            session.add(product_attr)
            
            affected_tables.extend(['attributes', 'product_attributes'])
            changes.append({
                'attribute': attr_name,
                'value': attr_value,
                'unit': attr_unit,
                'notes': attr_notes,
                'source_url': attr_source
            })
            count += 1
        
        return {
            'affected_tables': affected_tables,
            'changes': changes,
            'count': count
        }
    
    async def _update_product_extras(
        self,
        session: AsyncSession,
        product: Product,
        extras: List[Dict[str, Any]],
        manual_task: ManualTask,
        editor: str,
        notes: Optional[str],
        source_url: Optional[str]
    ) -> Dict[str, Any]:
        """Update product extras with manual data."""
        affected_tables = []
        changes = []
        count = 0
        
        for extra_data in extras:
            extra_name = extra_data.get('name')
            extra_value = extra_data.get('value')
            
            if not extra_name or not extra_value:
                continue
            
            product_extra = ProductExtra(
                product_id=product.product_id,
                name=extra_name,
                value=str(extra_value),
                source='manual',
                manual_task_id=manual_task.id,
                notes=notes,
                source_url=source_url
            )
            session.add(product_extra)
            
            affected_tables.append('product_extras')
            changes.append({
                'name': extra_name,
                'value': extra_value
            })
            count += 1
        
        return {
            'affected_tables': affected_tables,
            'changes': changes,
            'count': count
        }
    
    async def _update_document_media(
        self,
        session: AsyncSession,
        product: Product,
        documents: List[Dict[str, Any]],
        manual_task: ManualTask,
        editor: str,
        notes: Optional[str],
        source_url: Optional[str]
    ) -> Dict[str, Any]:
        """Update document media with manual data."""
        affected_tables = []
        changes = []
        count = 0
        
        for doc_data in documents:
            doc_url = doc_data.get('url')
            doc_type = doc_data.get('type', 'document')
            doc_description = doc_data.get('description', '')
            
            if not doc_url:
                continue
            
            document = DocumentMedia(
                product_id=product.product_id,
                url=doc_url,
                type=doc_type,
                description=doc_description,
                source='manual',
                manual_task_id=manual_task.id,
                notes=notes,
                source_url=source_url
            )
            session.add(document)
            
            affected_tables.append('document_media')
            changes.append({
                'url': doc_url,
                'type': doc_type,
                'description': doc_description
            })
            count += 1
        
        return {
            'affected_tables': affected_tables,
            'changes': changes,
            'count': count
        }
    
    async def _update_product_sellers(
        self,
        session: AsyncSession,
        product: Product,
        sellers: List[Dict[str, Any]],
        manual_task: ManualTask,
        editor: str,
        notes: Optional[str],
        source_url: Optional[str]
    ) -> Dict[str, Any]:
        """Update product sellers with manual data."""
        affected_tables = []
        changes = []
        count = 0
        
        for seller_data in sellers:
            seller_name = seller_data.get('name')
            seller_type = seller_data.get('type', 'distributor')
            
            if not seller_name:
                continue
            
            # Generate seller_id
            seller_id = f"{product.product_id}_{seller_name}_{int(datetime.now().timestamp())}"
            
            product_seller = ProductSeller(
                seller_id=seller_id,
                product_id=product.product_id,
                seller_name=seller_name,
                seller_type=seller_type,
                source='manual',
                manual_task_id=manual_task.id,
                notes=notes,
                source_url=source_url
            )
            session.add(product_seller)
            
            affected_tables.append('product_sellers')
            changes.append({
                'name': seller_name,
                'type': seller_type
            })
            count += 1
        
        return {
            'affected_tables': affected_tables,
            'changes': changes,
            'count': count
        }
    
    async def get_manual_task_history(
        self,
        part_number: Optional[str] = None,
        editor: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get manual task history with optional filtering.
        
        Args:
            part_number: Filter by part number
            editor: Filter by editor
            limit: Maximum number of records to return
            
        Returns:
            List of manual task records
        """
        async with self.AsyncSessionLocal() as session:
            query = select(ManualTask).order_by(ManualTask.created_date.desc()).limit(limit)
            
            if editor:
                query = query.where(ManualTask.editor == editor)
            
            result = await session.execute(query)
            tasks = result.scalars().all()
            
            return [
                {
                    'id': task.id,
                    'product_id': task.product_id,
                    'editor': task.editor,
                    'current_status': task.current_status,
                    'task_type': task.task_type,
                    'edited_fields': task.edited_fields,
                    'affected_tables': task.affected_tables,
                    'changes_summary': task.changes_summary,
                    'note': task.note,
                    'source_url': task.source_url,
                    'batch_id': task.batch_id,
                    'validated': task.validated,
                    'validator': task.validator,
                    'validation_date': task.validation_date,
                    'processing_info': task.processing_info,
                    'error_message': task.error_message,
                    'created_date': task.created_date,
                    'updated_date': task.updated_date
                }
                for task in tasks
            ]
    
    async def validate_manual_task(
        self,
        task_id: int,
        validator: str,
        validation_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a manual task.
        
        Args:
            task_id: ID of the manual task to validate
            validator: Username of the validator
            validation_notes: Optional validation notes
            
        Returns:
            Dictionary with validation results
        """
        async with self.AsyncSessionLocal() as session:
            try:
                task = await session.scalar(
                    select(ManualTask).where(ManualTask.id == task_id)
                )
                
                if not task:
                    return {
                        'status': 'error',
                        'message': f'Manual task {task_id} not found'
                    }
                
                task.mark_validated(validator)
                if validation_notes:
                    task.note = validation_notes
                await session.commit()
                
                return {
                    'status': 'success',
                    'message': f'Manual task {task_id} validated successfully',
                    'task_id': task_id,
                    'validator': validator,
                    'validation_date': task.validation_date
                }
                
            except Exception as e:
                await session.rollback()
                return {
                    'status': 'error',
                    'message': f'Failed to validate manual task: {str(e)}'
                }


    async def get_manual_task_by_id(self, task_id: int) -> Optional[dict]:
        async with self.AsyncSessionLocal() as session:
            result = await session.execute(select(ManualTask).where(ManualTask.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return None
            return {
                'id': task.id,
                'product_id': task.product_id,
                'editor': task.editor,
                'current_status': task.current_status,
                'task_type': task.task_type,
                'edited_fields': task.edited_fields,
                'affected_tables': task.affected_tables,
                'changes_summary': task.changes_summary,
                'note': task.note,
                'source_url': task.source_url,
                'batch_id': task.batch_id,
                'validated': task.validated,
                'validator': task.validator,
                'validation_date': task.validation_date,
                'processing_info': task.processing_info,
                'error_message': task.error_message,
                'created_date': task.created_date,
                'updated_date': task.updated_date
            }

    async def update_task_metadata(self, task_id: int, note: Optional[str], source_url: Optional[str]) -> bool:
        async with self.AsyncSessionLocal() as session:
            result = await session.execute(select(ManualTask).where(ManualTask.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return False
            if note is not None:
                task.note = note
            if source_url is not None:
                task.source_url = source_url
            task.updated_date = func.now()
            await session.commit()
            return True

    async def delete_task(self, task_id: int) -> bool:
        async with self.AsyncSessionLocal() as session:
            result = await session.execute(select(ManualTask).where(ManualTask.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return False
            await session.delete(task)
            await session.commit()
            return True

    async def get_tasks_by_filters(
        self,
        product_id: Optional[int] = None,
        part_number: Optional[str] = None,
        last_updated_days: Optional[int] = None,
        status: Optional[str] = None,
        editor: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get tasks with various filtering options.
        
        Args:
            product_id: Filter by product ID
            part_number: Filter by part number
            last_updated_days: Filter by tasks updated in last N days
            status: Filter by task status
            editor: Filter by editor
            limit: Maximum number of records to return
            
        Returns:
            List of manual task records
        """
        async with self.AsyncSessionLocal() as session:
            query = select(ManualTask).order_by(ManualTask.updated_date.desc()).limit(limit)
            
            # Apply filters
            if product_id:
                query = query.where(ManualTask.product_id == product_id)
            
            if part_number:
                # Join with PartNumber to filter by part number name
                query = query.join(Product, ManualTask.product_id == Product.product_id)\
                            .join(PartNumber, Product.part_number == PartNumber.product_id)\
                            .where(PartNumber.name.ilike(f"%{part_number}%"))
            
            if last_updated_days:
                from datetime import datetime, timedelta
                cutoff_date = datetime.now() - timedelta(days=last_updated_days)
                query = query.where(ManualTask.updated_date >= cutoff_date)
            
            if status:
                query = query.where(ManualTask.current_status == status)
            
            if editor:
                query = query.where(ManualTask.editor == editor)
            
            result = await session.execute(query)
            tasks = result.scalars().all()
            
            return [
                {
                    'id': task.id,
                    'product_id': task.product_id,
                    'editor': task.editor,
                    'current_status': task.current_status,
                    'task_type': task.task_type,
                    'edited_fields': task.edited_fields,
                    'affected_tables': task.affected_tables,
                    'changes_summary': task.changes_summary,
                    'note': task.note,
                    'source_url': task.source_url,
                    'batch_id': task.batch_id,
                    'validated': task.validated,
                    'validator': task.validator,
                    'validation_date': task.validation_date,
                    'processing_info': task.processing_info,
                    'error_message': task.error_message,
                    'created_date': task.created_date,
                    'updated_date': task.updated_date
                }
                for task in tasks
            ]

    async def search_part_numbers(
        self,
        query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search part numbers and get related product information.
        
        Args:
            query: Search query for part numbers
            limit: Maximum number of results to return
            
        Returns:
            List of part numbers with basic product info
        """
        async with self.AsyncSessionLocal() as session:
            # Search part numbers by name
            search_query = select(PartNumber)\
                .where(PartNumber.name.ilike(f"%{query}%"))\
                .order_by(PartNumber.name)\
                .limit(limit)
            
            result = await session.execute(search_query)
            part_numbers = result.scalars().all()
            
            results = []
            for pn in part_numbers:
                # Get associated product if exists
                product = await session.scalar(
                    select(Product).where(Product.part_number == pn.product_id)
                )
                
                # Get manufacturer info if product exists
                manufacturer = None
                if product and product.manufacturer_id:
                    manufacturer = await session.scalar(
                        select(Manufacturer).where(Manufacturer.id == product.manufacturer_id)
                    )
                
                # Get category info if product exists
                category = None
                if product and product.category_id:
                    category = await session.scalar(
                        select(Category).where(Category.id == product.category_id)
                    )
                
                results.append({
                    'part_number': pn.name,
                    'part_number_id': pn.id,
                    'product_id': product.product_id if product else None,
                    'manufacturer': manufacturer.name if manufacturer else None,
                    'manufacturer_id': manufacturer.id if manufacturer else None,
                    'category': category.name if category else None,
                    'category_id': category.id if category else None,
                    'notes': pn.notes,
                    'source_url': pn.source_url,
                    'last_manual_update': pn.last_manual_update,
                    'manual_editor': pn.manual_editor,
                    'created_date': pn.created_date,
                    'updated_date': pn.updated_date
                })
            
            return results

    async def get_product_details(
        self,
        product_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete product details including attributes, extras, category, etc.
        
        Args:
            product_id: Product ID to get details for
            
        Returns:
            Complete product details or None if not found
        """
        async with self.AsyncSessionLocal() as session:
            # Get product with relationships
            product = await session.scalar(
                select(Product)
                .options(
                    selectinload(Product.manufacturer),
                    selectinload(Product.category),
                    selectinload(Product.product_attributes).selectinload(ProductAttribute.attribute),
                    selectinload(Product.product_extras),
                    selectinload(Product.document_media),
                    selectinload(Product.product_sellers)
                )
                .where(Product.product_id == product_id)
            )
            
            if not product:
                return None
            
            # Get part number info
            part_number = await session.scalar(
                select(PartNumber).where(PartNumber.product_id == product.part_number)
            )
            
            # Build response
            result = {
                'product_id': product.product_id,
                'part_number': part_number.name if part_number else None,
                'part_number_id': part_number.id if part_number else None,
                'manufacturer': {
                    'id': product.manufacturer.id if product.manufacturer else None,
                    'name': product.manufacturer.name if product.manufacturer else None
                },
                'category': {
                    'id': product.category.id if product.category else None,
                    'name': product.category.name if product.category else None,
                    'fullname': product.category.fullname if product.category else None
                },
                'attributes': [
                    {
                        'id': attr.id,
                        'attribute_name': attr.attribute.name if attr.attribute else None,
                        'value_text': attr.value_text,
                        'value_float': attr.value_float,
                        'value_unit': attr.value_unit,
                        'source': attr.source,
                        'manual_task_id': attr.manual_task_id,
                        'automation_task_id': attr.automation_task_id,
                        'notes': attr.notes,
                        'source_url': attr.source_url,
                        'created_date': attr.created_date,
                        'updated_date': attr.updated_date
                    }
                    for attr in product.product_attributes
                ],
                'extras': [
                    {
                        'id': extra.extra_id,
                        'name': extra.name,
                        'value': extra.value,
                        'source': extra.source,
                        'manual_task_id': extra.manual_task_id,
                        'automation_task_id': extra.automation_task_id,
                        'notes': extra.notes,
                        'source_url': extra.source_url,
                        'created_date': extra.created_date,
                        'updated_date': extra.updated_date
                    }
                    for extra in product.product_extras
                ],
                'documents': [
                    {
                        'id': doc.id,
                        'url': doc.url,
                        'type': doc.type,
                        'description': doc.description,
                        'source': doc.source,
                        'manual_task_id': doc.manual_task_id,
                        'automation_task_id': doc.automation_task_id,
                        'notes': doc.notes,
                        'source_url': doc.source_url,
                        'created_date': doc.created_date,
                        'updated_date': doc.updated_date
                    }
                    for doc in product.document_media
                ],
                'sellers': [
                    {
                        'id': seller.id,
                        'seller_id': seller.seller_id,
                        'seller_name': seller.seller_name,
                        'seller_type': seller.seller_type,
                        'source': seller.source,
                        'ref_id': seller.ref_id,
                        'notes': seller.notes,
                        'source_url': seller.source_url,
                        'created_date': seller.created_date,
                        'updated_date': seller.updated_date
                    }
                    for seller in product.product_sellers
                ],
                'created_date': product.created_date,
                'updated_date': product.updated_date
            }
            
            return result

    async def get_product_by_part_number(
        self,
        part_number: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get product details by part number.
        
        Args:
            part_number: Part number to search for
            
        Returns:
            Complete product details or None if not found
        """
        async with self.AsyncSessionLocal() as session:
            # Find part number
            pn = await session.scalar(
                select(PartNumber).where(PartNumber.name == part_number)
            )
            
            if not pn:
                return None
            
            # Get product using the part number's product_id
            product = await session.scalar(
                select(Product).where(Product.part_number == pn.product_id)
            )
            
            if not product:
                return None
            
            # Use existing method to get full product details
            return await self.get_product_details(product.product_id)

    async def create_simple_task(
        self,
        product_id: Optional[int] = None,
        part_number: Optional[str] = None,
        editor: str = "",
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a simple manual task with just basic information.
        
        Args:
            product_id: Product ID (use this OR part_number)
            part_number: Part number (use this OR product_id)
            editor: Username of the editor
            notes: Optional notes about the task
            
        Returns:
            Dictionary with task information
        """
        async with self.AsyncSessionLocal() as session:
            try:
                # Resolve product_id if part_number is provided
                if part_number and not product_id:
                    pn = await session.scalar(
                        select(PartNumber).where(PartNumber.name == part_number)
                    )
                    if pn:
                        product = await session.scalar(
                            select(Product).where(Product.part_number == pn.product_id)
                        )
                        if product:
                            product_id = product.product_id
                
                # Create manual task record
                manual_task = ManualTask()
                manual_task.initialize_task(
                    product_id=product_id,
                    editor=editor,
                    batch_id=f"simple_{int(datetime.now().timestamp())}"
                )
                manual_task.task_type = 'simple_task'
                manual_task.note = notes
                manual_task.current_status = 'initialized'
                
                session.add(manual_task)
                await session.flush()
                await session.commit()
                
                return {
                    'status': 'success',
                    'task_id': manual_task.id,
                    'product_id': product_id,
                    'part_number': part_number,
                    'message': f'Simple task created successfully',
                    'next_step': f'Use POST /manual/task/process/ with task_id {manual_task.id} to add data'
                }
                
            except Exception as e:
                await session.rollback()
                return {
                    'status': 'error',
                    'message': f'Failed to create simple task: {str(e)}'
                }

    async def process_task_data(
        self,
        task_id: int,
        attributes: Optional[List] = None,
        extras: Optional[List] = None,
        documents: Optional[List] = None,
        sellers: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Process a task with detailed data including individual notes and sources.
        
        Args:
            task_id: Task ID to process
            attributes: List of attributes with individual notes/sources
            extras: List of extras with individual notes/sources
            documents: List of documents with individual notes/sources
            sellers: List of sellers with individual notes/sources
            
        Returns:
            Dictionary with processing results
        """
        async with self.AsyncSessionLocal() as session:
            try:
                # Get the task
                task = await session.scalar(
                    select(ManualTask).where(ManualTask.id == task_id)
                )
                
                if not task:
                    return {
                        'status': 'error',
                        'message': f'Task {task_id} not found'
                    }
                
                # Get the product
                product = await session.scalar(
                    select(Product).where(Product.product_id == task.product_id)
                )
                
                if not product:
                    return {
                        'status': 'error',
                        'message': f'Product {task.product_id} not found'
                    }
                
                # Start processing
                task.start_processing()
                
                affected_tables = []
                changes_summary = {}
                changes_count = 0
                
                # Process attributes with individual notes/sources
                if attributes:
                    attr_results = await self._process_attributes_with_meta(
                        session, product, attributes, task
                    )
                    affected_tables.extend(attr_results['affected_tables'])
                    changes_summary['attributes'] = attr_results['changes']
                    changes_count += attr_results['count']
                
                # Process extras with individual notes/sources
                if extras:
                    extra_results = await self._process_extras_with_meta(
                        session, product, extras, task
                    )
                    affected_tables.extend(extra_results['affected_tables'])
                    changes_summary['extras'] = extra_results['changes']
                    changes_count += extra_results['count']
                
                # Process documents with individual notes/sources
                if documents:
                    doc_results = await self._process_documents_with_meta(
                        session, product, documents, task
                    )
                    affected_tables.extend(doc_results['affected_tables'])
                    changes_summary['documents'] = doc_results['changes']
                    changes_count += doc_results['count']
                
                # Process sellers with individual notes/sources
                if sellers:
                    seller_results = await self._process_sellers_with_meta(
                        session, product, sellers, task
                    )
                    affected_tables.extend(seller_results['affected_tables'])
                    changes_summary['sellers'] = seller_results['changes']
                    changes_count += seller_results['count']
                
                # Update task with results
                task.affected_tables = list(set(affected_tables))
                task.changes_summary = changes_summary
                task.mark_completed()
                
                await session.commit()
                
                return {
                    'status': 'success',
                    'task_id': task_id,
                    'affected_tables': list(set(affected_tables)),
                    'changes_count': changes_count,
                    'changes_summary': changes_summary,
                    'message': f'Task {task_id} processed successfully'
                }
                
            except Exception as e:
                await session.rollback()
                if 'task' in locals():
                    task.mark_failed(str(e))
                    await session.commit()
                
                return {
                    'status': 'error',
                    'message': f'Failed to process task: {str(e)}'
                }

    async def _process_attributes_with_meta(
        self,
        session: AsyncSession,
        product: Product,
        attributes: List,
        task: ManualTask
    ) -> Dict[str, Any]:
        """Process attributes with individual metadata."""
        affected_tables = []
        changes = []
        count = 0
        
        for attr_data in attributes:
            attr_name = attr_data.get('name') if hasattr(attr_data, 'get') else getattr(attr_data, 'name', None)
            attr_value = attr_data.get('value') if hasattr(attr_data, 'get') else getattr(attr_data, 'value', None)
            attr_unit = attr_data.get('unit') if hasattr(attr_data, 'get') else getattr(attr_data, 'unit', None)
            attr_notes = attr_data.get('notes') if hasattr(attr_data, 'get') else getattr(attr_data, 'notes', None)
            attr_source = attr_data.get('source_url') if hasattr(attr_data, 'get') else getattr(attr_data, 'source_url', None)
            
            if not attr_name or not attr_value:
                continue
            
            # Get or create attribute
            attribute = await session.scalar(
                select(Attribute).where(Attribute.name == attr_name)
            )
            if not attribute:
                attribute = Attribute(name=attr_name)
                session.add(attribute)
                await session.flush()
            
            # Create product attribute with individual metadata
            product_attr = ProductAttribute(
                product_id=product.product_id,
                attribute_id=attribute.id,
                value_text=str(attr_value),
                value_unit=attr_unit,
                source='manual',
                manual_task_id=task.id,
                notes=attr_notes,
                source_url=attr_source
            )
            session.add(product_attr)
            
            affected_tables.extend(['attributes', 'product_attributes'])
            changes.append({
                'attribute': attr_name,
                'value': attr_value,
                'unit': attr_unit,
                'notes': attr_notes,
                'source_url': attr_source
            })
            count += 1
        
        return {
            'affected_tables': affected_tables,
            'changes': changes,
            'count': count
        }

    async def _process_extras_with_meta(
        self,
        session: AsyncSession,
        product: Product,
        extras: List,
        task: ManualTask
    ) -> Dict[str, Any]:
        """Process extras with individual metadata."""
        affected_tables = []
        changes = []
        count = 0
        
        for extra_data in extras:
            extra_name = extra_data.get('name') if hasattr(extra_data, 'get') else getattr(extra_data, 'name', None)
            extra_value = extra_data.get('value') if hasattr(extra_data, 'get') else getattr(extra_data, 'value', None)
            extra_notes = extra_data.get('notes') if hasattr(extra_data, 'get') else getattr(extra_data, 'notes', None)
            extra_source = extra_data.get('source_url') if hasattr(extra_data, 'get') else getattr(extra_data, 'source_url', None)
            
            if not extra_name or not extra_value:
                continue
            
            product_extra = ProductExtra(
                product_id=product.product_id,
                name=extra_name,
                value=str(extra_value),
                source='manual',
                manual_task_id=task.id,
                notes=extra_notes,
                source_url=extra_source
            )
            session.add(product_extra)
            
            affected_tables.append('product_extras')
            changes.append({
                'name': extra_name,
                'value': extra_value,
                'notes': extra_notes,
                'source_url': extra_source
            })
            count += 1
        
        return {
            'affected_tables': affected_tables,
            'changes': changes,
            'count': count
        }

    async def _process_documents_with_meta(
        self,
        session: AsyncSession,
        product: Product,
        documents: List,
        task: ManualTask
    ) -> Dict[str, Any]:
        """Process documents with individual metadata."""
        affected_tables = []
        changes = []
        count = 0
        
        for doc_data in documents:
            doc_url = doc_data.get('url') if hasattr(doc_data, 'get') else getattr(doc_data, 'url', None)
            doc_type = doc_data.get('type', 'document') if hasattr(doc_data, 'get') else getattr(doc_data, 'type', 'document')
            doc_description = doc_data.get('description', '') if hasattr(doc_data, 'get') else getattr(doc_data, 'description', '')
            doc_notes = doc_data.get('notes') if hasattr(doc_data, 'get') else getattr(doc_data, 'notes', None)
            doc_source = doc_data.get('source_url') if hasattr(doc_data, 'get') else getattr(doc_data, 'source_url', None)
            
            if not doc_url:
                continue
            
            document = DocumentMedia(
                product_id=product.product_id,
                url=doc_url,
                type=doc_type,
                description=doc_description,
                source='manual',
                manual_task_id=task.id,
                notes=doc_notes,
                source_url=doc_source
            )
            session.add(document)
            
            affected_tables.append('document_media')
            changes.append({
                'url': doc_url,
                'type': doc_type,
                'description': doc_description,
                'notes': doc_notes,
                'source_url': doc_source
            })
            count += 1
        
        return {
            'affected_tables': affected_tables,
            'changes': changes,
            'count': count
        }

    async def _process_sellers_with_meta(
        self,
        session: AsyncSession,
        product: Product,
        sellers: List,
        task: ManualTask
    ) -> Dict[str, Any]:
        """Process sellers with individual metadata."""
        affected_tables = []
        changes = []
        count = 0
        
        for seller_data in sellers:
            seller_name = seller_data.get('name') if hasattr(seller_data, 'get') else getattr(seller_data, 'name', None)
            seller_type = seller_data.get('type', 'distributor') if hasattr(seller_data, 'get') else getattr(seller_data, 'type', 'distributor')
            seller_notes = seller_data.get('notes') if hasattr(seller_data, 'get') else getattr(seller_data, 'notes', None)
            seller_source = seller_data.get('source_url') if hasattr(seller_data, 'get') else getattr(seller_data, 'source_url', None)
            
            if not seller_name:
                continue
            
            # Generate seller_id
            seller_id = f"{product.product_id}_{seller_name}_{int(datetime.now().timestamp())}"
            
            product_seller = ProductSeller(
                seller_id=seller_id,
                product_id=product.product_id,
                seller_name=seller_name,
                seller_type=seller_type,
                source='manual',
                manual_task_id=task.id,
                notes=seller_notes,
                source_url=seller_source
            )
            session.add(product_seller)
            
            affected_tables.append('product_sellers')
            changes.append({
                'name': seller_name,
                'type': seller_type,
                'notes': seller_notes,
                'source_url': seller_source
            })
            count += 1
        
        return {
            'affected_tables': affected_tables,
            'changes': changes,
            'count': count
        }
