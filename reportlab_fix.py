#!/usr/bin/env python3
"""
ReportLab Fix - แก้ไขปัญหา usedforsecurity parameter ใน Python 3.8.18
"""

import hashlib
import sys

def patch_reportlab_md5():
    """Patch ReportLab's MD5 usage for Python 3.8 compatibility"""
    try:
        # Test if usedforsecurity is supported
        hashlib.md5(usedforsecurity=False)
        print("✅ MD5 usedforsecurity parameter is supported")
        return True
    except TypeError:
        print("⚠️ MD5 usedforsecurity not supported, applying patch...")
        
        # Store original md5 function
        original_md5 = hashlib.md5
        
        def patched_md5(*args, **kwargs):
            """Patched md5 function that removes usedforsecurity parameter"""
            # Remove usedforsecurity if present
            kwargs.pop('usedforsecurity', None)
            return original_md5(*args, **kwargs)
        
        # Replace md5 function
        hashlib.md5 = patched_md5
        
        # Also patch the hashlib module for import statements
        import builtins
        original_import = builtins.__import__
        
        def patched_import(name, *args, **kwargs):
            """Patch imports to apply MD5 fix automatically"""
            module = original_import(name, *args, **kwargs)
            
            if name == 'hashlib' or (name.startswith('reportlab') and hasattr(module, 'md5')):
                if hasattr(module, 'md5'):
                    module.md5 = patched_md5
            
            return module
        
        builtins.__import__ = patched_import
        print("✅ ReportLab MD5 patch applied successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to apply ReportLab patch: {e}")
        return False

if __name__ == "__main__":
    patch_reportlab_md5()