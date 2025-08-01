# Quick Setup Guide for Manual Task System

## Step 1: Install Dependencies

```bash
python install_dependencies.py
```

Or manually:
```bash
pip install fastapi uvicorn[standard] sqlalchemy psycopg2-binary python-dotenv pydantic
```

## Step 2: Configure Environment

Make sure your `.env` file has:

```env
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=5432
DB_NAME=your_db_name
PROD_SCHEMA=production
TEST_SCHEMA=test
RUN_MODE=test
```

**⚠️ IMPORTANT: Set `RUN_MODE=test` for testing!**

## Step 3: Update Test Schema

```bash
python update_test_schema.py
```

This will:
- ✅ Preserve: manufacturers, categories, attributes, category_attributes
- 🔄 Recreate: products, part_numbers, document_media, product_sellers, product_attributes, product_extras, automation_tasks, manual_tasks
- 🔒 Only works on test schema (production is protected)

## Step 4: Start the Server

```bash
python run_server.py
```

## Step 5: Test the System

1. **API Documentation**: http://localhost:8000/docs
2. **Web Interface**: Open `src/ui/manual_task_interface.html` in your browser
3. **API Base URL**: http://localhost:8000/manual

## Available Endpoints

### Core Operations
- `POST /manual/imputation/` - Create manual task
- `GET /manual/tasks/` - Get tasks with filtering
- `GET /manual/partnumbers/search/` - Search part numbers
- `GET /manual/product/{id}/details/` - Get product details
- `GET /manual/partnumber/{pn}/product/` - Get product by part number

### Task Management
- `GET /manual/history/` - Task history
- `GET /manual/task/{id}/` - Get specific task
- `PUT /manual/task/{id}/` - Update task
- `DELETE /manual/task/{id}/` - Delete task
- `POST /manual/validate/{id}/` - Validate task

## Testing Examples

### Create a Manual Task
```bash
curl -X POST "http://localhost:8000/manual/imputation/" \
  -H "Content-Type: application/json" \
  -d '{
    "part_number": "TEST123",
    "editor": "test_user",
    "notes": "Test manual task",
    "attributes": [
      {
        "name": "Voltage",
        "value": "3.3V",
        "unit": "V"
      }
    ]
  }'
```

### Search Part Numbers
```bash
curl "http://localhost:8000/manual/partnumbers/search/?query=TEST&limit=10"
```

### Get Tasks
```bash
curl "http://localhost:8000/manual/tasks/?editor=test_user&limit=10"
```

## Troubleshooting

### Database Connection Issues
- Check your `.env` file credentials
- Ensure database is accessible
- Verify schema exists

### Missing Dependencies
```bash
python install_dependencies.py
```

### Schema Issues
```bash
python update_test_schema.py
```

### Server Won't Start
- Check if port 8000 is available
- Verify all dependencies are installed
- Check database connection

## Safety Features

- ✅ Production schema protection
- ✅ Input validation with Pydantic
- ✅ SQL injection protection with SQLAlchemy
- ✅ Comprehensive error handling
- ✅ Audit trail for all changes

## Next Steps

1. Test basic functionality with the web interface
2. Try the API endpoints with curl or Postman
3. Check the database to see created records
4. Validate the manual task workflow
5. Test integration with existing automation system

## Support

- Check `MANUAL_TASK_README.md` for detailed documentation
- Use the web interface for easier testing
- Check API docs at `/docs` for interactive testing
- Review error messages in server logs
