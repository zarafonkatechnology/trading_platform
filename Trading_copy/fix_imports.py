# fix_imports.py
"""
Fix import issues by creating missing directories and files
"""

import os
import sys
from pathlib import Path

def create_missing_dirs():
    """Create missing directories"""
    dirs = [
        'src/mt4_gateway',
        'src/core',
        'src/api/routes',
        'src/api/models',
        'src/api/middleware',
        'src/api/dependencies',
        'src/database',
        'src/services',
        'src/agents',
        'src/brokers',
        'src/core_engine',
        'src/queue',
        'src/cache',
        'src/web',
        'src/telegram',
        'src/utils',
        'tests/test_api',
        'tests/test_services',
        'tests/test_integration'
    ]
    
    for d in dirs:
        path = Path(d)
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {d}")

def create_init_files():
    """Create __init__.py files"""
    init_files = [
        'src/__init__.py',
        'src/mt4_gateway/__init__.py',
        'src/core/__init__.py',
        'src/api/__init__.py',
        'src/api/routes/__init__.py',
        'src/api/models/__init__.py',
        'src/api/middleware/__init__.py',
        'src/api/dependencies/__init__.py',
        'src/database/__init__.py',
        'src/services/__init__.py',
        'src/agents/__init__.py',
        'src/brokers/__init__.py',
        'src/core_engine/__init__.py',
        'src/queue/__init__.py',
        'src/cache/__init__.py',
        'src/web/__init__.py',
        'src/telegram/__init__.py',
        'src/utils/__init__.py',
        'tests/__init__.py',
        'tests/test_api/__init__.py',
        'tests/test_services/__init__.py',
        'tests/test_integration/__init__.py'
    ]
    
    for file in init_files:
        path = Path(file)
        if not path.exists():
            path.write_text('')
            print(f"✅ Created: {file}")

def main():
    print("🔧 Fixing import issues...")
    print("=" * 50)
    
    create_missing_dirs()
    create_init_files()
    
    print("\n" + "=" * 50)
    print("✅ All import issues fixed!")
    print("Now try running your tests again:")
    print("  pytest tests/ -v")

if __name__ == "__main__":
    main()