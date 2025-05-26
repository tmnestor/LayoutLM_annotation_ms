#!/usr/bin/env python3
"""
Simplified script to prepare annotation files and tracking data.

This script handles only the essential tasks needed for annotators:
1. Reads the list of images to annotate from annotation_images.csv
2. Generates label files for only those specific images
3. Creates a master tracking file with those images

The master file includes hyperlinks to images and label files on a network share.
"""

import argparse
import csv
import logging
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Import xlsxwriter and fail early if not available
try:
    import xlsxwriter
except ImportError:
    print("Error: XlsxWriter package not available. Please install it with 'pip install xlsxwriter'.")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger('prepare_annotations')


# ============================================================================
# File and Directory Utilities
# ============================================================================

def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory
        
    Returns:
        Path object for the directory
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def validate_file_exists(file_path: Union[str, Path], error_msg: str = None) -> Path:
    """
    Validate that a file exists and return its Path object.
    
    Args:
        file_path: Path to the file to validate
        error_msg: Custom error message if file is not found
        
    Returns:
        Path object for the file
        
    Raises:
        SystemExit if the file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        if error_msg is None:
            error_msg = f"Error: File not found: {file_path}"
        logger.error(error_msg)
        sys.exit(1)
    return path


def validate_directory_exists(dir_path: Union[str, Path], error_msg: str = None) -> Path:
    """
    Validate that a directory exists and return its Path object.
    
    Args:
        dir_path: Path to the directory to validate
        error_msg: Custom error message if directory is not found
        
    Returns:
        Path object for the directory
        
    Raises:
        SystemExit if the directory doesn't exist
    """
    path = Path(dir_path)
    if not path.is_dir():
        if error_msg is None:
            error_msg = f"Error: Directory not found: {dir_path}"
        logger.error(error_msg)
        sys.exit(1)
    return path


# ============================================================================
# CSV Parsing and Processing
# ============================================================================

def load_images_to_annotate(images_file: Union[str, Path]) -> List[Tuple[str, str]]:
    """
    Load the list of images that need to be annotated.

    Args:
        images_file: Path to CSV file with case_id and page_id columns

    Returns:
        List of (case_id, page_id) tuples
    """
    # Validate the file exists
    file_path = validate_file_exists(images_file, f"Error: Images file not found: {images_file}")
    
    images = []

    with file_path.open("r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)

        # Verify required columns
        if "case_id" not in reader.fieldnames or "page_id" not in reader.fieldnames:
            logger.error("Error: Images file must contain 'case_id' and 'page_id' columns")
            sys.exit(1)

        for row in reader:
            images.append((row["case_id"], row["page_id"]))

    logger.info(f"Loaded {len(images)} images to annotate from {images_file}")
    return images


def get_filter_column(headers: List[str]) -> Tuple[int, str]:
    """
    Determine the filter column index and name from CSV headers.
    
    Args:
        headers: List of CSV header column names
        
    Returns:
        Tuple of (column_index, column_name)
    """
    column_index = 0  # Default to first column
    column_name = "image_id"  # Default name

    if "page_id" in headers:
        column_index = headers.index("page_id")
        column_name = "page_id"
    elif "image_id" in headers:
        # For backward compatibility with older files that use image_id
        column_index = headers.index("image_id")
        column_name = "image_id"
    
    return column_index, column_name


def extract_bbox_coordinates(bbox_str: str) -> List[str]:
    """
    Extract x1, y1, x2, y2 coordinates from a bounding box string.
    
    Args:
        bbox_str: String in format "(x1, y1, x2, y2)"
        
    Returns:
        List of coordinate strings [x1, y1, x2, y2]
    """
    coords = []
    
    # Use regex to extract the coordinates from format like "(10, 20, 100, 40)"
    match = re.search(r'\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', bbox_str)
    if match:
        coords = list(match.groups())
    else:
        # If format doesn't match, use empty values
        coords = ['', '', '', '']
    
    return coords


def build_file_path(base_dir: str, case_id: str, template_parts: List[str], 
                   template: Optional[str] = None, **kwargs) -> str:
    """
    Build a file path using the provided template or default components.
    
    Args:
        base_dir: Base directory path
        case_id: Case ID
        template_parts: List of path parts to append to case_dir if no template
        template: Optional template string for custom paths
        **kwargs: Additional variables for template formatting
        
    Returns:
        Constructed file path
    """
    case_dir = str(Path(base_dir) / case_id)
    
    if template:
        # Use the provided template
        return template.format(case_id=case_id, case_dir=case_dir, **kwargs)
    else:
        # Build path from components
        return str(Path(case_dir, *template_parts))


# ============================================================================
# Image Processing Functions
# ============================================================================

def copy_image_files(
    cases_dir: str, images_dir: str, images: List[Tuple[str, str]], 
    args: Optional[Any] = None
) -> List[Tuple[str, str, str]]:
    """
    Copy image files to a separate directory for easier transfer.

    Args:
        cases_dir: Root directory containing case directories
        images_dir: Directory where image files will be copied
        images: List of (case_id, page_id) tuples to process
        args: Command line arguments containing path templates

    Returns:
        List of (case_id, page_id, copied_image_path) tuples for successfully copied files
    """
    # Create images directory if it doesn't exist
    ensure_directory_exists(images_dir)

    successful_copies = []
    failed_copies = []

    for case_id, page_id in images:
        # Check if case directory exists
        case_dir = str(Path(cases_dir) / case_id)
        if not Path(case_dir).is_dir():
            failed_copies.append((case_id, page_id, "Case directory not found"))
            continue

        # Build the image file path
        image_file = f"{page_id}.jpeg"
        template = getattr(args, "image_path_template", None) if args else None
        source_path = build_file_path(
            cases_dir, case_id, ["images", image_file], 
            template, page_id=page_id, image_file=image_file
        )

        if not Path(source_path).exists():
            failed_copies.append(
                (case_id, page_id, f"Image file not found at: {source_path}")
            )
            continue

        # Create a destination path with case_id prefix to avoid name collisions
        dest_file = f"{case_id}_{image_file}"
        dest_path = str(Path(images_dir) / dest_file)

        try:
            # Copy the image file
            shutil.copy2(source_path, dest_path)
            logger.info(f"Copied image: {dest_path}")
            successful_copies.append((case_id, page_id, dest_file))
        except Exception as e:
            failed_copies.append((case_id, page_id, f"Error copying image: {str(e)}"))

    # Report on failed copies
    if failed_copies:
        logger.warning("\nWarning: Could not copy these image files:")
        for case_id, page_id, reason in failed_copies:
            logger.warning(f"  - {case_id}/{page_id}: {reason}")

    logger.info(f"\nSuccessfully copied {len(successful_copies)} image files to {images_dir}")
    return successful_copies


# ============================================================================
# Annotation File Generation
# ============================================================================

def print_debug_info(is_success: bool, case_id: str, page_id: str, csv_path: str, 
                    headers: List[str], id_column: int, column_name: str,
                    rows: List[List[str]], image_row_count: int) -> None:
    """
    Print debug information for image processing.
    
    Args:
        is_success: Whether this is for a success or failure case
        case_id: Case ID
        page_id: Page ID
        csv_path: Path to the CSV file
        headers: CSV header columns
        id_column: Index of the ID column
        column_name: Name of the ID column
        rows: CSV data rows
        image_row_count: Number of rows found for this image
    """
    result_type = "SUCCESS" if is_success else "FAILURE"
    logger.info(f"\n===== DEBUG INFO FOR FIRST {result_type} =====")
    logger.info(f"Case ID: {case_id}, Page ID: {page_id}")
    logger.info(f"CSV File: {csv_path}")
    logger.info(f"CSV Headers: {headers}")

    # Find which column is used
    if "page_id" in headers:
        logger.info(f"Using 'page_id' column at position {headers.index('page_id')}")
    elif "image_id" in headers:
        logger.info(f"Using 'image_id' column at position {headers.index('image_id')}")
    else:
        logger.info("Neither 'page_id' nor 'image_id' found in headers!")

    # Show the first few rows and the values in the id column
    logger.info(f"First row of data: {rows[0] if rows else 'No rows'}")
    logger.info(f"Looking for: '{page_id}'")
    logger.info(f"In column: {id_column} ('{column_name}')")
    
    first_values = [row[id_column] for row in rows[:5] if len(row) > id_column]
    logger.info(f"First 5 values in this column: {first_values}")
    
    if is_success:
        logger.info(f"RESULT: Found {image_row_count} matching rows")
    else:
        logger.info(f"RESULT: No data rows found for '{page_id}' in '{column_name}' column")
        
    logger.info("===== END DEBUG INFO =====\n")


def create_annotation_file(annotation_file: str, headers_with_labels: List[str], 
                          image_rows: List[List[str]], bbox_idx: int) -> bool:
    """
    Create an annotation file in Excel format with the provided data and bbox coordinate columns.
    
    Args:
        annotation_file: Path to the output annotation file (will be converted to .xlsx)
        headers_with_labels: Headers including any additional columns
        image_rows: Data rows for this image
        bbox_idx: Index of the bboxes column, or -1 if not present
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert file path to .xlsx if it's not already
        excel_file = str(Path(annotation_file).with_suffix(".xlsx"))
        
        # Create the Excel workbook and worksheet
        workbook = xlsxwriter.Workbook(excel_file)
        worksheet = workbook.add_worksheet("Annotation")
        
        # Create formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        coord_format = workbook.add_format({
            'num_format': '0',  # Number format
            'align': 'center'
        })
        
        # Write the headers
        for col_idx, header in enumerate(headers_with_labels):
            worksheet.write(0, col_idx, header, header_format)
        
        # Set up auto-filter on the header row to enable sorting
        worksheet.autofilter(0, 0, len(image_rows), len(headers_with_labels) - 1)
        
        # We have 4 coordinate columns after the bbox column if it exists
        # These are added dynamically in the data row processing loop
        
        # Write the data rows
        for row_idx, row in enumerate(image_rows, start=1):
            col_offset = 0
            
            # Process each cell
            for col_idx, value in enumerate(row):
                # Write the original columns
                worksheet.write(row_idx, col_idx + col_offset, value)
                
                # After the bboxes column, add coordinate columns
                if bbox_idx >= 0 and col_idx == bbox_idx:
                    # Extract coordinates from the bboxes column
                    bbox_str = value
                    coords = extract_bbox_coordinates(bbox_str)
                    
                    # Add the four coordinate columns
                    for i, coord in enumerate(coords):
                        # Try to convert to integer for proper sorting
                        try:
                            coord_val = int(coord) if coord else None
                        except ValueError:
                            coord_val = coord
                            
                        worksheet.write(row_idx, col_idx + 1 + i, coord_val, coord_format)
                    
                    # Update offset for remaining columns
                    col_offset = 4
            
            # Add empty annotator label columns at the end
            worksheet.write(row_idx, len(row) + col_offset, "")      # annotator1_label
            worksheet.write(row_idx, len(row) + col_offset + 1, "")  # annotator2_label
        
        # Set column widths for better readability
        for col_idx, header in enumerate(headers_with_labels):
            if header in ['image_id', 'page_id', 'annotator1_label', 'annotator2_label']:
                worksheet.set_column(col_idx, col_idx, 15)
            elif header in ['bboxes']:
                worksheet.set_column(col_idx, col_idx, 18)
            elif header in ['words']:
                worksheet.set_column(col_idx, col_idx, 20)
            elif header in ['x1', 'y1', 'x2', 'y2']:
                worksheet.set_column(col_idx, col_idx, 8)
            else:
                worksheet.set_column(col_idx, col_idx, 10)
        
        # Freeze the header row
        worksheet.freeze_panes(1, 0)
        
        # Add data validation for dropdowns
        add_data_validation(worksheet, headers_with_labels, image_rows)
        
        # Add conditional formatting
        add_conditional_formatting(workbook, worksheet, headers_with_labels, len(image_rows))
        
        workbook.close()
        logger.info(f"Created annotation Excel file: {excel_file}")
        return True
    except Exception as e:
        logger.error(f"Error writing annotation Excel file: {str(e)}")
        return False


