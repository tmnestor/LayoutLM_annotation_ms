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
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

# Try to import xlsxwriter but don't fail if it's not available
try:
    import xlsxwriter

    HAVE_XLSXWRITER = True
except ImportError:
    HAVE_XLSXWRITER = False


def load_images_to_annotate(images_file: str) -> List[Tuple[str, str]]:
    """
    Load the list of images that need to be annotated.

    Args:
        images_file: Path to CSV file with case_id and page_id columns

    Returns:
        List of (case_id, page_id) tuples
    """
    if not Path(images_file).exists():
        print(f"Error: Images file not found: {images_file}")
        sys.exit(1)

    images = []

    with Path(images_file).open("r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)

        # Verify required columns
        if "case_id" not in reader.fieldnames or "page_id" not in reader.fieldnames:
            print("Error: Images file must contain 'case_id' and 'page_id' columns")
            sys.exit(1)

        for row in reader:
            images.append((row["case_id"], row["page_id"]))

    print(f"Loaded {len(images)} images to annotate from {images_file}")
    return images


def copy_image_files(
    cases_dir: str, images_dir: str, images: List[Tuple[str, str]], args=None
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
    Path(images_dir).mkdir(parents=True, exist_ok=True)

    successful_copies = []
    failed_copies = []

    for case_id, page_id in images:
        # Check if case directory exists
        case_dir = str(Path(cases_dir) / case_id)
        if not Path(case_dir).is_dir():
            failed_copies.append((case_id, page_id, "Case directory not found"))
            continue

        # Build the image file path using the template
        image_file = f"{page_id}.jpeg"
        source_path_template = str(Path(case_dir) / "images" / image_file)
        source_path = source_path_template

        # If a custom image path template is provided
        if args and hasattr(args, "image_path_template") and args.image_path_template:
            # Replace {case_id} and {page_id} if present
            source_path = args.image_path_template.format(
                case_id=case_id,
                page_id=page_id,
                image_file=image_file,
                case_dir=case_dir,
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
            print(f"Copied image: {dest_path}")
            successful_copies.append((case_id, page_id, dest_file))
        except Exception as e:
            failed_copies.append((case_id, page_id, f"Error copying image: {str(e)}"))

    # Report on failed copies
    if failed_copies:
        print("\nWarning: Could not copy these image files:")
        for case_id, page_id, reason in failed_copies:
            print(f"  - {case_id}/{page_id}: {reason}")

    print(f"\nSuccessfully copied {len(successful_copies)} image files to {images_dir}")
    return successful_copies


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
    Path(labels_dir).mkdir(parents=True, exist_ok=True)

    successful_files = []
    missing_files = []

    # Track if we've shown debug info for the first success and first failure
    first_success_debug_shown = False
    first_failure_debug_shown = False

    # Print information about what we're looking for
    print("\n===== SOURCE FILE INFO =====")
    print(
        f"Reading image list from: {args.images_file if args else 'data/annotation_images.csv'}"
    )
    print("First 5 entries from image list:")
    for i, (c_id, p_id) in enumerate(images[:5]):
        print(f"  {i + 1}. Case ID: {c_id}, Page ID: {p_id}")
    if len(images) > 5:
        print(f"  ... and {len(images) - 5} more entries")
    print("===== END SOURCE FILE INFO =====\n")

    for case_id, page_id in images:
        # Check if case directory exists
        case_dir = str(Path(cases_dir) / case_id)
        if not Path(case_dir).is_dir():
            missing_files.append((case_id, page_id, "Case directory not found"))
            continue

        # Build the df_check.csv path using the template
        csv_path_template = str(
            Path(case_dir) / "processing" / "form-recogniser" / "df_check.csv"
        )
        csv_path = csv_path_template

        # If a custom CSV path template is provided
        if hasattr(args, "csv_path_template") and args.csv_path_template:
            # Replace {case_id} and {page_id} if present
            csv_path = args.csv_path_template.format(
                case_id=case_id, page_id=page_id, case_dir=case_dir
            )

        if not Path(csv_path).exists():
            missing_files.append(
                (case_id, page_id, f"CSV file not found at: {csv_path}")
            )
            continue

        # Build the image file path using the template
        image_file = f"{page_id}.jpeg"
        image_path_template = str(Path(case_dir) / "images" / image_file)
        image_path = image_path_template

        # If a custom image path template is provided
        if hasattr(args, "image_path_template") and args.image_path_template:
            # Replace {case_id} and {page_id} if present
            image_path = args.image_path_template.format(
                case_id=case_id,
                page_id=page_id,
                image_file=image_file,
                case_dir=case_dir,
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

        # Add the annotator label column to headers
        headers_with_label = headers + ["annotator_label"]

        # Find the page_id column
        page_id_column = 0  # Default to first column

        if "page_id" in headers:
            page_id_column = headers.index("page_id")
        elif "image_id" in headers:
            # For backward compatibility with older files that use image_id
            page_id_column = headers.index("image_id")

        # Filter rows for this image using exact matching
        image_rows = [row for row in rows if row[page_id_column] == page_id]

        # Show debug info for the first successful case
        if image_rows and not first_success_debug_shown:
            first_success_debug_shown = True
            print("\n===== DEBUG INFO FOR FIRST SUCCESS =====")
            print(f"Case ID: {case_id}, Page ID: {page_id}")
            print(f"CSV File: {csv_path}")
            print(f"CSV Headers: {headers}")

            # Find which column is used
            if "page_id" in headers:
                print(f"Using 'page_id' column at position {headers.index('page_id')}")
            elif "image_id" in headers:
                print(
                    f"Using 'image_id' column at position {headers.index('image_id')}"
                )
            else:
                print("Neither 'page_id' nor 'image_id' found in headers!")

            # Show the first few rows and the values in the id column
            print(f"First row of data: {rows[0] if rows else 'No rows'}")
            print(f"Looking for: '{page_id}'")
            print(f"In column: {page_id_column} ('{headers[page_id_column]}')")
            print(
                f"First 5 values in this column: {[row[page_id_column] for row in rows[:5] if len(row) > page_id_column]}"
            )
            print(f"RESULT: Found {len(image_rows)} matching rows")
            print("===== END DEBUG INFO =====\n")

        if not image_rows and not first_failure_debug_shown:
            # Only print debug info for the first failure
            first_failure_debug_shown = True
            print("\n===== DEBUG INFO FOR FIRST FAILURE =====")
            print(f"Case ID: {case_id}, Page ID: {page_id}")
            print(f"CSV File: {csv_path}")
            print(f"CSV Headers: {headers}")

            # Find which column is used
            if "page_id" in headers:
                print(f"Using 'page_id' column at position {headers.index('page_id')}")
            elif "image_id" in headers:
                print(
                    f"Using 'image_id' column at position {headers.index('image_id')}"
                )
            else:
                print("Neither 'page_id' nor 'image_id' found in headers!")

            # Show the first few rows and the values in the id column
            print(f"First row of data: {rows[0] if rows else 'No rows'}")
            print(f"Looking for: '{page_id}'")
            print(f"In column: {page_id_column} ('{headers[page_id_column]}')")
            print(
                f"First 5 values in this column: {[row[page_id_column] for row in rows[:5] if len(row) > page_id_column]}"
            )
            print("===== END DEBUG INFO =====\n")

            # Print result for the first failure but don't exit
            print(
                f"RESULT: No data rows found for '{page_id}' in '{headers[page_id_column]}' column"
            )
            print("Continuing processing remaining files...")
        elif not image_rows:
            # Just add to missing files without debug output for subsequent failures
            missing_files.append(
                (
                    case_id,
                    page_id,
                    f"No data rows found for '{page_id}' in '{headers[page_id_column]}' column",
                )
            )
            continue

        # Create the annotation file
        label_file = f"{case_id}_{page_id}.csv"
        annotation_file = str(Path(labels_dir) / label_file)

        try:
            with Path(annotation_file).open("w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers_with_label)

                # Write all rows for this image, with an empty annotation column
                for row in image_rows:
                    writer.writerow(row + [""])  # Add empty string for annotation

            print(f"Created annotation file: {annotation_file}")
            successful_files.append((case_id, page_id, image_file, label_file))
        except Exception as e:
            missing_files.append(
                (case_id, page_id, f"Error writing annotation file: {str(e)}")
            )

    # Report on missing files
    if missing_files:
        print("\nWarning: Could not create annotation files for these images:")
        for case_id, page_id, reason in missing_files:
            print(f"  - {case_id}/{page_id}: {reason}")

    print(f"\nSuccessfully created {len(successful_files)} annotation files")
    return successful_files


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
        label_path = f"{network_share}\\annotation_labels\\{case_id}_{page_id}.csv"

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

    # Check for xlsxwriter availability
    if not HAVE_XLSXWRITER:
        print(
            "Error: XlsxWriter package not available. Install it with 'pip install xlsxwriter' to create Excel files."
        )
        sys.exit(1)
    
    # Helper function to write an Excel file with the given data
    def write_excel_file(file_path, data, sheet_name="Annotation Master", include_case_id=True):
        try:
            workbook = xlsxwriter.Workbook(file_path)
            worksheet = workbook.add_worksheet(sheet_name)

            # Create formats
            header_format = workbook.add_format({"bold": True})
            link_format = workbook.add_format({"font_color": "blue", "underline": 1})

            # Write header row - for case-specific files, we may skip the case_id column
            header_cols = fieldnames if include_case_id else [f for f in fieldnames if f != "case_id"]
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
            print(f"Error: Failed to create Excel file {file_path}: {str(e)}")
            return False

    # Create the main master file with all cases
    if write_excel_file(excel_file, hyperlink_data):
        print(f"Created master Excel file: {excel_file}")
    
    # Create individual files for each case_id and annotator if requested
    if split_by_case:
        case_files_created = 0
        
        # Create a directory structure for each annotator
        for annotator in annotators:
            annotator_dir = cases_dir / annotator
            annotator_dir.mkdir(exist_ok=True)
        
        # For each case, create separate files for each annotator
        for case_id, data in case_data.items():
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
                    if "assignee1" in annotator_row:
                        del annotator_row["assignee1"]
                    if "has_assignee1_completed" in annotator_row:
                        del annotator_row["has_assignee1_completed"]
                    if "assignee2" in annotator_row:
                        del annotator_row["assignee2"]
                    if "has_assignee2_completed" in annotator_row:
                        del annotator_row["has_assignee2_completed"]
                    
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
                    case_files_created += 1
                except Exception as e:
                    print(f"Error: Failed to create case file {case_file}: {str(e)}")
        
        print(f"Created {case_files_created} annotator-specific case files in {cases_dir}/")
        
        # Create an index file listing all cases with links to annotator-specific files
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
            print(f"Created case index file: {index_file}")
        except Exception as e:
            print(f"Error: Failed to create case index file: {str(e)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare annotation files and tracking data"
    )
    parser.add_argument(
        "--cases-dir",
        default="du_cases",
        help="Directory containing the case structure (default: du_cases)",
    )
    parser.add_argument(
        "--labels-dir",
        default="annotation_labels",
        help="Directory where annotation files will be saved (default: annotation_labels)",
    )
    parser.add_argument(
        "--images-dir",
        default="annotation_images",
        help="Directory where image files will be copied (default: annotation_images)",
    )
    parser.add_argument(
        "--images-file",
        default="data/annotation_images.csv",
        help="CSV file listing images to annotate (default: data/annotation_images.csv)",
    )
    parser.add_argument(
        "--master-file",
        default="data/master.xlsx",
        help="Path for the master tracking Excel file (default: data/master.xlsx)",
    )
    parser.add_argument(
        "--network-share",
        default="Z:Document Understanding\\information_extraction\\gold\\doc filter\\2025 gold eval set",
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
    args = parser.parse_args()

    # Make sure the cases directory exists
    if not Path(args.cases_dir).is_dir():
        print(f"Error: Cases directory not found: {args.cases_dir}")
        sys.exit(1)

    print(f"Using network share: {args.network_share}")
    print(f"- Images will be linked to: {args.network_share}\\annotation_images\\")
    print(f"- Labels will be linked to: {args.network_share}\\annotation_labels\\")

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

    print("\nAnnotation preparation complete!")
    if not args.no_copy_images:
        print(f"- Copied {len(copied_images)} image files to {args.images_dir}")
    print(f"- Generated {len(successful_files)} annotation files in {args.labels_dir}")
    print(f"- Created master tracking file: {args.master_file}")
    if split_by_case:
        cases_dir = Path(args.master_file).parent / "cases"
        print(f"- Created case-specific files in: {cases_dir}/")
        print(f"- Created case index file: {cases_dir}/index.xlsx")
    print(f"- Images path in master file: {args.network_share}\\annotation_images\\")
    print(f"- Labels path in master file: {args.network_share}\\annotation_labels\\")

    # Show warning if not all images were processed
    if len(successful_files) < len(images):
        print(
            f"\nWarning: {len(images) - len(successful_files)} images from {args.images_file} were not found"
        )


if __name__ == "__main__":
    main()
