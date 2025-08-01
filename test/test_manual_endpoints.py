import httpx
import asyncio
import json
import os
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any, Optional, Union

# --- Configuration ---
BASE_URL = "http://localhost:8000/manual"
TEST_BATCH_ID_PREFIX = "test_batch_"
TEST_EDITOR = "test_user_script"
TEST_VALIDATOR = "test_validator_script"

# --- Test Reporting Class ---
class TestReport:
    """Collects and summarizes test results."""
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.start_time = datetime.now()

    def add_result(self, name: str, endpoint: str, status: str,
                   status_code: Optional[int] = None,
                   expected_status: Optional[int] = None,
                   error_message: Optional[str] = None,
                   response_json: Optional[Union[Dict, str]] = None,
                   details: Optional[Dict] = None):
        """Adds a single test result to the report."""
        result = {
            "name": name,
            "endpoint": endpoint,
            "status": status, # PASSED, FAILED, SKIPPED
            "status_code": status_code,
            "expected_status": expected_status,
            "error_message": error_message,
            "response_json": response_json,
            "details": details or {} # Additional details like task_id, batch_id
        }
        self.results.append(result)
        print(f"[{status}] {name}: {endpoint} -> Status: {status_code or 'N/A'}")

    def generate_summary(self):
        """Prints a summary of all test results."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        print("\n" + "="*60)
        print("                 API ENDPOINT TEST SUMMARY")
        print("="*60)
        
        passed_count = sum(1 for r in self.results if r["status"] == "PASSED")
        failed_count = sum(1 for r in self.results if r["status"] == "FAILED")
        skipped_count = sum(1 for r in self.results if r["status"] == "SKIPPED")
        total_count = len(self.results)

        print(f"\nTotal Tests Run: {total_count}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {failed_count}")
        print(f"Skipped: {skipped_count}")
        print(f"Duration: {duration}\n")

        if failed_count > 0:
            print("-" * 60)
            print("FAILED TESTS DETAILS:")
            print("-" * 60)
            for r in self.results:
                if r["status"] == "FAILED":
                    print(f"\nTest Name: {r['name']}")
                    print(f"  Endpoint: {r['endpoint']}")
                    print(f"  Status Code: {r['status_code']} (Expected: {r['expected_status']})")
                    print(f"  Error Message: {r['error_message']}")
                    if r['response_json']:
                        print(f"  Response: {json.dumps(r['response_json'], indent=2)}")
        
        print("\n" + "="*60)
        print("                 END OF REPORT")
        print("="*60)

# --- Helper for executing API requests and reporting ---
async def execute_api_test(
    client: httpx.AsyncClient,
    report: TestReport,
    name: str,
    method: str,
    path: str,
    json_data: Optional[Dict] = None,
    files: Optional[Dict] = None,
    params: Optional[Dict] = None,
    expected_status: int = 200,
    skip_if_condition: bool = False,
    skip_reason: str = ""
) -> Dict[str, Any]:
    """
    Executes an API request, reports the result, and returns the response JSON.
    Returns a dictionary of the test result for internal use.
    """
    full_url = f"{BASE_URL}{path}"
    
    if skip_if_condition:
        report.add_result(name, f"{method} {path}", "SKIPPED",
                          error_message=skip_reason)
        return {"status": "SKIPPED"}

    response_json = None
    error_message = None
    status = "FAILED"

    try:
        if method.upper() == "GET":
            response = await client.get(full_url, params=params)
        elif method.upper() == "POST":
            if files:
                response = await client.post(full_url, files=files, params=params)
            else:
                response = await client.post(full_url, json=json_data)
        elif method.upper() == "PUT":
            response = await client.put(full_url, json=json_data)
        elif method.upper() == "DELETE":
            response = await client.delete(full_url)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        try:
            response_json = response.json()
        except json.JSONDecodeError:
            response_json = response.text # Fallback to text if not JSON

        if response.status_code == expected_status:
            status = "PASSED"
        else:
            error_message = f"Unexpected status code: {response.status_code}. Response: {response_json}"

    except httpx.ConnectError as e:
        error_message = f"Connection failed: {e}"
    except httpx.RequestError as e:
        error_message = f"Request error: {e}"
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"

    report.add_result(
        name,
        f"{method} {path}",
        status,
        response.status_code if 'response' in locals() else None,
        expected_status,
        error_message,
        response_json
    )
    
    return {
        "status": status,
        "response_json": response_json,
        "status_code": response.status_code if 'response' in locals() else None
    }

# --- Main Test Runner ---
async def run_tests():
    report = TestReport()
    async with httpx.AsyncClient(timeout=30.0) as client: # Increased timeout for potentially slow operations
        print("Starting Manual Task API Endpoint Tests...\n")

        # --- Test 1: Create a simple task (part number) ---
        part_number_1 = f"PN_SCRIPT_SIMPLE_{random.randint(1000, 9999)}"
        simple_task_data_pn = {
            "part_number": part_number_1,
            "editor": TEST_EDITOR,
            "notes": "Simple task created via script for part number"
        }
        test_1_result = await execute_api_test(
            client, report, "Test 1: Create Simple Task (Part Number)", "POST",
            "/task/create/", json_data=simple_task_data_pn
        )
        task_id_1 = test_1_result["response_json"].get("task_id") if test_1_result["status"] == "PASSED" else None

        # --- Test 2: Create a simple task (product ID) ---
        # This test is dependent on having an existing product_id.
        # For robust testing, you might need to create a product first or use a known existing one.
        # For now, we'll use a dummy ID and note its potential failure.
        product_id_to_use = 1 # This might need to be a real product ID from your DB
        simple_task_data_product_id = {
            "product_id": product_id_to_use,
            "editor": TEST_EDITOR,
            "notes": "Simple task created via script for product ID"
        }
        test_2_result = await execute_api_test(
            client, report, "Test 2: Create Simple Task (Product ID)", "POST",
            "/task/create/", json_data=simple_task_data_product_id
        )
        task_id_2 = test_2_result["response_json"].get("task_id") if test_2_result["status"] == "PASSED" else None
        
        # --- Test 3: Process task data (using task_id_1) ---
        process_task_data = {
            "attributes": [
                {"name": "Voltage Range", "value": "5V-12V", "unit": "V", "notes": "Processed attribute", "source_url": "http://example.com/processed-attr"},
            ],
            "extras": [
                {"name": "Color", "value": "Blue", "notes": "Processed extra", "source_url": "http://example.com/processed-extra"}
            ],
            "documents": [
                {"url": "http://example.com/manual_processed_doc.pdf", "type": "manual", "description": "Manual processed document"}
            ]
        }
        test_3_result = await execute_api_test(
            client, report, "Test 3: Process Task Data", "POST",
            f"/task/process/{task_id_1}/", json_data=process_task_data,
            skip_if_condition=(task_id_1 is None), skip_reason="Test 1 (Create Simple Task) failed."
        )

        # --- Test 4: Create a full manual imputation task ---
        part_number_full = f"PN_SCRIPT_FULL_{random.randint(1000, 9999)}"
        full_imputation_data = {
            "part_number": part_number_full,
            "editor": TEST_EDITOR,
            "notes": "Comprehensive task creation from script",
            "source_url": "http://example.com/full-spec.html",
            "batch_id": f"{TEST_BATCH_ID_PREFIX}{int(datetime.now().timestamp())}", # Use a unique batch ID for this task
            "attributes": [
                {"name": "Resistance", "value": "100", "unit": "Ohm"},
                {"name": "Power Rating", "value": "0.25", "unit": "W"}
            ],
            "extras": [
                {"name": "Operating Temp", "value": "-40C to 85C"},
                {"name": "Tolerance", "value": "5%"}
            ],
            "documents": [
                {"url": "http://example.com/datasheet.pdf", "type": "datasheet", "description": "Main datasheet"}
            ],
            "sellers": [
                {"name": "Mouser", "type": "distributor"},
                {"name": "ManufacturerCo", "type": "manufacturer"}
            ]
        }
        test_4_result = await execute_api_test(
            client, report, "Test 4: Create Full Manual Imputation Task", "POST",
            "/imputation/", json_data=full_imputation_data
        )
        task_id_3 = test_4_result["response_json"].get("task_id") if test_4_result["status"] == "PASSED" else None
        
        # Give some time for DB writes if needed
        await asyncio.sleep(0.5)

        # --- Test 5: Get manual task history (filter by editor) ---
        test_5_result = await execute_api_test(
            client, report, "Test 5: Get Manual Task History (Filter by Editor)", "GET",
            f"/history/", params={"editor": TEST_EDITOR, "limit": 5}
        )
        
        # --- Test 6: Get manual task details (using task_id_3) ---
        test_6_result = await execute_api_test(
            client, report, "Test 6: Get Manual Task Details", "GET",
            f"/task/{task_id_3}/",
            skip_if_condition=(task_id_3 is None), skip_reason="Test 4 (Create Full Imputation Task) failed."
        )

        # --- Test 7: Validate a manual task (using task_id_3) ---
        validation_data = {
            "validator": TEST_VALIDATOR,
            "validation_notes": "All data verified and approved."
        }
        test_7_result = await execute_api_test(
            client, report, "Test 7: Validate Manual Task", "POST",
            f"/validate/{task_id_3}/", json_data=validation_data,
            skip_if_condition=(task_id_3 is None), skip_reason="Test 4 (Create Full Imputation Task) failed."
        )
        
        # Give some time for DB writes
        await asyncio.sleep(0.5)

        # --- Test 8: Update manual task metadata (using task_id_1) ---
        update_data = {
            "note": "Updated notes from script for simple task",
            "source_url": "http://example.com/updated-simple-task-source"
        }
        test_8_result = await execute_api_test(
            client, report, "Test 8: Update Manual Task Metadata", "PUT",
            f"/task/{task_id_1}/", json_data=update_data,
            skip_if_condition=(task_id_1 is None), skip_reason="Test 1 (Create Simple Task) failed."
        )

        # --- Test 9: Get tasks by filters (batch_id, status) ---
        # Use the batch ID from Test 4
        batch_id_from_test4 = full_imputation_data["batch_id"]
        test_9_result = await execute_api_test(
            client, report, "Test 9: Get Tasks by Filters (Batch ID, Status)", "GET",
            f"/tasks/", params={"batch_id": batch_id_from_test4, "status": "completed", "limit": 10}
        )
        
        # --- Test 10: Get Tasks by Filters (Editor, Last 1 day) ---
        test_10_result = await execute_api_test(
            client, report, "Test 10: Get Tasks by Filters (Editor, Last 1 day)", "GET",
            f"/tasks/", params={"editor": TEST_EDITOR, "last_updated_days": 1, "limit": 10}
        )

        # --- Test 11: Search part numbers ---
        search_query_pn_script = "PN_SCRIPT"
        test_11_result = await execute_api_test(
            client, report, "Test 11: Search Part Numbers", "GET",
            f"/partnumbers/search/", params={"query": search_query_pn_script, "limit": 5}
        )

        # --- Test 12: Get products for selection (for UI dropdowns) ---
        test_12_result = await execute_api_test(
            client, report, "Test 12: Get Products for Selection", "GET",
            f"/products/", params={"search": "PN_SCRIPT", "limit": 5}
        )
        product_id_from_search = None
        if test_12_result["status"] == "PASSED" and test_12_result["response_json"] and len(test_12_result["response_json"]) > 0:
            product_id_from_search = test_12_result["response_json"][0]["product_id"]

        # --- Test 13: Get product details by ID (using product_id_from_search) ---
        test_13_result = await execute_api_test(
            client, report, "Test 13: Get Product Details by ID", "GET",
            f"/product/{product_id_from_search}/details/",
            skip_if_condition=(product_id_from_search is None), skip_reason="Test 12 (Get Products for Selection) did not return a product ID."
        )

        # --- Test 14: Get product details by Part Number (using part_number_full) ---
        test_14_result = await execute_api_test(
            client, report, "Test 14: Get Product Details by Part Number", "GET",
            f"/partnumber/{part_number_full}/product/",
            skip_if_condition=(part_number_full is None), skip_reason="Test 4 (Create Full Imputation Task) did not provide a part number."
        )

        # --- Test 15: Get categories (root) ---
        test_15_result = await execute_api_test(
            client, report, "Test 15: Get Categories (Root)", "GET",
            f"/categories/"
        )
        category_id_to_use = None
        if test_15_result["status"] == "PASSED" and test_15_result["response_json"] and len(test_15_result["response_json"]) > 0:
            # Assuming the first category is a root or suitable parent
            category_id_to_use = test_15_result["response_json"][0]["id"]
            
        # --- Test 16: Create a new category ---
        new_category_name = f"TestCategory_{random.randint(1000, 9999)}"
        create_category_data = {
            "name": new_category_name,
            "parent_id": category_id_to_use,
            "product_category": True
        }
        test_16_result = await execute_api_test(
            client, report, "Test 16: Create a New Category", "POST",
            f"/categories/", json_data=create_category_data,
            skip_if_condition=(category_id_to_use is None), skip_reason="Test 15 (Get Categories) did not return a category ID."
        )
        new_category_id = test_16_result["response_json"].get("id") if test_16_result["status"] == "PASSED" and test_16_result["response_json"] else None
            
        # --- Test 17: Get attributes (all) ---
        test_17_result = await execute_api_test(
            client, report, "Test 17: Get Attributes (All)", "GET",
            f"/attributes/"
        )
        
        # --- Test 18: Create a new attribute and link to category ---
        new_attribute_name = f"TestAttr_{random.randint(1000, 9999)}"
        create_attribute_data = {
            "name": new_attribute_name,
            "desc": "A new test attribute",
            "category_id": new_category_id # Link to newly created category
        }
        test_18_result = await execute_api_test(
            client, report, "Test 18: Create New Attribute and Link to Category", "POST",
            f"/attributes/", json_data=create_attribute_data,
            skip_if_condition=(new_category_id is None), skip_reason="Test 16 (Create New Category) failed."
        )

        # --- Test 19: Create batch tasks ---
        batch_tasks_data = {
            "tasks": [
                {
                    "part_number": f"BATCH_PN_1_{random.randint(100,999)}",
                    "editor": TEST_EDITOR,
                    "notes": "Batch task 1",
                    "attributes": [{"name": "BatchAttr1", "value": "Val1"}]
                },
                {
                    "part_number": f"BATCH_PN_2_{random.randint(100,999)}",
                    "editor": TEST_EDITOR,
                    "notes": "Batch task 2",
                    "extras": [{"name": "BatchExtra1", "value": "ExtraVal1"}]
                }
            ],
            "batch_id": f"{TEST_BATCH_ID_PREFIX}{int(datetime.now().timestamp())}" # Unique batch ID for this batch
        }
        test_19_result = await execute_api_test(
            client, report, "Test 19: Create Batch Tasks", "POST",
            f"/batch/create/", json_data=batch_tasks_data
        )
        batch_id_from_test19 = batch_tasks_data["batch_id"] if test_19_result["status"] == "PASSED" else None
        
        # Give some time for background processing
        await asyncio.sleep(1)

        # --- Test 20: Get batch status ---
        test_20_result = await execute_api_test(
            client, report, "Test 20: Get Batch Status", "GET",
            f"/batch/{batch_id_from_test19}/status/",
            skip_if_condition=(batch_id_from_test19 is None), skip_reason="Test 19 (Create Batch Tasks) failed."
        )
            
        # --- Test 21: Import batch from CSV ---
        csv_content = f"""part_number,notes,source_url,attribute_name,attribute_value,attribute_unit,extra_name,extra_value,document_url,document_type,seller_name,seller_type
