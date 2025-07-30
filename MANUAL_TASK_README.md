# Manual Task System v2.0

A comprehensive manual data imputation system for electronic components with REST API endpoints, batch operations, and a web interface.

## 🆕 What's New in v2.0

### Batch Operations
- **Bulk Task Creation**: Create multiple tasks in a single API call
- **CSV Import**: Upload CSV files to create tasks automatically
- **Batch Status Tracking**: Monitor progress of batch operations
- **Batch Cancellation**: Cancel or delete entire batches

### Advanced Search
- **Multi-Filter Search**: Search with multiple criteria simultaneously
- **Pagination Support**: Handle large result sets efficiently
- **Sorting Options**: Sort by relevance, name, or date
- **Attribute/Document Filtering**: Filter by presence of attributes or documents

### Enhanced UI
- **Batch Operations Test Interface**: Interactive testing for new endpoints
- **Real-time Progress Monitoring**: Track batch operation progress
- **CSV Template Generation**: Download sample CSV files
- **Advanced Search Interface**: User-friendly search with multiple filters

## Overview

This system allows users to manually add, edit, and manage product data for electronic components. It provides:

- **Manual Task Creation**: Create tasks to add/update product attributes, extras, documents, and sellers
- **Batch Operations**: Process multiple tasks efficiently with bulk operations
- **Part Number Search**: Search and filter part numbers with related product information
- **Product Details**: View complete product information including all related data
- **Task Management**: Track, filter, and validate manual tasks
- **CSV Import/Export**: Import tasks from CSV files and export results
- **Automation Integration**: Works alongside the existing automation system

## Features

### Core Manual Task Operations
- `POST /manual/imputation/` - Create a new manual imputation task
- `GET /manual/history/` - Get manual task history with filtering
- `GET /manual/task/{task_id}/` - Get specific task details
- `PUT /manual/task/{task_id}/` - Update task metadata
- `DELETE /manual/task/{task_id}/` - Delete a task
- `POST /manual/validate/{task_id}/` - Validate a manual task

### 🆕 Batch Operations (New in v2.0)
- `POST /manual/batch/create/` - Create multiple tasks in one operation
- `POST /manual/batch/import-csv/` - Import tasks from CSV files
- `GET /manual/batch/{batch_id}/status/` - Check batch operation status
- `DELETE /manual/batch/{batch_id}/` - Cancel/delete batch operations

### Enhanced Search and Filtering
- `GET /manual/tasks/` - Get tasks with advanced filtering (product_id, part_number, last_updated_days, status, editor, batch_id)
- `GET /manual/partnumbers/search/` - Search part numbers with related product info
- `GET /manual/search/advanced/` - 🆕 Advanced search with multiple filters and pagination
- `GET /manual/product/{product_id}/details/` - Get complete product details
- `GET /manual/partnumber/{part_number}/product/` - Get product details by part number

### Workflow Management
- `POST /manual/task/create/` - Create simple task with minimal information
- `POST /manual/task/process/` - Process task with detailed data and individual metadata

### Category and Attribute Management
- `GET /manual/categories/` - Get categories with optional parent filtering
- `POST /manual/categories/` - Create new categories
- `GET /manual/attributes/` - Get attributes with optional category filtering
- `POST /manual/attributes/` - Create new attributes and link to categories

## Data Types Supported

1. **Product Attributes**: Technical specifications with units and individual metadata
2. **Product Extras**: Additional product information with source tracking
3. **Documents & Media**: Datasheets, images, and other documentation with individual metadata
4. **Sellers**: Distributors, manufacturers, and brokers with source tracking

## Task Tracking

Each manual task includes:
- **Status Tracking**: initialized → processing → data_finished → supabase_finished → completed
- **Editor Information**: Who made the changes
- **Validation**: Approval workflow with validator tracking
- **Traceability**: Notes, source URLs, and batch IDs
- **Change Summary**: Detailed tracking of what was modified
- **Individual Metadata**: Each item can have its own notes and source URL

## Installation & Setup