def add_data_validation(worksheet, headers_with_labels: List[str], image_rows: List[List[str]]) -> None:
    """Add dropdown data validation for annotator label columns."""
    try:
        # Shorter list to avoid Excel issues
        standard_labels = ['O', 'B-PER', 'I-PER', 'B-ORG', 'I-ORG', 'B-LOC', 'I-LOC']
        
        # Find annotator columns
        ann1_idx = headers_with_labels.index('annotator1_label')
        ann2_idx = headers_with_labels.index('annotator2_label')
        
        # Use proper Excel range format and simpler validation
        max_row = len(image_rows)
        if max_row > 0:
            worksheet.data_validation(1, ann1_idx, max_row, ann1_idx, {
                'validate': 'list',
                'source': standard_labels
            })
            worksheet.data_validation(1, ann2_idx, max_row, ann2_idx, {
                'validate': 'list',
                'source': standard_labels
            })
    except (ValueError, IndexError):
        pass  # Skip if columns not found


def add_conditional_formatting(workbook, worksheet, headers_with_labels: List[str], num_rows: int) -> None:
    """Add conditional formatting to highlight high-confidence predictions."""
    try:
        # Find prob column in the final headers (after bbox columns are inserted)
        prob_idx = None
        for i, header in enumerate(headers_with_labels):
            if header == 'prob':
                prob_idx = i
                break
        
        if prob_idx is None:
            return  # Skip if prob column not found
        
        # Use the actual number of data rows + header
        max_row = num_rows + 1
        
        # Apply rules in order - Excel uses first matching rule
        # Yellow for medium confidence (0.5 <= x <= 0.8)
        yellow_format = workbook.add_format({'bg_color': '#FFEB9C'})
        worksheet.conditional_format(1, prob_idx, max_row, prob_idx, {
            'type': 'cell',
            'criteria': 'between',
            'minimum': 0.5,
            'maximum': 0.8,
            'format': yellow_format
        })
        
        # Green for high confidence (>0.8) - this will override yellow for >0.8 values
        green_format = workbook.add_format({'bg_color': '#C6EFCE'})
        worksheet.conditional_format(1, prob_idx, max_row, prob_idx, {
            'type': 'cell',
            'criteria': '>',
            'value': 0.8,
            'format': green_format
        })
    except Exception:
        pass  # Skip if any error occurs


