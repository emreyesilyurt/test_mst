# Workflow Orchestrator Guide

## Overview

The Workflow Orchestrator is a comprehensive system designed to intelligently manage the flow of data from BigQuery to either automated processing or manual tasks. It provides a smart decision-making engine that analyzes various factors to determine the best processing approach for each part number.

## Architecture

```
BigQuery Data → Workflow Orchestrator → Decision Engine → Task Delegation
                                                        ↓
                                            ┌─────────────────────┐
                                            │   Automation Tasks  │
                                            │   (DigiKey API)     │
                                            └─────────────────────┘
                                                        ↓
                                            ┌─────────────────────┐
                                            │   Manual Tasks      │
                                            │   (Human Review)    │
                                            └─────────────────────┘
                                                        ↓
                                            ┌─────────────────────┐
                                            │   Fallback System   │
                                            │   (Auto → Manual)   │
                                            └─────────────────────┘
```

## Key Components

### 1. WorkflowOrchestrator Class
The main orchestrator that coordinates the entire workflow process.

**Key Methods:**
- `orchestrate_workflow()`: Main entry point for workflow execution
- `get_workflow_status()`: Check status of a batch
- `get_pending_manual_tasks()`: Retrieve tasks awaiting manual processing

### 2. Decision Engine
Intelligent system that analyzes multiple factors to decide task delegation:

**Decision Criteria:**
- **Priority Score**: From BigQuery data (0.0 - 1.0)
- **Manufacturer Reliability**: Historical success rate
- **Data Completeness**: How complete the record is
- **Automation History**: Recent failures for the part number
- **Configurable Thresholds**: Customizable decision boundaries

### 3. Task Types

#### Automation Tasks
- **Trigger**: High priority score (≥0.8) or good combined score (≥0.7)
- **Process**: DigiKey API scraping via existing automation system
- **Tracking**: AutomationTask records with detailed status
- **Concurrency**: Configurable parallel processing

#### Manual Tasks
- **Trigger**: Low priority score, automation failures, or complex cases
- **Process**: Creates ManualTask records for human review
- **Data**: Includes BigQuery data and decision metadata
- **Priority**: High, Medium, Low based on analysis

### 4. Fallback System
- **Auto-Fallback**: Failed automation tasks → Manual tasks
- **Configurable**: Can be enabled/disabled
- **Tracking**: Separate batch IDs for fallback tasks

## Configuration

### WorkflowConfig Parameters

```python
@dataclass
class WorkflowConfig:
    # Automation criteria
    automation_priority_threshold: float = 0.8    # Min score for automation
    automation_max_concurrent: int = 5            # Parallel automation tasks
    automation_retry_attempts: int = 3            # Retry failed tasks
    
    # Manual task criteria  
    manual_priority_threshold: float = 0.5        # Min score for processing
    manual_batch_size: int = 50                   # Manual task batch size
    
    # Fallback criteria
    automation_failure_to_manual: bool = True     # Enable fallback
    max_automation_failures: int = 3              # Max failures before manual
    
    # Processing limits
    max_daily_tasks: int = 1000                   # Daily processing limit
    max_batch_size: int = 100                     # Max batch size
```

## Usage

### Command Line Interface

The system includes a comprehensive CLI tool (`run_workflow.py`) for easy operation:

#### 1. Run Workflow
```bash
# Basic workflow execution
python run_workflow.py run --limit 50

# Force all tasks to manual mode (for testing)
python run_workflow.py run --limit 20 --force-manual

# Force all tasks to automation mode
python run_workflow.py run --limit 30 --force-automation

# Custom priority threshold
python run_workflow.py run --limit 100 --priority-threshold 0.7

# Save results to file
python run_workflow.py run --limit 50 --output results.json
```

#### 2. Check Status
```bash
# Check workflow batch status
python run_workflow.py status batch_1234567890

# Save status to file
python run_workflow.py status batch_1234567890 --output status.json
```

#### 3. View Pending Tasks
```bash
# Get pending manual tasks
python run_workflow.py pending --limit 10

# Filter by priority
python run_workflow.py pending --limit 20 --priority high

# Save to file
python run_workflow.py pending --limit 50 --output pending_tasks.json
```

#### 4. Configuration
```bash
# Show current configuration
python run_workflow.py config --show
```

### Programmatic Usage

```python
from src.services.workflow_orchestrator import (
    run_workflow, 
    get_workflow_status, 
    get_pending_manual_tasks,
    WorkflowOrchestrator,
    WorkflowConfig
)

# Run workflow with custom configuration
config = WorkflowConfig(
    automation_priority_threshold=0.75,
    automation_max_concurrent=10
)
orchestrator = WorkflowOrchestrator(config)
results = await orchestrator.orchestrate_workflow(limit=100)

# Or use convenience functions
results = await run_workflow(limit=50, force_manual=True)
status = await get_workflow_status("batch_1234567890")
pending = await get_pending_manual_tasks(limit=20, priority="high")
```

