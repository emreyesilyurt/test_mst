"""
Test script for the Manual Data Imputation System.
This script demonstrates how to use the manual imputation service and API.
"""

import asyncio
import json
from datetime import datetime
from src.services.manual_imputation_service import ManualImputationService


async def test_manual_imputation_service():
    """Test the ManualImputationService with sample data."""
    
    print("🚀 Testing Manual Data Imputation System")
    print("=" * 50)
    
    # Initialize the service
    service = ManualImputationService()
    
    # Test 1: Create a manual task with product attributes
    print("\n📋 Test 1: Adding Product Attributes")
    print("-" * 30)
    
    result1 = await service.create_manual_task(
        part_number="LM358N",
        editor="test_engineer",
        data_updates={
            "attributes": [
                {
                    "name": "Supply Voltage",
                    "value": "3V to 32V",
                    "unit": "V"
                },
                {
                    "name": "Input Offset Voltage",
                    "value": "2mV",
                    "unit": "mV"
                },
                {
                    "name": "Slew Rate",
                    "value": "0.3V/μs",
                    "unit": "V/μs"
                }
            ]
        },
        notes="Added specifications from TI datasheet",
        source_url="https://www.ti.com/lit/ds/symlink/lm358.pdf"
    )
    
    print(f"✅ Result: {result1['status']}")
    print(f"📝 Message: {result1['message']}")
    if result1['status'] == 'success':
        print(f"🆔 Task ID: {result1['task_id']}")
        print(f"📊 Changes Count: {result1['changes_count']}")
        print(f"🗂️ Affected Tables: {', '.join(result1['affected_tables'])}")
    
    # Test 2: Create a manual task with product extras and documents
    print("\n📝 Test 2: Adding Product Extras and Documents")
    print("-" * 40)
    
    result2 = await service.create_manual_task(
        part_number="STM32F103C8T6",
        editor="test_engineer",
        data_updates={
            "extras": [
                {
                    "name": "Package Type",
                    "value": "LQFP-48"
                },
                {
                    "name": "Core",
                    "value": "ARM Cortex-M3"
                },
                {
                    "name": "Flash Memory",
                    "value": "64KB"
                }
            ],
            "documents": [
                {
                    "url": "https://www.st.com/resource/en/datasheet/stm32f103c8.pdf",
                    "type": "datasheet",
                    "description": "STM32F103C8T6 Official Datasheet"
                },
                {
                    "url": "https://www.st.com/resource/en/reference_manual/rm0008.pdf",
                    "type": "document",
                    "description": "Reference Manual"
                }
            ]
        },
        notes="Added microcontroller specifications and documentation",
        source_url="https://www.st.com/en/microcontrollers-microprocessors/stm32f103c8.html"
    )
    
    print(f"✅ Result: {result2['status']}")
    print(f"📝 Message: {result2['message']}")
    if result2['status'] == 'success':
        print(f"🆔 Task ID: {result2['task_id']}")
        print(f"📊 Changes Count: {result2['changes_count']}")
        print(f"🗂️ Affected Tables: {', '.join(result2['affected_tables'])}")
    
    # Test 3: Create a manual task with sellers
    print("\n🏪 Test 3: Adding Sellers")
    print("-" * 20)
    
    result3 = await service.create_manual_task(
        part_number="ATMEGA328P-PU",
        editor="test_engineer",
        data_updates={
            "sellers": [
                {
                    "name": "Digi-Key",
                    "type": "distributor"
                },
                {
                    "name": "Mouser Electronics",
                    "type": "distributor"
                },
                {
                    "name": "Microchip Technology",
                    "type": "manufacturer"
                }
            ]
        },
        notes="Added major distributors and manufacturer",
        batch_id="test_batch_001"
    )
    
    print(f"✅ Result: {result3['status']}")
    print(f"📝 Message: {result3['message']}")
    if result3['status'] == 'success':
        print(f"🆔 Task ID: {result3['task_id']}")
        print(f"📊 Changes Count: {result3['changes_count']}")
        print(f"🗂️ Affected Tables: {', '.join(result3['affected_tables'])}")
    
    # Test 4: Get manual task history
    print("\n📚 Test 4: Retrieving Task History")
    print("-" * 30)
    
    history = await service.get_manual_task_history(
        editor="test_engineer",
        limit=10
    )
    
    print(f"📊 Found {len(history)} manual tasks")
    for task in history[:3]:  # Show first 3 tasks
        print(f"  🆔 Task {task['id']}: {task['part_number']} by {task['editor']}")
        print(f"     📅 Created: {task['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"     📊 Status: {task['status']}")
        print(f"     ✅ Validated: {'Yes' if task['validated'] else 'No'}")
    
    # Test 5: Validate a manual task (if we have tasks)
    if history and len(history) > 0:
        print("\n✅ Test 5: Validating a Manual Task")
        print("-" * 35)
        
        task_to_validate = history[0]
        validation_result = await service.validate_manual_task(
            task_id=task_to_validate['id'],
            validator="test_supervisor",
            validation_notes="Verified data accuracy and completeness"
        )
        
        print(f"✅ Validation Result: {validation_result['status']}")
        print(f"📝 Message: {validation_result['message']}")
    
    # Test 6: Comprehensive test with all data types
    print("\n🎯 Test 6: Comprehensive Manual Task")
    print("-" * 35)
    
    comprehensive_result = await service.create_manual_task(
        part_number="ESP32-WROOM-32",
        editor="test_engineer",
        data_updates={
            "attributes": [
                {
                    "name": "CPU",
                    "value": "Xtensa dual-core 32-bit LX6",
                    "unit": None
                },
                {
                    "name": "Flash Memory",
                    "value": "4MB",
                    "unit": "MB"
                },
                {
                    "name": "WiFi",
                    "value": "802.11 b/g/n",
                    "unit": None
                }
            ],
            "extras": [
                {
                    "name": "Bluetooth",
                    "value": "v4.2 BR/EDR and BLE"
                },
                {
                    "name": "GPIO Pins",
                    "value": "34"
                },
                {
                    "name": "Operating Temperature",
                    "value": "-40°C to +85°C"
                }
            ],
            "documents": [
                {
                    "url": "https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf",
                    "type": "datasheet",
                    "description": "ESP32-WROOM-32 Datasheet"
                },
                {
                    "url": "https://docs.espressif.com/projects/esp-idf/en/latest/esp32/",
                    "type": "document",
                    "description": "ESP-IDF Programming Guide"
                }
            ],
            "sellers": [
                {
                    "name": "Espressif Systems",
                    "type": "manufacturer"
                },
                {
                    "name": "Adafruit",
                    "type": "retailer"
                },
                {
                    "name": "SparkFun",
                    "type": "retailer"
                }
            ]
        },
        notes="Comprehensive data entry for ESP32 module including all specifications, documentation, and suppliers",
        source_url="https://www.espressif.com/en/products/modules/esp32",
        batch_id="comprehensive_test_batch"
    )
    
    print(f"✅ Result: {comprehensive_result['status']}")
    print(f"📝 Message: {comprehensive_result['message']}")
    if comprehensive_result['status'] == 'success':
        print(f"🆔 Task ID: {comprehensive_result['task_id']}")
        print(f"📊 Changes Count: {comprehensive_result['changes_count']}")
        print(f"🗂️ Affected Tables: {', '.join(comprehensive_result['affected_tables'])}")
    
    print("\n🎉 Manual Data Imputation System Test Complete!")
    print("=" * 50)


def test_api_request_format():
    """Show example API request formats."""
    
    print("\n🌐 API Request Examples")
    print("=" * 25)
    
    # Example 1: Basic manual imputation request
    basic_request = {
        "part_number": "LM741",
        "editor": "john.doe",
        "notes": "Added basic op-amp specifications",
        "source_url": "https://www.ti.com/lit/ds/symlink/lm741.pdf",
        "attributes": [
            {
                "name": "Supply Voltage",
                "value": "±15V",
                "unit": "V"
            },
            {
                "name": "Input Offset Voltage",
                "value": "1mV",
                "unit": "mV"
            }
        ],
        "extras": [
            {
                "name": "Package",
                "value": "DIP-8"
            }
        ]
    }
    
    print("📋 Basic Manual Imputation Request:")
    print("POST /manual/imputation/")
    print("Content-Type: application/json")
    print()
    print(json.dumps(basic_request, indent=2))
    
    # Example 2: Validation request
    validation_request = {
        "validator": "supervisor.name",
        "validation_notes": "Data verified against manufacturer specifications"
    }
    
    print("\n✅ Task Validation Request:")
    print("POST /manual/validate/123/")
    print("Content-Type: application/json")
    print()
    print(json.dumps(validation_request, indent=2))
    
    # Example 3: History query
    print("\n📚 Task History Query:")
    print("GET /manual/history/?part_number=LM741&editor=john.doe&limit=50")
    
    # Example 4: Statistics query
    print("\n📊 Statistics Query:")
    print("GET /manual/stats/")


if __name__ == "__main__":
    print("🧪 Manual Data Imputation System - Test Suite")
    print("=" * 55)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show API examples first
    test_api_request_format()
    
    # Run async tests
    try:
        asyncio.run(test_manual_imputation_service())
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        print("💡 Make sure your database is configured and accessible")
        print("💡 Check that all required environment variables are set")
    
    print(f"\n⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
