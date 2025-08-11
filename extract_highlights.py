#!/usr/bin/env python3
"""
PDF Highlight Extractor for TCAnnex Annotated Documents

This script extracts highlighted text from PDF files based on highlight colors
and maps them to annotation types (Def, FYI, Rec) as defined in the TCAnnex legend.

Requirements:
    pip install PyMuPDF

Usage:
    from extract_highlights import extract_pdf_highlights
    highlights = extract_pdf_highlights("path/to/pdf/file.pdf")
"""

import fitz  # PyMuPDF
import pymupdf
from typing import List, Dict, Tuple, Optional
_threshold_intersection = 0.6  # if the intersection is large enough.


def _check_contain(r_word, points):
    """If `r_word` is contained in the rectangular area.

    The area of the intersection should be large enough compared to the
    area of the given word.

    Args:
        r_word (fitz.Rect): rectangular area of a single word.
        points (list): list of points in the rectangular area of the
            given part of a highlight.

    Returns:
        bool: whether `r_word` is contained in the rectangular area.
    """
    # `r` is mutable, so everytime a new `r` should be initiated.
    r = fitz.Quad(points).rect
    r.intersect(r_word)

    if r.get_area() >= r_word.get_area() * _threshold_intersection:
        contain = True
    else:
        contain = False
    return contain


def _extract_annot(annot, words_on_page):
    """Extract words in a given highlight.

    Args:
        annot (fitz.Annot): [description]
        words_on_page (list): [description]

    Returns:
        str: words in the entire highlight.
    """
    quad_points = annot.vertices
    quad_count = int(len(quad_points) / 4)
    sentences = ['' for i in range(quad_count)]
    for i in range(quad_count):
        points = quad_points[i * 4: i * 4 + 4]
        words = [
            w for w in words_on_page if
            _check_contain(fitz.Rect(w[:4]), points)
        ]
        sentences[i] = ' '.join(w[4] for w in words)
    sentence = ' '.join(sentences)

    return sentence

