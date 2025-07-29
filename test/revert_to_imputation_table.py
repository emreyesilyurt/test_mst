#!/usr/bin/env python3
"""
Alternative approach: Revert AutomationTask to use existing imputation_tasks table.
This approach keeps your existing data intact and just updates the model to use the old table.
"""

def revert_instructions():
    """
    Instructions to revert AutomationTask to use imputation_tasks table.
    """
    print("Option 2: Revert to Use Existing imputation_tasks Table")
    print("=" * 60)
    print()
    print("This approach will:")
    print("✅ Keep all your existing data intact")
    print("✅ Use the existing imputation_tasks table")
    print("✅ Add new columns to the existing table structure")
    print("✅ No data migration needed")
    print()
    print("Steps to implement:")
    print()
    print("1. Update AutomationTask model in src/db/models/models.py:")
    print("   Change:")
    print("   __tablename__ = tables.get('automation_tasks').split('.')[1]")
    print("   __table_args__ = {'schema': tables.get('automation_tasks').split('.')[0]}")
    print()
    print("   Back to:")
    print("   __tablename__ = tables.get('imputation_tasks').split('.')[1]")
    print("   __table_args__ = {'schema': tables.get('imputation_tasks').split('.')[0]}")
    print()
    print("2. Update foreign key references in related models:")
    print("   Change all:")
    print("   ForeignKey(f\"{tables.get('automation_tasks')}.id\")")
    print()
    print("   Back to:")
    print("   ForeignKey(f\"{tables.get('imputation_tasks')}.id\")")
    print()
    print("3. Run database update to add new columns:")
    print("   python add_new_columns_to_imputation_tasks.py")
    print()
    print("This approach preserves all your existing data and relationships!")

if __name__ == "__main__":
    revert_instructions()
