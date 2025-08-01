#!/usr/bin/env python3
"""
Install required dependencies for the manual task system.
"""

import subprocess
import sys

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} installed successfully")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Failed to install {package}")
        return False

def main():
    print("📦 Installing dependencies for Manual Task System...")
    
    # Required packages
    packages = [
        "fastapi",
        "uvicorn[standard]",
        "sqlalchemy",
        "psycopg2-binary",
        "python-dotenv",
        "pydantic"
    ]
    
    failed_packages = []
    
    for package in packages:
        print(f"\n📥 Installing {package}...")
        if not install_package(package):
            failed_packages.append(package)
    
    print(f"\n{'='*50}")
    if failed_packages:
        print(f"❌ Failed to install: {', '.join(failed_packages)}")
        print(f"Please install them manually using: pip install {' '.join(failed_packages)}")
    else:
        print("🎉 All dependencies installed successfully!")
        print("\n🔧 Next steps:")
        print("1. Set up your .env file with database credentials")
        print("2. Set RUN_MODE=test in .env")
        print("3. Run: python scripts/update_test_schema.py")
        print("4. Run: python run_server.py")

if __name__ == "__main__":
    main()