def extract_pdf_highlights(pdf_path: str) -> List[Dict]:
    """
    Extract highlighted text from a PDF file and return as a list of dictionaries.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        List[Dict]: List of dictionaries containing highlighted text and metadata.
                   Each dictionary contains:
                   - page: Page number (1-based)
                   - text: The highlighted text
                   - color: RGB color tuple
                   - annotation_type: Mapped type (Def, FYI, Rec, or None)
                   - coordinates: Dictionary with x0, y0, x1, y1 coordinates
    """
    
    # Color mappings based on TCAnnex annotation types
    # Based on actual colors found in the PDF
    COLOR_MAPPINGS = {
        # Actual colors from the PDF
        (1.0, 0.76, 0.0): "FYI",     # Gold/orange - FYI (Other important info) 
        (0.77, 0.98, 0.45): "Def",   # Light green - Def (Definition)
        (0.22, 0.9, 1.0): "Rec",     # Light blue - Rec (Recommendation)
        (1.0, 0.38, 0.0): "Err",   # Red - Err (Error)
        (0.86, 0.67, 1.0): "Ref",    # Light purple - Ref (Reference to external resource)
        
        # Add tolerance variants for similar colors
        (1.0, 0.75, 0.0): "FYI",     # Gold variant
        (1.0, 0.77, 0.0): "FYI",     # Gold variant
        (0.97, 0.39, 0.39): "Err",   # Red variant
        (0.76, 0.98, 0.45): "Def",   # Green variant
        (0.78, 0.98, 0.45): "Def",   # Green variant  
        (0.21, 0.9, 1.0): "Rec",     # Blue variant
        (0.23, 0.9, 1.0): "Rec",     # Blue variant
        (0.96, 0.39, 0.39): "Err",   # Red variant
        (0.98, 0.39, 0.39): "Err",   # Red variant
        (0.85, 0.67, 1.0): "Ref",    # Purple variant
        (0.87, 0.67, 1.0): "Ref",    # Purple variant
    }
    
    def normalize_color(color: Tuple[float, ...]) -> Tuple[float, ...]:
        """Normalize color values to a consistent format."""
        if not color:
            return (0.0, 0.0, 0.0)
        
        # Ensure we have RGB values
        if len(color) >= 3:
            return tuple(round(c, 2) for c in color[:3])
        elif len(color) == 1:
            # Grayscale to RGB
            return (round(color[0], 2),) * 3
        else:
            return (0.0, 0.0, 0.0)
    
    def map_color_to_type(color: Tuple[float, ...]) -> Optional[str]:
        """Map a color to an annotation type."""
        normalized_color = normalize_color(color)
        
        # Direct match
        if normalized_color in COLOR_MAPPINGS:
            return COLOR_MAPPINGS[normalized_color]
        
        # Fuzzy match with tolerance
        tolerance = 0.15
        for mapped_color, annotation_type in COLOR_MAPPINGS.items():
            if all(abs(c1 - c2) <= tolerance for c1, c2 in zip(normalized_color, mapped_color)):
                return annotation_type
        
        return None

    def is_quality_text(text: str) -> bool:
        """Check if text is meaningful content (not URLs, page numbers, etc.)."""
        if not text or len(text.strip()) < 2:
            return False
        
        text_lower = text.lower().strip()
        
        # Filter out URLs and web content
        url_indicators = ['http', 'www.', '.com', '.org', '.gov', '.edu', 'doi.org']
        if any(indicator in text_lower for indicator in url_indicators):
            return False
        
        # Filter out common artifacts
        artifacts = ['page', 'figure', 'table', 'appendix', 'section']
        if text_lower in artifacts:
            return False
        
        # Filter out pure numbers or minimal content
        if text.strip().isdigit() or len(text.strip()) < 3:
            return False
        
        # Check for reasonable ratio of letters to other characters
        letters = sum(1 for c in text if c.isalpha())
        if len(text) > 0 and letters / len(text) < 0.3:
            return False
        
        return True
    
    def extract_text_from_rect(page: fitz.Page, annot: fitz.Annot, rect: fitz.Rect) -> str:
        """Extract text from a specific rectangle on a page with improved precision."""
        try:
            #Get all the word blocks in the associated rectangle. Order them by y then x coordinates
            #word_blocks = sorted(page.get_text("words", clip=rect), key=lambda w:(w[1], w[0]))
            word_blocks = page.get_text("words", clip=rect)
            #Extract only the words which are highlighted, nothing more.
            clip_text = _extract_annot(annot, word_blocks)

            if not clip_text or not is_quality_text(clip_text):
                return ""
            
            # Clean up the extracted text
            import re
            # Remove excessive whitespace but preserve single spaces and line breaks
            clean_text = re.sub(r'[ \t]+', ' ', clip_text)  # Multiple spaces/tabs to single space
            clean_text = re.sub(r'\n+', ' ', clean_text)    # Multiple newlines to single space
            clean_text = clean_text.strip()
            
            return clean_text
            
        except Exception as e:
            print(f"Error extracting text from rectangle: {e}")
            return ""
    
    # Main extraction logic
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return []
    
    all_highlights = []
    
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            try:
                # Get all annotations on the page
                annotations = page.annots()
                
                for annot in annotations:
                    # Check if this is a highlight annotation
                    if annot.type[0] == pymupdf.PDF_ANNOT_HIGHLIGHT:
                        # Get the highlight color
                        color = annot.colors.get("stroke") or annot.colors.get("fill")
                        
                        # Get the highlighted area
                        rect = annot.rect

                        # Extract the text in the highlighted area
                        highlighted_text = extract_text_from_rect(page, annot, rect)

                        if highlighted_text.strip():
                            # Map color to annotation type
                            annotation_type = map_color_to_type(color)
                            
                            highlight_data = {
                                "page": page_num + 1,  # 1-based page numbering
                                "text": highlighted_text.strip(),
                                #"matthew_text": annot.get_textbox(rect).strip(),
                                "color": normalize_color(color) if color else None,
                                "annotation_type": annotation_type,
                                "coordinates": {
                                    "x0": rect.x0,
                                    "y0": rect.y0,
                                    "x1": rect.x1,
                                    "y1": rect.y1
                                },
                                "highlight_area": rect.width * rect.height,
                                "text_length": len(highlighted_text.strip())
                            }
                            all_highlights.append(highlight_data)
            
            except Exception as e:
                print(f"Error processing page {page_num + 1}: {e}")
                continue
    
    finally:
        doc.close()
    
    return all_highlights




def get_highlight_color_stats(pdf_path: str) -> Dict:
    """
    Get statistics about colors used for highlights in the PDF.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        Dict: Dictionary mapping color tuples to occurrence counts
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return {}
    
    color_stats = {}
    
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            annotations = page.annots()
            
            for annot in annotations:
                if annot.type[1] == "Highlight":
                    color = annot.colors.get("stroke") or annot.colors.get("fill")
                    if color:
                        normalized_color = tuple(round(c, 2) for c in color[:3]) if len(color) >= 3 else (0.0, 0.0, 0.0)
                        color_stats[normalized_color] = color_stats.get(normalized_color, 0) + 1
    
    finally:
        doc.close()
    
    return color_stats


if __name__ == "__main__":
    # Example usage
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python extract_highlights.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Extract highlights
    highlights = extract_pdf_highlights(pdf_path)
    
    # Show results
    output_data = {
        "pdf_file": pdf_path,
        "total_highlights": len(highlights),
        "highlights": highlights,
        "annotation_types": {
            "Def": "Definition",
            "FYI": "Other important info", 
            "Rec": "Recommendation"
        }
    }
    
    print(json.dumps(output_data, indent=2, ensure_ascii=False))
    
    # Also show color statistics
    print("\nColor Statistics:", file=sys.stderr)
    color_stats = get_highlight_color_stats(pdf_path)
    for color, count in color_stats.items():
        print(f"  {color}: {count} highlights", file=sys.stderr)