#!/usr/bin/env python3
"""
Example usage of the PDF highlight extractor.
"""

from extract_highlights import extract_pdf_highlights
import json
import pandas as pd

def main():
    # Path to your PDF file
    pdf_path = "data/tcannex-annotated-NIST.SP.800-63B-4-raw-merged.pdf"
    
    # Extract highlights
    highlights = extract_pdf_highlights(pdf_path)
    
    print(f"Found {len(highlights)} highlighted sections")
    print()
    
    # Group by annotation type
    by_type = {"Def": [], "FYI": [], "Rec": [], "Err": [], "Ref": []}
    
    for highlight in highlights:
        ann_type = highlight.get("annotation_type")
        if ann_type in by_type:
            by_type[ann_type].append(highlight)
    
    # Show examples of each type
    for ann_type, items in by_type.items():
        key = "text"
        if items:
            print(f"=== {ann_type} ({len(items)} items) ===")
            for i, item in enumerate(items[:3]):  # Show first 3 of each type
                text = item[key][:150] + "..." if len(item[key]) > 150 else item[key]
                print(f"{i+1}. Page {item['page']}: {text}")
            if len(items) > 3:
                print(f"   ... and {len(items) - 3} more")
            print()

    annotate_file = pdf_path.replace(".pdf", "").replace('data/tcannex-annotated', '')
    # Save to JSON file
    output_file = f"extracted_highlights_{annotate_file}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(highlights, f, indent=2, ensure_ascii=False)
    
    print(f"All highlights saved to {output_file}")
    
    # Save to Excel file
    excel_file = f"extracted_highlights_{annotate_file}.xlsx"
    
    # Create DataFrame with main components
    excel_data = []
    for highlight in highlights:
        excel_data.append({
            'page': highlight['page'],
            'text': highlight['text'],
            'annotation_type': highlight.get('annotation_type', 'Unknown')
        })
    
    df = pd.DataFrame(excel_data)
    
    # Save to Excel with formatting
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Highlights', index=False)
        
        # Get the workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Highlights']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            # Set width with some padding, max 100 characters for text column
            adjusted_width = min(max_length + 2, 100 if column_letter == 'B' else 20)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"All highlights saved to Excel: {excel_file}")
    print(f"Excel file contains {len(highlights)} rows with columns: page, text, annotation_type")

if __name__ == "__main__":
    main()