### Prerequisites

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv pydantic
```

### Environment Variables

Create a `.env` file with your database configuration:

```env
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=5432
DB_NAME=your_db_name
PROD_SCHEMA=production
TEST_SCHEMA=test
RUN_MODE=prod
```

### Running the Server

```bash
python run_server.py
```

The server will start on `http://localhost:8000`

- API Documentation: `http://localhost:8000/docs`
- Manual Task Interface: Open `src/ui/manual_task_interface.html` in your browser
- 🆕 Batch Operations Test: Open `src/ui/batch_operations_test.html` in your browser

## Usage Examples

### 1. Create a Manual Task

```python
import requests

data = {
    "part_number": "STM32F407VGT6",
    "editor": "john_doe",
    "notes": "Adding missing specifications",
    "source_url": "https://www.st.com/resource/en/datasheet/stm32f407vg.pdf",
    "attributes": [
        {
            "name": "Supply Voltage",
            "value": "1.8V to 3.6V",
            "unit": "V"
        },
        {
            "name": "Flash Memory",
            "value": "1024",
            "unit": "KB"
        }
    ],
    "extras": [
        {
            "name": "Package Type",
            "value": "LQFP-100"
        }
    ],
    "documents": [
        {
            "url": "https://www.st.com/resource/en/datasheet/stm32f407vg.pdf",
            "type": "datasheet",
            "description": "Official STM32F407VG datasheet"
        }
    ],
    "sellers": [
        {
            "name": "Digi-Key",
            "type": "distributor"
        }
    ]
}

response = requests.post("http://localhost:8000/manual/imputation/", json=data)
print(response.json())
```

### 2. 🆕 Create Batch Tasks

```python
batch_data = {
    "tasks": [
        {
            "part_number": "STM32F103C8T6",
            "editor": "engineer1",
            "notes": "ARM Cortex-M3 microcontroller",
            "attributes": [
                {"name": "Core", "value": "ARM Cortex-M3"},
                {"name": "Flash", "value": "64KB", "unit": "KB"}
            ]
        },
        {
            "part_number": "STM32F407VGT6",
            "editor": "engineer1",
            "notes": "ARM Cortex-M4 microcontroller",
            "attributes": [
                {"name": "Core", "value": "ARM Cortex-M4"},
                {"name": "Flash", "value": "1024KB", "unit": "KB"}
            ]
        }
    ],
    "batch_id": "stm32_batch_001"
}

response = requests.post("http://localhost:8000/manual/batch/create/", json=batch_data)
print(response.json())
```

### 3. 🆕 Import from CSV

```python
with open('tasks.csv', 'rb') as f:
    files = {'file': f}
    params = {
        'editor': 'engineer1',
        'batch_id': 'csv_import_001'
    }
    
    response = requests.post(
        'http://localhost:8000/manual/batch/import-csv/',
        files=files,
        params=params
    )
    print(response.json())
```

**CSV Format:**
```csv
part_number,notes,source_url,attribute_name,attribute_value,attribute_unit
STM32F103,ARM Cortex-M3,https://st.com,Core,ARM Cortex-M3,
LM358N,Op-amp,https://ti.com,Supply Voltage,3V to 32V,V
```

### 4. 🆕 Advanced Search

```python
params = {
    'query': 'STM32',
    'manufacturer_id': 123,
    'has_attributes': True,
    'sort_by': 'date_desc',
    'page_size': 50
}

response = requests.get("http://localhost:8000/manual/search/advanced/", params=params)
results = response.json()

print(f"Found {results['total_found']} results")
for item in results['results']:
    print(f"Part: {item['part_number']}, Attributes: {item['attributes_count']}")
```

### 5. 🆕 Monitor Batch Status

```python
batch_id = "batch_1703123456"
response = requests.get(f"http://localhost:8000/manual/batch/{batch_id}/status/")
status = response.json()

print(f"Batch Progress: {status['completion_percentage']:.1f}%")
print(f"Completed: {status['completed']}/{status['total_tasks']}")
```

### 6. Search Part Numbers

```python
response = requests.get("http://localhost:8000/manual/partnumbers/search/?query=STM32&limit=10")
results = response.json()

for part in results:
    print(f"Part: {part['part_number']}, Manufacturer: {part['manufacturer']}")
```