CSV_PN_1_{random.randint(100,999)},CSV task 1,http://csv.com/source1,CSV_Attr,10,unit,CSV_Extra,ABC,http://csv.com/doc1.pdf,datasheet,CSV_Seller1,distributor
CSV_PN_2_{random.randint(100,999)},CSV task 2,http://csv.com/source2,,,,,,http://csv.com/doc2.jpg,image,CSV_Seller2,manufacturer
INVALID_PN,,,,,
"""
        csv_file_data = io.BytesIO(csv_content.encode('utf-8'))
        files = {'file': ('test_tasks.csv', csv_file_data, 'text/csv')}
        csv_batch_id = f"csv_batch_{int(datetime.now().timestamp())}"
        params = {'editor': TEST_EDITOR, 'batch_id': csv_batch_id}
        test_21_result = await execute_api_test(
            client, report, "Test 21: Import Batch from CSV", "POST",
            f"/batch/import-csv/", files=files, params=params
        )

        # Give some time for background processing
        await asyncio.sleep(1)

        # --- Test 22: Advanced search ---
        advanced_search_params = {
            "query": "PN_SCRIPT",
            "editor": TEST_EDITOR,
            "date_from": (datetime.now() - timedelta(days=7)).isoformat(),
            "date_to": datetime.now().isoformat(),
            "has_attributes": True,
            "sort_by": "date_desc",
            "page_size": 10
        }
        test_22_result = await execute_api_test(
            client, report, "Test 22: Advanced Search", "GET",
            f"/search/advanced/", params=advanced_search_params
        )
        
        # --- Test 23: Delete a manual task (using task_id_2 if available) ---
        test_23_result = await execute_api_test(
            client, report, "Test 23: Delete Manual Task", "DELETE",
            f"/task/{task_id_2}/", expected_status=204, # Expect 204 No Content for successful delete
            skip_if_condition=(task_id_2 is None), skip_reason="Test 2 (Create Simple Task with Product ID) failed."
        )

        # --- Test 24: Cancel batch operation (delete all tasks in TEST_BATCH_ID from Test 19) ---
        test_24_result = await execute_api_test(
            client, report, "Test 24: Cancel Batch Operation", "DELETE",
            f"/batch/{batch_id_from_test19}/",
            skip_if_condition=(batch_id_from_test19 is None), skip_reason="Test 19 (Create Batch Tasks) failed."
        )

    report.generate_summary()

if __name__ == "__main__":
    import io
    asyncio.run(run_tests())