def generate_annotation_files(
    cases_dir: str, labels_dir: str, images: List[Tuple[str, str]], args=None
) -> List[Tuple[str, str, str, str]]:
    """
    Generate annotation files for the specified images.

    Args:
        cases_dir: Root directory containing case directories
        labels_dir: Directory where annotation files will be saved
        images: List of (case_id, page_id) tuples to process
        args: Command line arguments containing path templates

    Returns:
        List of (case_id, page_id, image_path, label_path) tuples for successfully created files
    """
    # Create labels directory if it doesn't exist
    ensure_directory_exists(labels_dir)

    successful_files = []
    missing_files = []

    # Track if we've shown debug info for the first success and first failure
    first_success_debug_shown = False
    first_failure_debug_shown = False

    # Print information about what we're looking for
    logger.info("\n===== SOURCE FILE INFO =====")
    logger.info(
        f"Reading image list from: {args.images_file if args else 'data/annotation_images.csv'}"
    )
    logger.info("First 5 entries from image list:")
    for i, (c_id, p_id) in enumerate(images[:5]):
        logger.info(f"  {i + 1}. Case ID: {c_id}, Page ID: {p_id}")
    if len(images) > 5:
        logger.info(f"  ... and {len(images) - 5} more entries")
    logger.info("===== END SOURCE FILE INFO =====\n")

    for case_id, page_id in images:
        # Check if case directory exists
        case_dir = str(Path(cases_dir) / case_id)
        if not Path(case_dir).is_dir():
            missing_files.append((case_id, page_id, "Case directory not found"))
            continue

        # Build the df_check.csv path
        template = getattr(args, "csv_path_template", None) if args else None
        csv_path = build_file_path(
            cases_dir, case_id, ["processing", "form-recogniser", "df_check.csv"], 
            template, page_id=page_id
        )

        if not Path(csv_path).exists():
            missing_files.append(
                (case_id, page_id, f"CSV file not found at: {csv_path}")
            )
            continue

        # Build the image file path
        image_file = f"{page_id}.jpeg"
        img_template = getattr(args, "image_path_template", None) if args else None
        image_path = build_file_path(
            cases_dir, case_id, ["images", image_file], 
            img_template, page_id=page_id, image_file=image_file
        )

        if not Path(image_path).exists():
            missing_files.append(
                (case_id, page_id, f"Image file not found at: {image_path}")
            )
            continue

        # Load the CSV data
        try:
            with Path(csv_path).open("r", newline="") as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader)  # Get the header row
                rows = list(reader)  # Get all data rows
        except Exception as e:
            missing_files.append((case_id, page_id, f"Error reading CSV: {str(e)}"))
            continue

        # Extract bbox columns if present
        bbox_columns = []
        try:
            bbox_idx = headers.index('bboxes')
            # Add columns for individual bbox coordinates after the bboxes column
            bbox_columns = ['x1', 'y1', 'x2', 'y2']
        except ValueError:
            # No bboxes column, so no bbox coordinates to add
            bbox_idx = -1
            
        # Add the annotator label columns and any bbox columns to headers
        headers_with_label = (
            headers[:bbox_idx+1] + bbox_columns + headers[bbox_idx+1:] + ["annotator1_label", "annotator2_label"]
        )

        # Find the page_id column
        page_id_column, column_name = get_filter_column(headers)

        # Filter rows for this image using exact matching
        image_rows = [row for row in rows if row[page_id_column] == page_id]

        # Show debug info for the first successful case
        if image_rows and not first_success_debug_shown:
            first_success_debug_shown = True
            print_debug_info(
                True, case_id, page_id, csv_path, headers, 
                page_id_column, column_name, rows, len(image_rows)
            )

        if not image_rows and not first_failure_debug_shown:
            # Only print debug info for the first failure
            first_failure_debug_shown = True
            print_debug_info(
                False, case_id, page_id, csv_path, headers, 
                page_id_column, column_name, rows, 0
            )

            # Print result for the first failure but don't exit
            logger.warning(
                f"RESULT: No data rows found for '{page_id}' in '{column_name}' column"
            )
            logger.info("Continuing processing remaining files...")
        elif not image_rows:
            # Just add to missing files without debug output for subsequent failures
            missing_files.append(
                (
                    case_id,
                    page_id,
                    f"No data rows found for '{page_id}' in '{column_name}' column",
                )
            )
            continue

        # Create the annotation file (now using .xlsx extension)
        label_file = f"{case_id}_{page_id}.xlsx"
        annotation_file = str(Path(labels_dir) / label_file)

        if create_annotation_file(annotation_file, headers_with_label, image_rows, bbox_idx):
            successful_files.append((case_id, page_id, image_file, label_file))
        else:
            missing_files.append(
                (case_id, page_id, f"Error writing annotation file: {annotation_file}")
            )

    # Report on missing files
    if missing_files:
        logger.warning("\nWarning: Could not create annotation files for these images:")
        for case_id, page_id, reason in missing_files:
            logger.warning(f"  - {case_id}/{page_id}: {reason}")

    logger.info(f"\nSuccessfully created {len(successful_files)} annotation files")
    return successful_files