## Decision Logic Flow

```
1. Fetch BigQuery Data
   ↓
2. For each record:
   ├─ Force type specified? → Use forced type
   ├─ Part number exists with recent failures? → Manual
   ├─ Data completeness ≥ 0.8? → Manual (complex data needs human review)
   ├─ Data completeness 0.5-0.8?
   │  ├─ Manufacturer unreliable OR priority < 0.3? → Manual
   │  └─ Good manufacturer AND decent priority? → Automation
   └─ Data completeness < 0.5?
      ├─ Priority < 0.2? → Manual (very low priority)
      └─ Priority ≥ 0.2? → Automation (automation excels at filling gaps)
   ↓
3. Execute Tasks
   ├─ Automation: Parallel DigiKey scraping
   └─ Manual: Create task records
   ↓
4. Handle Fallbacks
   └─ Failed automation → Manual tasks
```

## Data Flow

### Input (BigQuery)
- Part numbers with priority scores
- Manufacturer information
- Category data
- Specifications and documentation
- Historical data

### Processing
- Intelligent task delegation
- Parallel automation execution
- Manual task creation
- Status tracking and logging

### Output (Supabase)
- **Products**: Core product records
- **AutomationTask**: Automation tracking
- **ManualTask**: Manual task records
- **ProductAttribute**: Scraped attributes
- **DocumentMedia**: Product documentation
- **ProductExtra**: Additional product data

## Monitoring and Logging

### Batch Tracking
- Unique batch IDs for each workflow run
- Status tracking: `in_progress`, `completed`, `failed`, `completed_with_failures`
- Processing time and performance metrics

### Task Status
- **Automation**: `initialized`, `processing`, `data_finished`, `supabase_finished`, `completed`, `failed`
- **Manual**: `initialized`, `processing`, `completed`, `failed`

### Logging
- Console output with emojis for easy reading
- File-based progress logging for automation tasks
- Detailed error tracking and reporting

## Error Handling

### Automation Failures
- Retry logic with exponential backoff
- Automatic fallback to manual tasks
- Error categorization and reporting

### Manual Task Failures
- Validation before task creation
- Error logging and recovery
- Batch operation rollback on critical failures

## Best Practices

### 1. Start Small
```bash
# Test with small batches first
python run_workflow.py run --limit 10 --force-manual
```

### 2. Monitor Progress
```bash
# Check status regularly
python run_workflow.py status batch_1234567890
```

### 3. Handle Manual Tasks
```bash
# Review pending tasks
python run_workflow.py pending --priority high
```

### 4. Adjust Configuration
- Monitor success rates
- Adjust thresholds based on performance
- Scale concurrency based on system capacity

## Integration Points

### Existing Systems
- **BigQuery Service**: Data source integration
- **TaskAutomator**: Automation execution
- **ManualImputationService**: Manual task handling
- **Database Models**: Data persistence

### APIs and Services
- **DigiKey API**: Product data scraping
- **Supabase**: Data storage
- **BigQuery**: Data source

## Troubleshooting

### Common Issues

1. **No BigQuery Data**
   - Check BigQuery connection
   - Verify priority thresholds
   - Ensure data exists in source table

2. **Automation Failures**
   - Check DigiKey API connectivity
   - Verify part number formats
   - Review error logs

3. **Manual Task Creation Issues**
   - Check database connectivity
   - Verify product/part number relationships
   - Review session management

### Debug Mode
```python
# Enable detailed logging
orchestrator = WorkflowOrchestrator()
orchestrator.task_automator.silent = False
```

## Future Enhancements

### Planned Features
- **Machine Learning**: Improve decision accuracy
- **Real-time Monitoring**: Dashboard for workflow status
- **Advanced Scheduling**: Cron-based workflow execution
- **Performance Analytics**: Success rate tracking
- **Custom Rules Engine**: User-defined decision rules

### Scalability
- **Distributed Processing**: Multi-node execution
- **Queue Management**: Redis/RabbitMQ integration
- **Load Balancing**: Dynamic resource allocation

## Support

For issues or questions:
1. Check the logs in `automation_progress.log`
2. Review the workflow status using the CLI
3. Examine pending manual tasks for patterns
4. Adjust configuration parameters as needed

## Examples

### Complete Workflow Example
```bash
# 1. Run workflow
python run_workflow.py run --limit 100 --output workflow_results.json

# 2. Check status
python run_workflow.py status batch_1234567890

# 3. Handle manual tasks
python run_workflow.py pending --priority high --limit 20

# 4. Review configuration
python run_workflow.py config --show
```

This workflow system provides a robust, scalable solution for intelligently processing electronic component data while maintaining flexibility for both automated and manual processing paths.
