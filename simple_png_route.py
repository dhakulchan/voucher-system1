#!/usr/bin/env python3
"""Simple PNG route test for booking 91"""

from flask import Blueprint, Response
import os
import glob
from services.pdf_image import pdf_to_long_png_bytes

# Create simple test route
simple_png_bp = Blueprint('simple_png', __name__)

@simple_png_bp.route('/test-backend-png/91')
def test_backend_png_91():
    """Test PNG generation for booking 91"""
    try:
        # Find PDF file
        pdf_patterns = [
            'static/generated/classic_quote_BK20251118WKZ4_*.pdf',
            'static/generated/classic_service_proposal_BK20251118WKZ4_*.pdf',
        ]
        
        pdf_file_path = None
        for pattern in pdf_patterns:
            matches = glob.glob(pattern)
            if matches:
                pdf_file_path = max(matches)
                break
        
        if not pdf_file_path:
            return 'No PDF found', 404
            
        # Read and convert
        with open(pdf_file_path, 'rb') as f:
            pdf_bytes = f.read()
            
        png_bytes = pdf_to_long_png_bytes(pdf_bytes)
        
        if not png_bytes:
            return 'PNG conversion failed', 500
            
        # Return PNG
        response = Response(png_bytes, mimetype='image/png')
        response.headers['Content-Disposition'] = 'inline; filename="test_backend_91.png"'
        return response
        
    except Exception as e:
        return f'Error: {str(e)}', 500

if __name__ == '__main__':
    print("Simple PNG route created")