# ============================================================================
# Excel File Generation
# ============================================================================

def create_excel_workbook(file_path: str, data: List[Dict], 
                        fields: List[str], sheet_name: str = "Annotation Master",
                        include_case_id: bool = True) -> bool:
    """
    Create an Excel workbook with the provided data.
    
    Args:
        file_path: Path to the Excel file to create
        data: List of dictionaries containing row data
        fields: List of field names to include as columns
        sheet_name: Name of the worksheet
        include_case_id: Whether to include the case_id column
        
    Returns:
        True if successful, False otherwise
    """
    try:
        workbook = xlsxwriter.Workbook(file_path)
        worksheet = workbook.add_worksheet(sheet_name)

        # Create formats
        header_format = workbook.add_format({"bold": True})
        link_format = workbook.add_format({"font_color": "blue", "underline": 1})

        # Write header row - for case-specific files, we may skip the case_id column
        header_cols = fields if include_case_id else [f for f in fields if f != "case_id"]
        for col, field in enumerate(header_cols):
            worksheet.write(0, col, field, header_format)

        # Write data rows
        for row_idx, row_data in enumerate(data, start=1):
            col_offset = 0
            
            # Skip case_id column for case-specific files if requested
            if include_case_id:
                worksheet.write(row_idx, 0, row_data["case_id"])
            else:
                col_offset = -1  # Shift all columns one to the left
            
            # Write page_id
            worksheet.write(row_idx, 1 + col_offset, row_data["page_id"])

            # Write hyperlinks
            worksheet.write_formula(
                row_idx,
                2 + col_offset,
                f'HYPERLINK("{row_data["image_path"]}","View image")',
                link_format,
            )
            worksheet.write_formula(
                row_idx,
                3 + col_offset,
                f'HYPERLINK("{row_data["label_path"]}","View labels")',
                link_format,
            )

            # Write remaining cells
            worksheet.write(row_idx, 4 + col_offset, row_data["assignee1"])
            worksheet.write(row_idx, 5 + col_offset, row_data["has_assignee1_completed"])
            worksheet.write(row_idx, 6 + col_offset, row_data["assignee2"])
            worksheet.write(row_idx, 7 + col_offset, row_data["has_assignee2_completed"])
            worksheet.write(row_idx, 8 + col_offset, row_data["notes"])

        # Set column widths for better readability
        if include_case_id:
            worksheet.set_column(0, 0, 15)  # case_id
            worksheet.set_column(1, 1, 15)  # page_id
            worksheet.set_column(2, 3, 20)  # hyperlinks
            worksheet.set_column(4, 7, 15)  # assignees and status
            worksheet.set_column(8, 8, 25)  # notes
        else:
            worksheet.set_column(0, 0, 15)  # page_id
            worksheet.set_column(1, 2, 20)  # hyperlinks
            worksheet.set_column(3, 6, 15)  # assignees and status
            worksheet.set_column(7, 7, 25)  # notes

        workbook.close()
        return True
    except Exception as e:
        logger.error(f"Error: Failed to create Excel file {file_path}: {str(e)}")
        return False