### 7. Get Product Details

```python
# By product ID
response = requests.get("http://localhost:8000/manual/product/12345/details/")

# By part number
response = requests.get("http://localhost:8000/manual/partnumber/STM32F407VGT6/product/")

product = response.json()
print(f"Product: {product['part_number']}")
print(f"Attributes: {len(product['attributes'])}")
print(f"Documents: {len(product['documents'])}")
```

### 8. Filter Tasks

```python
# Get tasks by editor in last 7 days
response = requests.get("http://localhost:8000/manual/tasks/?editor=john_doe&last_updated_days=7")

# Get completed tasks for a specific batch
response = requests.get("http://localhost:8000/manual/tasks/?batch_id=batch_001&status=completed")

# Get tasks for a specific part number
response = requests.get("http://localhost:8000/manual/tasks/?part_number=STM32&status=completed")
```

## Web Interface

The system includes comprehensive web interfaces:

### Main Manual Task Interface (`src/ui/manual_task_interface.html`)
- **Simple Task Tab**: Create basic tasks with minimal information
- **Process Task Tab**: Add detailed data with individual metadata
- **Full Create Tab**: Complete task creation with all data types
- **Search Parts Tab**: Search part numbers with autocomplete
- **View Tasks Tab**: Filter and view tasks with detailed information
- **Product Details Tab**: Look up complete product information

### 🆕 Batch Operations Interface (`src/ui/batch_operations_test.html`)
- **Batch Create Tab**: Create multiple tasks with JSON input
- **CSV Import Tab**: Upload CSV files with drag-and-drop support
- **Advanced Search Tab**: Multi-criteria search with real-time results
- **Batch Status Tab**: Monitor batch progress with visual indicators

## Database Schema

The system integrates with existing tables:

- **manual_tasks**: Task tracking and metadata with batch support
- **part_numbers**: Part number registry with manual tracking fields
- **products**: Main product table
- **product_attributes**: Technical specifications with task references
- **product_extras**: Additional product data with task references
- **document_media**: Files and documentation with task references
- **product_sellers**: Distributor and seller information with task references
- **manufacturers**: Manufacturer data
- **categories**: Product categorization with hierarchy support
- **attributes**: Attribute definitions with category linking

## Integration with Automation

The manual task system works alongside the existing automation system:

- **Shared Data Model**: Uses the same database tables and structure
- **Source Tracking**: Manual vs automated data is clearly marked
- **Task References**: Links to both manual_task_id and automation_task_id
- **Validation Workflow**: Manual tasks can be validated before going live
- **Batch Processing**: Both manual and automated tasks support batch operations

## API Response Examples

### Successful Task Creation
```json
{
    "status": "success",
    "task_id": 12345,
    "part_number": "STM32F407VGT6",
    "affected_tables": ["part_numbers", "products", "product_attributes", "document_media"],
    "changes_count": 4,
    "message": "Manual imputation completed for STM32F407VGT6"
}
```

### 🆕 Batch Creation Response
```json
{
    "status": "success",
    "batch_id": "batch_1703123456",
    "summary": {
        "total": 100,
        "successful": 95,
        "failed": 5
    },
    "results": [
        {
            "index": 0,
            "task_id": 12346,
            "part_number": "STM32F103",
            "status": "success"
        }
    ]
}
```

### 🆕 CSV Import Response
```json
{
    "status": "success",
    "batch_id": "csv_import_1703123456",
    "total_rows": 1000,
    "successful": 950,
    "failed": 50,
    "validation_errors": [
        {
            "row": 15,
            "error": "Part number is required"
        }
    ],
    "created_tasks": [12347, 12348, 12349]
}
```

### 🆕 Advanced Search Results
```json
{
    "results": [
        {
            "part_number": "STM32F407VGT6",
            "product_id": 67890,
            "manufacturer": "STMicroelectronics",
            "category": "Microcontrollers",
            "last_updated": "2025-01-28T20:15:00Z",
            "attributes_count": 15,
            "documents_count": 3
        }
    ],
    "pagination": {
        "page": 1,
        "page_size": 25,
        "total_count": 150,
        "total_pages": 6
    },
    "total_found": 150
}
```

