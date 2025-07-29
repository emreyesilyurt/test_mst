# Manual Task System

A comprehensive manual data imputation system for electronic components with REST API endpoints and a web interface.

## Overview

This system allows users to manually add, edit, and manage product data for electronic components. It provides:

- **Manual Task Creation**: Create tasks to add/update product attributes, extras, documents, and sellers
- **Part Number Search**: Search and filter part numbers with related product information
- **Product Details**: View complete product information including all related data
- **Task Management**: Track, filter, and validate manual tasks
- **Automation Integration**: Works alongside the existing automation system

## Features

### API Endpoints

#### Core Manual Task Operations
- `POST /manual/imputation/` - Create a new manual imputation task
- `GET /manual/history/` - Get manual task history with filtering
- `GET /manual/task/{task_id}/` - Get specific task details
- `PUT /manual/task/{task_id}/` - Update task metadata
- `DELETE /manual/task/{task_id}/` - Delete a task
- `POST /manual/validate/{task_id}/` - Validate a manual task

#### Enhanced Search and Filtering
- `GET /manual/tasks/` - Get tasks with advanced filtering (product_id, part_number, last_updated_days, status, editor)
- `GET /manual/partnumbers/search/` - Search part numbers with related product info
- `GET /manual/product/{product_id}/details/` - Get complete product details
- `GET /manual/partnumber/{part_number}/product/` - Get product details by part number

### Data Types Supported

1. **Product Attributes**: Technical specifications with units
2. **Product Extras**: Additional product information
3. **Documents & Media**: Datasheets, images, and other documentation
4. **Sellers**: Distributors, manufacturers, and brokers

### Task Tracking

Each manual task includes:
- **Status Tracking**: initialized → processing → data_finished → supabase_finished → completed
- **Editor Information**: Who made the changes
- **Validation**: Approval workflow with validator tracking
- **Traceability**: Notes, source URLs, and batch IDs
- **Change Summary**: Detailed tracking of what was modified

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

### 2. Search Part Numbers

```python
response = requests.get("http://localhost:8000/manual/partnumbers/search/?query=STM32&limit=10")
results = response.json()

for part in results:
    print(f"Part: {part['part_number']}, Manufacturer: {part['manufacturer']}")
```

### 3. Get Product Details

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

### 4. Filter Tasks

```python
# Get tasks by editor in last 7 days
response = requests.get("http://localhost:8000/manual/tasks/?editor=john_doe&last_updated_days=7")

# Get completed tasks for a specific part number
response = requests.get("http://localhost:8000/manual/tasks/?part_number=STM32&status=completed")
```

## Web Interface

The system includes a comprehensive web interface (`src/ui/manual_task_interface.html`) with:

### Create Task Tab
- Form for entering part number and editor information
- Dynamic fields for adding attributes, extras, documents, and sellers
- Real-time validation and error handling

### Search Parts Tab
- Search part numbers with autocomplete
- Click to select and auto-fill in create form
- Display manufacturer and category information

### View Tasks Tab
- Filter tasks by editor, status, and date range
- View detailed task information and history
- JSON formatted results for technical users

### Product Details Tab
- Look up products by ID or part number
- Display complete product information
- Organized sections for attributes, extras, documents, and sellers

## Database Schema

The system integrates with existing tables:

- **manual_tasks**: Task tracking and metadata
- **part_numbers**: Part number registry with manual tracking fields
- **products**: Main product table
- **product_attributes**: Technical specifications
- **product_extras**: Additional product data
- **document_media**: Files and documentation
- **product_sellers**: Distributor and seller information
- **manufacturers**: Manufacturer data
- **categories**: Product categorization
- **attributes**: Attribute definitions

## Integration with Automation

The manual task system works alongside the existing automation system:

- **Shared Data Model**: Uses the same database tables and structure
- **Source Tracking**: Manual vs automated data is clearly marked
- **Task References**: Links to both manual_task_id and automation_task_id
- **Validation Workflow**: Manual tasks can be validated before going live

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

## Security Considerations

- **Input Validation**: All inputs are validated using Pydantic schemas
- **SQL Injection Protection**: Uses SQLAlchemy ORM with parameterized queries
- **Editor Tracking**: All changes are attributed to specific users
- **Audit Trail**: Complete history of all changes with timestamps

## Performance

- **Async Operations**: All database operations are asynchronous
- **Connection Pooling**: Efficient database connection management
- **Batch Processing**: Support for batch operations with batch_id
- **Pagination**: Configurable limits on search results

## Troubleshooting

### Common Issues

1. **Database Connection**: Check environment variables and database accessibility
2. **Missing Dependencies**: Ensure all required packages are installed
3. **CORS Issues**: The API allows all origins for development (configure for production)
4. **Large Datasets**: Use pagination and filtering to manage large result sets

### Logging

The system provides detailed logging for debugging:
- Task creation and processing steps
- Database operations and errors
- Validation results and failures

## Future Enhancements

- **Bulk Import**: CSV/Excel file upload for batch operations
- **Advanced Validation**: Custom validation rules per product category
- **Workflow Management**: Multi-step approval processes
- **Data Quality Metrics**: Completeness and accuracy tracking
- **Integration APIs**: Connect with external data sources
- **Mobile Interface**: Responsive design for mobile devices

## Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review the error messages and logs
3. Verify database connectivity and permissions
4. Test with the provided web interface first