def create_annotator_excel_files(
    case_id: str, data: List[Dict], annotators: List[str], cases_dir: Path
) -> int:
    """
    Create Excel files for each annotator for a specific case.
    
    Args:
        case_id: Case ID
        data: List of dictionaries containing row data for this case
        annotators: List of annotator names
        cases_dir: Directory to save the files
        
    Returns:
        Number of files created successfully
    """
    files_created = 0
    
    for annotator_idx, annotator in enumerate(annotators):
        # Filter data for this annotator
        annotator_data = []
        for row in data:
            # Create a copy of the row with only relevant annotator info
            annotator_row = row.copy()
            
            # Keep only the current annotator's columns
            if annotator_idx == 0:  # First annotator
                annotator_row["assignee"] = annotator_row["assignee1"]
                annotator_row["has_completed"] = annotator_row["has_assignee1_completed"]
            else:  # Second annotator
                annotator_row["assignee"] = annotator_row["assignee2"]
                annotator_row["has_completed"] = annotator_row["has_assignee2_completed"]
            
            # Remove the other annotator's columns
            for key in ["assignee1", "has_assignee1_completed", "assignee2", "has_assignee2_completed"]:
                if key in annotator_row:
                    del annotator_row[key]
            
            annotator_data.append(annotator_row)
        
        # Create a file for this case and annotator
        case_file = str(cases_dir / annotator / f"{case_id}.xlsx")
        
        # Define the fieldnames specifically for annotator-specific files
        annotator_fieldnames = [
            "page_id",
            "image_file_path",
            "label_file_path",
            "assignee",
            "has_completed",
            "notes"
        ]
        
        try:
            workbook = xlsxwriter.Workbook(case_file)
            worksheet = workbook.add_worksheet(f"Case {case_id}")
            
            # Create formats
            header_format = workbook.add_format({"bold": True})
            link_format = workbook.add_format({"font_color": "blue", "underline": 1})
            
            # Write header row
            for col, field in enumerate(annotator_fieldnames):
                worksheet.write(0, col, field, header_format)
            
            # Write data rows
            for row_idx, row_data in enumerate(annotator_data, start=1):
                # Write page_id
                worksheet.write(row_idx, 0, row_data["page_id"])
                
                # Write hyperlinks
                worksheet.write_formula(
                    row_idx,
                    1,
                    f'HYPERLINK("{row_data["image_path"]}","View image")',
                    link_format,
                )
                worksheet.write_formula(
                    row_idx,
                    2,
                    f'HYPERLINK("{row_data["label_path"]}","View labels")',
                    link_format,
                )
                
                # Write remaining cells
                worksheet.write(row_idx, 3, row_data["assignee"])
                worksheet.write(row_idx, 4, row_data["has_completed"])
                worksheet.write(row_idx, 5, row_data["notes"])
            
            # Set column widths for better readability
            worksheet.set_column(0, 0, 15)  # page_id
            worksheet.set_column(1, 2, 20)  # hyperlinks
            worksheet.set_column(3, 3, 15)  # assignee
            worksheet.set_column(4, 4, 15)  # has_completed
            worksheet.set_column(5, 5, 25)  # notes
            
            workbook.close()
            files_created += 1
        except Exception as e:
            logger.error(f"Error: Failed to create case file {case_file}: {str(e)}")
    
    return files_created