### Part Number Search Results
```json
[
    {
        "part_number": "STM32F407VGT6",
        "part_number_id": 12345,
        "product_id": 67890,
        "manufacturer": "STMicroelectronics",
        "manufacturer_id": 123,
        "category": "Microcontrollers",
        "category_id": "uuid-here",
        "notes": "Updated with latest specs",
        "source_url": "https://example.com/datasheet",
        "last_manual_update": "2025-01-28T20:15:00Z",
        "manual_editor": "john_doe",
        "created_date": "2025-01-20T10:00:00Z",
        "updated_date": "2025-01-28T20:15:00Z"
    }
]
```

## Error Handling

The API provides detailed error messages:

```json
{
    "status": "error",
    "message": "Failed to process manual imputation: Part number is required",
    "part_number": "STM32F407VGT6"
}
```

### 🆕 Batch Error Handling
```json
{
    "status": "partial_success",
    "batch_id": "batch_1703123456",
    "summary": {
        "total": 10,
        "successful": 8,
        "failed": 2
    },
    "results": [
        {
            "index": 5,
            "part_number": "INVALID_PART",
            "status": "failed",
            "error": "Part number validation failed"
        }
    ]
}
```

## Security Considerations

- **Input Validation**: All inputs are validated using Pydantic schemas
- **SQL Injection Protection**: Uses SQLAlchemy ORM with parameterized queries
- **File Upload Security**: CSV files are validated and sanitized
- **Batch Size Limits**: Prevents resource exhaustion attacks
- **Editor Tracking**: All changes are attributed to specific users
- **Audit Trail**: Complete history of all changes with timestamps

## Performance

- **Async Operations**: All database operations are asynchronous
- **Connection Pooling**: Efficient database connection management
- **Batch Processing**: Support for bulk operations with optimized queries
- **Pagination**: Configurable limits on search results
- **Caching**: Strategic caching for frequently accessed data
- **Indexing**: Database indexes on commonly filtered fields

## Troubleshooting

### Common Issues

1. **Database Connection**: Check environment variables and database accessibility
2. **Missing Dependencies**: Ensure all required packages are installed
3. **CORS Issues**: The API allows all origins for development (configure for production)
4. **Large Datasets**: Use pagination and filtering to manage large result sets
5. **Batch Timeouts**: Monitor batch operations and adjust size for performance
6. **CSV Format Issues**: Use provided templates and validate before import

### Logging

The system provides detailed logging for debugging:
- Task creation and processing steps
- Database operations and errors
- Validation results and failures
- Batch operation progress and errors
- File upload and processing status

## Future Enhancements

### Planned Features
- **Real-time Progress**: WebSocket updates for batch operations
- **Export Functionality**: Export search results to various formats
- **Template System**: Save and reuse task configurations
- **Workflow Management**: Multi-step approval processes
- **Advanced Validation**: Custom validation rules per product category
- **Data Quality Metrics**: Completeness and accuracy tracking
- **Integration APIs**: Connect with external data sources
- **Mobile Interface**: Responsive design for mobile devices
- **Scheduled Operations**: Queue batches for later processing

### Performance Improvements
- **Background Processing**: Async processing for large batches
- **Parallel Processing**: Process multiple tasks simultaneously
- **Compression**: Compress large batch payloads
- **Advanced Caching**: Redis integration for better performance

## Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Use the batch operations test interface for debugging
3. Review the error messages and logs
4. Verify database connectivity and permissions
5. Test with the provided web interfaces first

## Version History

### v2.0 (Current)
- ✅ Batch operations with CSV import
- ✅ Advanced search with multiple filters
- ✅ Batch status monitoring and cancellation
- ✅ Enhanced UI with batch operations test interface
- ✅ Individual metadata for all data types
- ✅ Improved error handling and validation

### v1.0
- ✅ Basic manual task creation and management
- ✅ Part number search and product details
- ✅ Category and attribute management
- ✅ Task validation workflow
- ✅ Web interface for manual operations