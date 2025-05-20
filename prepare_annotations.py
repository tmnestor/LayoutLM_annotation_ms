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
import os
import shutil
import sys
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
    if not os.path.exists(images_file):
        print(f"Error: Images file not found: {images_file}")
        sys.exit(1)

    images = []

    with open(images_file, "r", newline="") as csvfile:
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
    os.makedirs(images_dir, exist_ok=True)

    successful_copies = []
    failed_copies = []

    for case_id, page_id in images:
        # Check if case directory exists
        case_dir = os.path.join(cases_dir, case_id)
        if not os.path.isdir(case_dir):
            failed_copies.append((case_id, page_id, "Case directory not found"))
            continue

        # Build the image file path using the template
        image_file = f"{page_id}.jpeg"
        source_path_template = os.path.join(case_dir, "images", image_file)
        source_path = source_path_template

        # If a custom image path template is provided
        if args and hasattr(args, "image_path_template") and args.image_path_template:
            # Replace {case_id} and {page_id} if present
            source_path = args.image_path_template.format(
                case_id=case_id, page_id=page_id, image_file=image_file, case_dir=case_dir
            )

        if not os.path.exists(source_path):
            failed_copies.append((case_id, page_id, f"Image file not found at: {source_path}"))
            continue

        # Create a destination path with case_id prefix to avoid name collisions
        dest_file = f"{case_id}_{image_file}"
        dest_path = os.path.join(images_dir, dest_file)

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
    os.makedirs(labels_dir, exist_ok=True)

    successful_files = []
    missing_files = []

    # Track if we've shown debug info for the first success and first failure
    first_success_debug_shown = False
    first_failure_debug_shown = False

    # Print information about what we're looking for
    print("\n===== SOURCE FILE INFO =====")
    print(f"Reading image list from: {args.images_file if args else 'data/annotation_images.csv'}")
    print("First 5 entries from image list:")
    for i, (c_id, p_id) in enumerate(images[:5]):
        print(f"  {i + 1}. Case ID: {c_id}, Page ID: {p_id}")
    if len(images) > 5:
        print(f"  ... and {len(images) - 5} more entries")
    print("===== END SOURCE FILE INFO =====\n")

    for case_id, page_id in images:
        # Check if case directory exists
        case_dir = os.path.join(cases_dir, case_id)
        if not os.path.isdir(case_dir):
            missing_files.append((case_id, page_id, "Case directory not found"))
            continue

        # Build the df_check.csv path using the template
        csv_path_template = os.path.join(case_dir, "processing", "form-recogniser", "df_check.csv")
        csv_path = csv_path_template

        # If a custom CSV path template is provided
        if hasattr(args, "csv_path_template") and args.csv_path_template:
            # Replace {case_id} and {page_id} if present
            csv_path = args.csv_path_template.format(case_id=case_id, page_id=page_id, case_dir=case_dir)

        if not os.path.exists(csv_path):
            missing_files.append((case_id, page_id, f"CSV file not found at: {csv_path}"))
            continue

        # Build the image file path using the template
        image_file = f"{page_id}.jpeg"
        image_path_template = os.path.join(case_dir, "images", image_file)
        image_path = image_path_template

        # If a custom image path template is provided
        if hasattr(args, "image_path_template") and args.image_path_template:
            # Replace {case_id} and {page_id} if present
            image_path = args.image_path_template.format(
                case_id=case_id, page_id=page_id, image_file=image_file, case_dir=case_dir
            )

        if not os.path.exists(image_path):
            missing_files.append((case_id, page_id, f"Image file not found at: {image_path}"))
            continue

        # Load the CSV data
        try:
            with open(csv_path, "r", newline="") as csvfile:
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
                print(f"Using 'image_id' column at position {headers.index('image_id')}")
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
                print(f"Using 'image_id' column at position {headers.index('image_id')}")
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
            print(f"RESULT: No data rows found for '{page_id}' in '{headers[page_id_column]}' column")
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
        annotation_file = os.path.join(labels_dir, label_file)

        try:
            with open(annotation_file, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers_with_label)

                # Write all rows for this image, with an empty annotation column
                for row in image_rows:
                    writer.writerow(row + [""])  # Add empty string for annotation

            print(f"Created annotation file: {annotation_file}")
            successful_files.append((case_id, page_id, image_file, label_file))
        except Exception as e:
            missing_files.append((case_id, page_id, f"Error writing annotation file: {str(e)}"))

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
) -> None:
    """
    Create a master tracking file for the annotation process.

    Args:
        successful_files: List of (case_id, page_id, image_file, label_file) tuples
        master_file: Path where the master file will be saved
        network_share: Network share path where files will be copied (e.g., \\server\share)
        annotators: List of annotator names (default: ["annotator1", "annotator2"])
    """
    if annotators is None or len(annotators) < 2:
        annotators = ["annotator1", "annotator2"]

    # Create the output directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(master_file)), exist_ok=True)

    # Prepare the CSV data
    csv_data = []
    for case_id, page_id, image_file, label_file in successful_files:
        # Standard network share paths - store just the paths without hyperlink formatting
        image_path = f"{network_share}\\annotation_images\\{case_id}_{page_id}.jpeg"
        label_path = f"{network_share}\\annotation_labels\\{case_id}_{page_id}.csv"

        # Create a row for the master CSV with the paths only - hyperlink formatting will be done at write time
        row = {
            "case_id": case_id,
            "page_id": page_id,
            "image_file_path": image_path,
            "label_file_path": label_path,
            "assignee1": annotators[0],
            "has_assignee1_completed": "no",
            "assignee2": annotators[1],
            "has_assignee2_completed": "no",
            "notes": "",
        }
        csv_data.append(row)

    # Define the fieldnames for the CSV file
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

    # Format the data for CSV output with proper hyperlinks for Excel
    formatted_rows = []
    hyperlink_data = []  # Store data for XLSX generation

    for row in csv_data:
        current_case_id = row["case_id"]
        current_page_id = row["page_id"]

        # Create properly formatted hyperlinks for Excel
        image_path = f"Z:Document Understanding\\information_extraction\\gold\\doc filter\\2025 gold eval set\\annotation_images\\{current_case_id}_{current_page_id}.jpeg"
        label_path = f"Z:Document Understanding\\information_extraction\\gold\\doc filter\\2025 gold eval set\\annotation_labels\\{current_case_id}_{current_page_id}.csv"

        # Store the formatted row for CSV
        formatted_row = {
            "case_id": row["case_id"],
            "page_id": row["page_id"],
            "image_file_path": f'=HYPERLINK("{image_path}","View image")',
            "label_file_path": f'=HYPERLINK("{label_path}","View labels")',
            "assignee1": row["assignee1"],
            "has_assignee1_completed": row["has_assignee1_completed"],
            "assignee2": row["assignee2"],
            "has_assignee2_completed": row["has_assignee2_completed"],
            "notes": row["notes"],
        }
        formatted_rows.append(formatted_row)

        # Store the raw data for XLSX creation
        hyperlink_data.append(
            {
                "case_id": current_case_id,
                "page_id": current_page_id,
                "image_path": image_path,
                "label_path": label_path,
                "assignee1": row["assignee1"],
                "has_assignee1_completed": row["has_assignee1_completed"],
                "assignee2": row["assignee2"],
                "has_assignee2_completed": row["has_assignee2_completed"],
                "notes": row["notes"],
            }
        )

    # Write the CSV file manually to avoid automatic escaping
    with open(master_file, "w", newline="") as f:
        # Write header
        f.write(",".join(fieldnames) + "\n")

        # Write each row manually with exact formatting
        for row in formatted_rows:
            # For non-hyperlink fields
            normal_fields = [
                row["case_id"],
                row["page_id"],
                f'"{row["image_file_path"]}"',  # Quoted hyperlink
                f'"{row["label_file_path"]}"',  # Quoted hyperlink
                row["assignee1"],
                row["has_assignee1_completed"],
                row["assignee2"],
                row["has_assignee2_completed"],
                row["notes"],
            ]
            f.write(",".join(normal_fields) + "\n")

    # Also create an Excel file if xlsxwriter is available
    excel_file = os.path.splitext(master_file)[0] + ".xlsx"
    if HAVE_XLSXWRITER:
        try:
            # Create the Excel file with proper hyperlinks
            workbook = xlsxwriter.Workbook(excel_file)
            worksheet = workbook.add_worksheet("Annotation Master")

            # Create formats
            header_format = workbook.add_format({"bold": True})
            link_format = workbook.add_format({"font_color": "blue", "underline": 1})

            # Write header row
            for col, field in enumerate(fieldnames):
                worksheet.write(0, col, field, header_format)

            # Write data rows
            for row_idx, row_data in enumerate(hyperlink_data, start=1):
                # Write regular cells
                worksheet.write(row_idx, 0, row_data["case_id"])
                worksheet.write(row_idx, 1, row_data["page_id"])

                # Write hyperlinks
                worksheet.write_formula(
                    row_idx, 2, f'HYPERLINK("{row_data["image_path"]}","View image")', link_format
                )
                worksheet.write_formula(
                    row_idx, 3, f'HYPERLINK("{row_data["label_path"]}","View labels")', link_format
                )

                # Write remaining cells
                worksheet.write(row_idx, 4, row_data["assignee1"])
                worksheet.write(row_idx, 5, row_data["has_assignee1_completed"])
                worksheet.write(row_idx, 6, row_data["assignee2"])
                worksheet.write(row_idx, 7, row_data["has_assignee2_completed"])
                worksheet.write(row_idx, 8, row_data["notes"])

            workbook.close()
            print(f"Created master XLSX file: {excel_file}")
        except Exception as e:
            print(f"Warning: Failed to create Excel file: {str(e)}")
    else:
        print(
            "Note: XlsxWriter package not available. Install it with 'pip install xlsxwriter' to create Excel files."
        )

    print(f"Created master CSV file: {master_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare annotation files and tracking data")
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
        default="data/master.csv",
        help="Path for the master tracking file (default: data/master.csv)",
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
    args = parser.parse_args()

    # Make sure the cases directory exists
    if not os.path.isdir(args.cases_dir):
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
    successful_files = generate_annotation_files(args.cases_dir, args.labels_dir, images, args)

    # Step 4: Create master tracking file
    create_master_file(successful_files, args.master_file, args.network_share, args.annotators)

    print("\nAnnotation preparation complete!")
    if not args.no_copy_images:
        print(f"- Copied {len(copied_images)} image files to {args.images_dir}")
    print(f"- Generated {len(successful_files)} annotation files in {args.labels_dir}")
    print(f"- Created master tracking file: {args.master_file}")
    if HAVE_XLSXWRITER:
        excel_file = os.path.splitext(args.master_file)[0] + ".xlsx"
        print(f"  Also created Excel file: {excel_file}")
    print(f"- Images path in master file: {args.network_share}\\annotation_images\\")
    print(f"- Labels path in master file: {args.network_share}\\annotation_labels\\")

    # Show warning if not all images were processed
    if len(successful_files) < len(images):
        print(
            f"\nWarning: {len(images) - len(successful_files)} images from {args.images_file} were not found"
        )


if __name__ == "__main__":
    main()
