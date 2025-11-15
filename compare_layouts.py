#!/usr/bin/env python3
"""
Compare layouts - สร้าง PDF/PNG และเปิดไฟล์เปรียบเทียบ
"""

import os
import subprocess
from generate_service_proposal_sample import generate_sample_proposal

def compare_layouts():
    """Generate new layout and open for comparison"""
    
    print("🔄 Generating new layout...")
    pdf_path, png_path = generate_sample_proposal()
    
    if png_path and os.path.exists(png_path):
        print(f"✅ Generated: {png_path}")
        
        # Open the new PNG
        subprocess.run(['open', png_path])
        
        # Also open the target sample if available
        if os.path.exists('target_sample.pdf'):
            print("📋 Opening target sample for comparison...")
            subprocess.run(['open', 'target_sample.pdf'])
        
        print("\n📊 Comparison ready!")
        print("🔍 Check if the layout matches the target sample")
        
    else:
        print("❌ Failed to generate PNG")

if __name__ == "__main__":
    compare_layouts()
