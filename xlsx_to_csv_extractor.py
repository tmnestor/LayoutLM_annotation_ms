#!/usr/bin/env python3
"""
Excel to CSV Column Extractor

This script reads all Excel (.xlsx) files in a directory and extracts specified
columns by name to CSV files. Fully configurable via command line arguments.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd


def extract_columns_from_xlsx(
    xlsx_file: Path,
    columns: List[str],
    output_dir: Path,
    sheet_name: Optional[str] = None,
    keep_original_name: bool = False
) -> bool:
    """
    Extract specified columns from an Excel file and save to CSV.
    
    Args:
        xlsx_file: Path to the Excel file
        columns: List of column names to extract
        output_dir: Directory to save the CSV file
        sheet_name: Name of the sheet to read (None for first sheet)
        keep_original_name: If True, keep original filename; if False, add suffix
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Read the Excel file
        df = pd.read_excel(xlsx_file, sheet_name=sheet_name, engine='xlsxwriter')  # noqa: PD901
        
        # Check if all requested columns exist
        missing_columns = [col for col in columns if col not in df.columns]
        if missing_columns:
            print(f"Warning: {xlsx_file.name} - Missing columns: {missing_columns}")
            # Use only available columns
            available_columns = [col for col in columns if col in df.columns]
            if not available_columns:
                print(f"Error: {xlsx_file.name} - No requested columns found")
                return False
            columns = available_columns
        
        # Extract the specified columns
        extracted_df = df[columns]
        
        # Generate output filename
        if keep_original_name:
            output_filename = xlsx_file.stem + '.csv'
        else:
            output_filename = xlsx_file.stem + '_extracted.csv'
        
        output_path = output_dir / output_filename
        
        # Save to CSV
        extracted_df.to_csv(output_path, index=False)
        print(f"Extracted {len(columns)} columns from {xlsx_file.name} -> {output_filename}")
        return True
        
    except Exception as e:
        print(f"Error processing {xlsx_file.name}: {str(e)}")
        return False


def process_directory(
    input_dir: Path,
    output_dir: Path,
    columns: List[str],
    sheet_name: Optional[str] = None,
    keep_original_name: bool = False,
    recursive: bool = False
) -> None:
    """
    Process all Excel files in a directory.
    
    Args:
        input_dir: Directory containing Excel files
        output_dir: Directory to save CSV files
        columns: List of column names to extract
        sheet_name: Name of the sheet to read (None for first sheet)
        keep_original_name: If True, keep original filename; if False, add suffix
        recursive: If True, search subdirectories recursively
    """
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find Excel files
    if recursive:
        xlsx_files = list(input_dir.rglob('*.xlsx'))
    else:
        xlsx_files = list(input_dir.glob('*.xlsx'))
    
    if not xlsx_files:
        print(f"No Excel files found in {input_dir}")
        return
    
    print(f"Found {len(xlsx_files)} Excel file(s)")
    
    successful = 0
    failed = 0
    
    for xlsx_file in xlsx_files:
        if extract_columns_from_xlsx(
            xlsx_file, columns, output_dir, sheet_name, keep_original_name
        ):
            successful += 1
        else:
            failed += 1
    
    print("\nProcessing complete:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")


def list_columns_in_file(xlsx_file: Path, sheet_name: Optional[str] = None) -> None:
    """
    List all column names in an Excel file.
    
    Args:
        xlsx_file: Path to the Excel file
        sheet_name: Name of the sheet to read (None for first sheet)
    """
    try:
        df = pd.read_excel(xlsx_file, sheet_name=sheet_name, engine='xlsxwriter')  # noqa: PD901
        print(f"\nColumns in {xlsx_file.name}:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")
        print(f"\nTotal columns: {len(df.columns)}")
        
    except Exception as e:
        print(f"Error reading {xlsx_file.name}: {str(e)}")


def main() -> None:
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Extract specified columns from Excel files and save as CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract specific columns from all xlsx files in current directory
  python xlsx_to_csv_extractor.py --columns "Name,Email,Phone" --input-dir .

  # Extract columns with custom output directory
  python xlsx_to_csv_extractor.py --columns "ID,Status" --input-dir data/ --output-dir output/

  # Extract from specific sheet and keep original filenames
  python xlsx_to_csv_extractor.py --columns "A,B,C" --sheet "Sheet2" --keep-original-name

  # List columns in a specific file
  python xlsx_to_csv_extractor.py --list-columns file.xlsx

  # Process directories recursively
  python xlsx_to_csv_extractor.py --columns "Name,Value" --recursive
        """
    )
    
    # Main operation mode
    parser.add_argument(
        '--columns',
        type=str,
        help='Comma-separated list of column names to extract (e.g., "Name,Email,Phone")'
    )
    
    # Input/output paths
    parser.add_argument(
        '--input-dir',
        type=str,
        default='.',
        help='Directory containing Excel files (default: current directory)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='.',
        help='Directory to save CSV files (default: current directory)'
    )
    
    # Excel-specific options
    parser.add_argument(
        '--sheet',
        type=str,
        help='Name of the Excel sheet to read (default: first sheet)'
    )
    
    # Output options
    parser.add_argument(
        '--keep-original-name',
        action='store_true',
        help='Keep original filename for CSV output (default: add "_extracted" suffix)'
    )
    
    parser.add_argument(
        '--recursive',
        action='store_true',
        help='Search for Excel files recursively in subdirectories'
    )
    
    # Utility options
    parser.add_argument(
        '--list-columns',
        type=str,
        metavar='FILE',
        help='List all column names in the specified Excel file and exit'
    )
    
    args = parser.parse_args()
    
    # Handle list-columns mode
    if args.list_columns:
        xlsx_file = Path(args.list_columns)
        if not xlsx_file.exists():
            print(f"Error: File not found: {xlsx_file}")
            sys.exit(1)
        list_columns_in_file(xlsx_file, args.sheet)
        return
    
    # Validate required arguments for extraction mode
    if not args.columns:
        print("Error: --columns is required for extraction mode")
        print("Use --list-columns FILE to see available columns")
        sys.exit(1)
    
    # Parse column names
    columns = [col.strip() for col in args.columns.split(',')]
    if not columns or not columns[0]:
        print("Error: No valid column names provided")
        sys.exit(1)
    
    # Validate paths
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        sys.exit(1)
    
    if not input_dir.is_dir():
        print(f"Error: Input path is not a directory: {input_dir}")
        sys.exit(1)
    
    output_dir = Path(args.output_dir)
    
    print(f"Input directory: {input_dir.absolute()}")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Columns to extract: {columns}")
    if args.sheet:
        print(f"Sheet: {args.sheet}")
    if args.recursive:
        print("Recursive search: enabled")
    
    # Process the directory
    process_directory(
        input_dir=input_dir,
        output_dir=output_dir,
        columns=columns,
        sheet_name=args.sheet,
        keep_original_name=args.keep_original_name,
        recursive=args.recursive
    )


if __name__ == '__main__':
    main()