def create_case_index_file(case_data: Dict[str, List[Dict]], cases_dir: Path, 
                         annotators: List[str]) -> bool:
    """
    Create an index file for all cases with links to annotator-specific files.
    
    Args:
        case_data: Dictionary of case_id to list of row data dictionaries
        cases_dir: Directory containing the case files
        annotators: List of annotator names
        
    Returns:
        True if successful, False otherwise
    """
    index_file = str(cases_dir / "index.xlsx")
    try:
        workbook = xlsxwriter.Workbook(index_file)
        worksheet = workbook.add_worksheet("Case Index")
        
        # Create formats
        header_format = workbook.add_format({"bold": True})
        link_format = workbook.add_format({"font_color": "blue", "underline": 1})
        
        # Write header
        worksheet.write(0, 0, "case_id", header_format)
        worksheet.write(0, 1, "num_images", header_format)
        
        # Add columns for each annotator
        for idx, annotator in enumerate(annotators):
            worksheet.write(0, 2 + idx, f"{annotator}", header_format)
        
        # Write data rows
        for row_idx, (case_id, data) in enumerate(sorted(case_data.items()), start=1):
            worksheet.write(row_idx, 0, case_id)
            worksheet.write(row_idx, 1, len(data))
            
            # Create hyperlinks to annotator-specific case files
            for idx, annotator in enumerate(annotators):
                case_file_path = f"{annotator}/{case_id}.xlsx"
                worksheet.write_formula(
                    row_idx, 
                    2 + idx, 
                    f'HYPERLINK("{case_file_path}","{annotator} file")',
                    link_format
                )
        
        # Set column widths
        worksheet.set_column(0, 0, 15)  # case_id
        worksheet.set_column(1, 1, 10)  # num_images
        worksheet.set_column(2, 2 + len(annotators) - 1, 15)  # annotator columns
        
        workbook.close()
        logger.info(f"Created case index file: {index_file}")
        return True
    except Exception as e:
        logger.error(f"Error: Failed to create case index file: {str(e)}")
        return False


