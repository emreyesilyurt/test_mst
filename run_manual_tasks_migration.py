#!/usr/bin/env python3
"""
Simple script to run the manual_tasks table migration.

Usage:
    python run_manual_tasks_migration.py          # Run migration
    python run_manual_tasks_migration.py rollback # Rollback migration
"""

import sys
import asyncio
from src.db.migration.migrate_manual_tasks_to_new_structure import migrate_manual_tasks_table, rollback_migration


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        print("🔄 Starting rollback migration...")
        asyncio.run(rollback_migration())
    else:
        print("🚀 Starting manual_tasks table migration...")
        asyncio.run(migrate_manual_tasks_table())


if __name__ == "__main__":
    main()
