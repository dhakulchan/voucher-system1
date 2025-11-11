import fitz  # PyMuPDF
from typing import List
from PIL import Image
import io
import os
from utils.logging_config import get_logger

logger = get_logger(__name__)


def pdf_page_count(pdf_bytes: bytes) -> int:
    """Get number of pages in PDF bytes."""
    if not pdf_bytes:
        return 0
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        count = len(doc)
        doc.close()
        return count
    except Exception as e:
        logger.error(f"Failed to count PDF pages: {e}")
        return 0


def pdf_page_to_png_bytes(pdf_bytes: bytes, page_index: int, zoom: float = 2.0) -> bytes:
    """Render a single page to PNG bytes with high quality.

    Args:
        pdf_bytes: PDF content as bytes
        page_index: 0-based page index
        zoom: Zoom factor for rendering (2.0 = 200% = high quality)
    
    Returns:
        bytes: PNG image data
    """
    if not pdf_bytes:
        return b""
    
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if page_index < 0 or page_index >= len(doc):
            doc.close()
            return b""
        
        # High quality rendering matrix
        matrix = fitz.Matrix(zoom, zoom)
        page = doc.load_page(page_index)
        
        # Render with high quality settings
        pix = page.get_pixmap(
            matrix=matrix, 
            alpha=False,  # No transparency for better compression
            colorspace=fitz.csRGB  # Ensure RGB colorspace
        )
        
        png_bytes = pix.tobytes("png")
        doc.close()
        
        logger.debug(f"✅ Rendered page {page_index} to PNG ({len(png_bytes):,} bytes)")
        return png_bytes
        
    except Exception as e:
        logger.error(f"❌ Failed to render page {page_index} to PNG: {e}")
        return b""


def pdf_to_png_bytes_list(pdf_bytes: bytes, zoom: float = 2.0) -> List[bytes]:
    """Convert entire PDF bytes to list of PNG bytes (one per page) with optimization."""
    if not pdf_bytes:
        return []
    
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        matrix = fitz.Matrix(zoom, zoom)
        out: List[bytes] = []
        
        for i in range(len(doc)):
            try:
                page = doc.load_page(i)
                pix = page.get_pixmap(
                    matrix=matrix, 
                    alpha=False,
                    colorspace=fitz.csRGB
                )
                png_bytes = pix.tobytes("png")
                out.append(png_bytes)
                logger.debug(f"✅ Page {i+1}/{len(doc)} rendered ({len(png_bytes):,} bytes)")
            except Exception as e:
                logger.error(f"❌ Failed to render page {i}: {e}")
                out.append(b"")  # Add empty bytes to maintain index
        
        doc.close()
        logger.info(f"🎯 Converted PDF to {len(out)} PNG pages")
        return out
        
    except Exception as e:
        logger.error(f"❌ Failed to convert PDF to PNG list: {e}")
        return []


def pdf_to_long_png_bytes(pdf_bytes: bytes, zoom: float = 2.0, page_spacing: int = 20) -> bytes:
    """Convert multi-page PDF to a single long PNG by stacking pages vertically.
    
    Args:
        pdf_bytes: PDF content as bytes
        zoom: Zoom factor for rendering (default 2.0 for high quality)
        page_spacing: Spacing between pages in pixels (default 20)
    
    Returns:
        bytes: Single PNG with all pages stacked vertically
    """
    if not pdf_bytes:
        return b""
    
    # Get all pages as PNG bytes
    png_pages = pdf_to_png_bytes_list(pdf_bytes, zoom)
    if not png_pages:
        return b""
    
    # If only one page, return it directly
    if len(png_pages) == 1:
        return png_pages[0]
    
    # Open all PNG images
    images = []
    total_width = 0
    total_height = 0
    
    for png_bytes in png_pages:
        img = Image.open(io.BytesIO(png_bytes))
        images.append(img)
        total_width = max(total_width, img.width)
        total_height += img.height
    
    # Add spacing between pages (except for the last page)
    total_height += page_spacing * (len(images) - 1)
    
    # Create new image with white background
    combined = Image.new('RGB', (total_width, total_height), 'white')
    
    # Paste each page
    y_offset = 0
    for img in images:
        # Center the image horizontally if it's narrower than total_width
        x_offset = (total_width - img.width) // 2
        combined.paste(img, (x_offset, y_offset))
        y_offset += img.height + page_spacing
    
    # Convert to bytes
    output_buffer = io.BytesIO()
    combined.save(output_buffer, format='PNG', optimize=True)
    return output_buffer.getvalue()
