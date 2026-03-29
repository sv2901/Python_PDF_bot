"""
PDF Processor - Compression and A4 Resizing
Handles Ghostscript compression and PyMuPDF page resizing
"""

import subprocess
import tempfile
import os
import logging
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# A4 dimensions in points (72 points = 1 inch)
A4_WIDTH = 595
A4_HEIGHT = 842


def compress_pdf(input_path: str, output_path: str) -> bool:
    """
    Compress PDF using Ghostscript with balanced settings.
    Optimized for quality vs file size tradeoff.
    """
    try:
        gs_command = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",  # Balanced compression
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dAutoRotatePages=/None",
            "-dColorImageDownsampleType=/Bicubic",
            "-dColorImageResolution=150",
            "-dGrayImageDownsampleType=/Bicubic",
            "-dGrayImageResolution=150",
            "-dMonoImageDownsampleType=/Bicubic",
            "-dMonoImageResolution=150",
            f"-sOutputFile={output_path}",
            input_path
        ]
        
        result = subprocess.run(
            gs_command,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for large files
        )
        
        if result.returncode != 0:
            logger.error(f"Ghostscript error: {result.stderr}")
            return False
            
        return os.path.exists(output_path)
        
    except subprocess.TimeoutExpired:
        logger.error("Ghostscript timeout - file too large or complex")
        return False
    except Exception as e:
        logger.error(f"Compression error: {e}")
        return False


def resize_to_a4(input_path: str, output_path: str) -> bool:
    """
    Resize all pages to A4 dimensions using PyMuPDF.
    Maintains aspect ratio and centers content.
    """
    try:
        doc = fitz.open(input_path)
        new_doc = fitz.open()
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Create new A4 page
            new_page = new_doc.new_page(
                width=A4_WIDTH,
                height=A4_HEIGHT
            )
            
            # Get source page dimensions
            src_rect = page.rect
            src_width = src_rect.width
            src_height = src_rect.height
            
            # Calculate scale to fit A4 while maintaining aspect ratio
            scale_x = A4_WIDTH / src_width
            scale_y = A4_HEIGHT / src_height
            scale = min(scale_x, scale_y)
            
            # Calculate new dimensions
            new_width = src_width * scale
            new_height = src_height * scale
            
            # Center the content
            x_offset = (A4_WIDTH - new_width) / 2
            y_offset = (A4_HEIGHT - new_height) / 2
            
            # Define destination rectangle
            dest_rect = fitz.Rect(
                x_offset,
                y_offset,
                x_offset + new_width,
                y_offset + new_height
            )
            
            # Copy page content to new location
            new_page.show_pdf_page(dest_rect, doc, page_num)
        
        new_doc.save(output_path, garbage=4, deflate=True)
        new_doc.close()
        doc.close()
        
        return os.path.exists(output_path)
        
    except Exception as e:
        logger.error(f"Resize error: {e}")
        return False


def process_pdf(input_path: str, output_path: str) -> tuple[bool, str]:
    """
    Full PDF processing pipeline:
    1. Compress with Ghostscript
    2. Resize to A4 with PyMuPDF
    
    Returns (success, error_message)
    """
    temp_compressed = None
    
    try:
        # Create temp file for intermediate compressed PDF
        fd, temp_compressed = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        
        # Step 1: Compress
        logger.info("Starting compression...")
        if not compress_pdf(input_path, temp_compressed):
            return False, "Compression failed"
        
        compressed_size = os.path.getsize(temp_compressed)
        original_size = os.path.getsize(input_path)
        logger.info(f"Compressed: {original_size} -> {compressed_size} bytes")
        
        # Step 2: Resize to A4
        logger.info("Starting A4 resize...")
        if not resize_to_a4(temp_compressed, output_path):
            return False, "A4 resize failed"
        
        final_size = os.path.getsize(output_path)
        logger.info(f"Final size: {final_size} bytes")
        
        return True, ""
        
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return False, str(e)
        
    finally:
        # Cleanup temp file
        if temp_compressed and os.path.exists(temp_compressed):
            try:
                os.remove(temp_compressed)
            except OSError:
                pass


def get_pdf_info(file_path: str) -> dict:
    """Get basic PDF info for logging/stats."""
    try:
        doc = fitz.open(file_path)
        info = {
            "pages": len(doc),
            "size_bytes": os.path.getsize(file_path),
            "size_mb": round(os.path.getsize(file_path) / (1024 * 1024), 2)
        }
        doc.close()
        return info
    except Exception as e:
        logger.error(f"Error getting PDF info: {e}")
        return {"pages": 0, "size_bytes": 0, "size_mb": 0}