def create_master_file(
    successful_files: List[Tuple[str, str, str, str]],
    master_file: str,
    network_share: str,
    annotators: List[str] = None,
    split_by_case: bool = True,
) -> None:
    """
    Create master tracking files for the annotation process as Excel XLSX files.
    Generates both a combined master file and individual files per case_id.

    Args:
        successful_files: List of (case_id, page_id, image_file, label_file) tuples
        master_file: Path where the master file will be saved (will be modified to .xlsx)
        network_share: Network share path where files will be copied (e.g., Z:)
        annotators: List of annotator names (default: ["annotator1", "annotator2"])
        split_by_case: Whether to create separate files for each case_id
    """
    if annotators is None or len(annotators) < 2:
        annotators = ["annotator1", "annotator2"]

    # Create the output directory if it doesn't exist
    master_dir = Path(master_file).parent.resolve()
    master_dir.mkdir(parents=True, exist_ok=True)
    
    cases_dir = master_dir / "cases"
    if split_by_case:
        cases_dir.mkdir(exist_ok=True)

    # Convert master_file path to .xlsx extension
    excel_file = str(Path(master_file).with_suffix(".xlsx"))

    # Prepare the data and organize by case_id
    hyperlink_data = []  # Store data for XLSX generation
    case_data = {}  # Data organized by case_id for per-case files
    
    for case_id, page_id, _image_file, _label_file in successful_files:
        # Create properly formatted hyperlinks for Excel
        image_path = f"{network_share}\\annotation_images\\{case_id}_{page_id}.jpeg"
        label_path = f"{network_share}\\annotation_labels\\{case_id}_{page_id}.xlsx"

        # Create the row data
        row_data = {
            "case_id": case_id,
            "page_id": page_id,
            "image_path": image_path,
            "label_path": label_path,
            "assignee1": annotators[0],
            "has_assignee1_completed": "no",
            "assignee2": annotators[1],
            "has_assignee2_completed": "no",
            "notes": "",
        }
        
        # Add to the main data list
        hyperlink_data.append(row_data)
        
        # Organize by case_id for per-case files
        if case_id not in case_data:
            case_data[case_id] = []
        case_data[case_id].append(row_data)

    # Define the fieldnames for the Excel file
    fieldnames = [
        "case_id",
        "page_id",
        "image_file_path",
        "label_file_path",
        "assignee1",
        "has_assignee1_completed",
        "assignee2",
        "has_assignee2_completed",
        "notes",
    ]

    # Create the main master file with all cases
    if create_excel_workbook(excel_file, hyperlink_data, fieldnames):
        logger.info(f"Created master Excel file: {excel_file}")
    
    # Create individual files for each case_id and annotator if requested
    if split_by_case:
        case_files_created = 0
        
        # Create a directory structure for each annotator
        for annotator in annotators:
            annotator_dir = cases_dir / annotator
            annotator_dir.mkdir(exist_ok=True)
        
        # For each case, create separate files for each annotator
        for case_id, data in case_data.items():
            case_files_created += create_annotator_excel_files(
                case_id, data, annotators, cases_dir
            )
        
        logger.info(f"Created {case_files_created} annotator-specific case files in {cases_dir}/")
        
        # Create an index file listing all cases with links to annotator-specific files
        create_case_index_file(case_data, cases_dir, annotators)


# ============================================================================
# Main Function and CLI
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Prepare annotation files and tracking data"
    )
    parser.add_argument(
        "--cases-dir",
        default="du_cases",
        help="Directory containing the case structure (default: /efs/shared/prod/doc-und/cases)",
    )
    parser.add_argument(
        "--labels-dir",
        default="annotation_labels",
        help="Directory where annotation files will be saved (default: annotation_labels). "
             "If --output-dir is provided, this will be relative to that directory.",
    )
    parser.add_argument(
        "--images-dir",
        default="annotation_images",
        help="Directory where image files will be copied (default: annotation_images). "
             "If --output-dir is provided, this will be relative to that directory.",
    )
    parser.add_argument(
        "--images-file",
        default="data/annotation_images.csv",
        help="CSV file listing images to annotate (default: data/annotation_images.csv)",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for all generated files (annotation labels, master file, cases). "
             "If provided, overrides default locations for --master-file, --labels-dir, etc.",
    )
    parser.add_argument(
        "--master-file",
        default="data/master.xlsx",
        help="Path for the master tracking Excel file (default: data/master.xlsx). "
             "If --output-dir is provided, this will be relative to that directory.",
    )
    parser.add_argument(
        "--network-share",
        default="data",
        help="Network share path for hyperlinks (default: Z:Document Understanding\\information_extraction\\gold\\doc filter\\2025 gold eval set)",
    )
    parser.add_argument(
        "--csv-path-template",
        help="Template for CSV file paths. Available variables: {case_dir}, {case_id}, {page_id}. "
        "Example: {case_dir}/some/path/{case_id}/{page_id}.csv",
    )
    parser.add_argument(
        "--image-path-template",
        help="Template for image file paths. Available variables: {case_dir}, {case_id}, {page_id}, {image_file}. "
        "Example: {case_dir}/images/{page_id}.jpeg",
    )
    parser.add_argument(
        "--no-copy-images",
        action="store_true",
        help="Skip copying image files to the annotation_images directory",
    )
    parser.add_argument(
        "--annotators",
        nargs="+",
        default=["annotator1", "annotator2"],
        help="List of annotator names (default: annotator1 annotator2)",
    )
    parser.add_argument(
        "--split-by-case",
        action="store_true",
        help="Split the master file into separate Excel files for each case_id",
    )
    parser.add_argument(
        "--no-split-by-case",
        action="store_true",
        help="Do not split the master file by case_id",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output to warnings and errors only",
    )
    return parser.parse_args()


def main() -> None:
    """
    Main entry point for the script.
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Set logging level based on verbosity flags
    if args.verbose and args.quiet:
        logger.warning("Both --verbose and --quiet specified; using --verbose")
        logger.setLevel(logging.DEBUG)
    elif args.verbose:
        logger.setLevel(logging.DEBUG)
    elif args.quiet:
        logger.setLevel(logging.WARNING)
    
    # Process output directory if provided
    if args.output_dir:
        # Create the output directory if it doesn't exist
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Using output directory: {output_dir}")
        
        # Update paths to be relative to output directory
        if not Path(args.labels_dir).is_absolute():
            args.labels_dir = str(output_dir / args.labels_dir)
            logger.debug(f"Updated labels directory: {args.labels_dir}")
            
        if not Path(args.images_dir).is_absolute():
            args.images_dir = str(output_dir / args.images_dir)
            logger.debug(f"Updated images directory: {args.images_dir}")
            
        if not Path(args.master_file).is_absolute():
            # For master file, get just the filename if it's a path
            master_filename = Path(args.master_file).name
            args.master_file = str(output_dir / master_filename)
            logger.debug(f"Updated master file path: {args.master_file}")
    
    # Make sure the cases directory exists
    validate_directory_exists(
        args.cases_dir, f"Error: Cases directory not found: {args.cases_dir}"
    )

    logger.info(f"Using network share: {args.network_share}")
    logger.info(f"- Images will be linked to: {args.network_share}\\annotation_images\\")
    logger.info(f"- Labels will be linked to: {args.network_share}\\annotation_labels\\")

    # Step 1: Load the list of images to annotate
    images = load_images_to_annotate(args.images_file)

    # Step 2: Copy image files (unless explicitly skipped)
    copied_images = []
    if not args.no_copy_images:
        copied_images = copy_image_files(args.cases_dir, args.images_dir, images, args)

    # Step 3: Generate annotation files
    successful_files = generate_annotation_files(
        args.cases_dir, args.labels_dir, images, args
    )

    # Step 4: Create master tracking file
    # Determine whether to split by case
    split_by_case = True  # Default to True
    if args.no_split_by_case:
        split_by_case = False
    elif args.split_by_case:
        split_by_case = True
        
    create_master_file(
        successful_files, args.master_file, args.network_share, args.annotators, split_by_case
    )

    logger.info("\nAnnotation preparation complete!")
    if not args.no_copy_images:
        logger.info(f"- Copied {len(copied_images)} image files to {args.images_dir}")
    logger.info(f"- Generated {len(successful_files)} annotation files in {args.labels_dir}")
    logger.info(f"- Created master tracking file: {args.master_file}")
    if split_by_case:
        cases_dir = Path(args.master_file).parent / "cases"
        logger.info(f"- Created case-specific files in: {cases_dir}/")
        logger.info(f"- Created case index file: {cases_dir}/index.xlsx")
    logger.info(f"- Images path in master file: {args.network_share}\\annotation_images\\")
    logger.info(f"- Labels path in master file: {args.network_share}\\annotation_labels\\")

    # Show warning if not all images were processed
    if len(successful_files) < len(images):
        logger.warning(
            f"\nWarning: {len(images) - len(successful_files)} images from {args.images_file} were not found"
        )


if __name__ == "__main__":
    main()