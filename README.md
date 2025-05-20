# LayoutLM Outputs Annotation System

A system for managing files used by human annotators to benchmark the DU-SSD LayoutLM outputs.

## Overview

This system provides tools for preparing document image annotations:

1. **Preparing annotation files** - Extract data for individual images from the DU-SSD Pipeline to simplify the annotation process
2. **Managing annotation workflow** - Organize work across multiple annotators with tracking capabilities
3. **Tracking annotation progress** - Update and report on annotation status

The system works with the existing DU-SSD directory structure where:
- Each case has a unique identifier (e.g., 1-12ABCDEF)
- Each case contains multiple document images
- LayoutLM output results are stored in CSV format with an image_id column
- Annotation data is extracted to individual files for human review

## LayoutLM Annotation Management System Directory Structure

```
/
├── data/                   # Configuration and template files
│   ├── annotation_images.csv  # List of images to annotate
│   ├── master.xlsx         # Master tracking file in Excel format
│   ├── cases/              # Individual case files
│   │   ├── 1-12ABCDEF.xlsx # One Excel file per case
│   │   ├── 1-15XYZWQP.xlsx
│   │   ├── ...
│   │   └── index.xlsx      # Index of all cases with links
│   └── completion_updates.csv # Template for batch updates
├── du_cases/               # Main case directory structure
│   ├── 1-12ABCDEF/         # Example case directory
│   │   ├── images/         # Contains all page images for this case
│   │   │   ├── 9876543210_01_0.jpeg
│   │   │   └── ...
│   │   └── processing/
│   │       └── form-recogniser/ 
│   │           └── df_check.csv  # LayoutLM processing results
├── annotation_images/      # Image files for annotation
├── annotation_labels/      # Generated annotation files
└── reports/                # Generated reports
```

## Source Data Format: df_check.csv

The system relies on `df_check.csv` files located in each case directory at `du_cases/{case_id}/processing/form-recogniser/df_check.csv`. These files are critical for creating annotation files.

### df_check.csv Format

Each df_check.csv file contains LayoutLM processing results with the following columns:

- `image_id` - **IMPORTANT**: This column must contain the exact same values as the `page_id` column in `data/annotation_images.csv`. This is used for matching records.
- `block_ids` - Block identifier 
- `word_ids` - Word identifier
- `words` - Text content
- `bboxes` - Bounding box coordinates
- `labels` - Original label
- `pred` - Prediction value
- `prob` - Probability score

## File Formats

### data/annotation_images.csv
```
case_id,image_id
1-12ABCDEF,9876543210_01_0
1-12ABCDEF,9876543210_02_0
```

### data/completion_updates.csv
```
case_id,image_id,annotator,status
1-12ABCDEF,9876543210_01_0,annotator1,yes
1-15XYZWQP,1122334455_03_1,,yes
```

### data/master.xlsx
An Excel workbook containing the following columns:
- case_id
- image_id
- image_file_path (as clickable hyperlinks)
- label_file_path (as clickable hyperlinks)
- assignee1
- has_assignee1_completed
- assignee2
- has_assignee2_completed
- notes

### data/cases/*.xlsx
Individual Excel files for each case, containing the same columns as the master file except for case_id (which is already in the filename). This makes it easier to distribute specific cases to annotators.

## Workflow

The typical workflow for using this system is:

1. **Specify images to annotate**
   - Edit `data/annotation_images.csv` to list the case_id and page_id of each image to annotate

2. **Generate annotation files and master tracking file**
   - Run `./prepare_annotations.py` to create individual annotation files and the master tracking file
   - The master tracking file (data/master.xlsx) will be automatically generated
   - Individual Excel files for each case will be created in data/cases/

3. **Track annotation progress**
   - Use `./update_master_file.py` to update the completion status of annotations
   - Generate reports with `./generate_report.py` to monitor progress

## Quick Start

To prepare annotation files for a specific list of images:

```bash
# Basic usage (local paths)
./prepare_annotations.py

# Using mapped Z: drive (recommended for our environment)
./prepare_annotations.py --network-share "Z:Document Understanding\information_extraction\gold\doc filter\2025 gold eval set"

# Or simply use the drive letter for the root directory
./prepare_annotations.py --network-share Z:
```

This single script will:
1. Read the list of images from `data/annotation_images.csv`
2. Generate annotation files only for those images in the `annotation_labels/` directory
3. Create a master tracking file in `data/master.xlsx` with clickable hyperlinks
4. Create individual Excel files for each case in `data/cases/` directory
5. Create an index file (`data/cases/index.xlsx`) with links to individual case files
6. Provide a summary of how many images were processed

## Scripts

### prepare_annotations.py

Create annotation files for the specified images and generate a master tracking file:

```bash
# Using mapped Z: drive with complete path (recommended for our environment)
./prepare_annotations.py --network-share "Z:Document Understanding\information_extraction\gold\doc filter\2025 gold eval set"
```

Options:
- `--cases-dir`: Directory containing the DU-SSD LayoutLM outputs (default: du_cases)
- `--labels-dir`: Directory where annotation files will be saved (default: annotation_labels)
- `--images-dir`: Directory where image files will be copied (default: annotation_images)
- `--images-file`: CSV file listing images to annotate (default: data/annotation_images.csv)
- `--master-file`: Path for the master tracking file (default: data/master.xlsx)
- `--network-share`: Network share path where files will be copied
- `--csv-path-template`: Template for CSV file paths with variables {case_dir}, {case_id}, {page_id}
- `--image-path-template`: Template for image file paths with variables {case_dir}, {case_id}, {page_id}, {image_file}
- `--no-copy-images`: Skip copying image files to the annotation_images directory
- `--annotators`: List of annotator names (default: annotator1 annotator2)
- `--split-by-case`: Split the master file into separate Excel files for each case_id (default: enabled)
- `--no-split-by-case`: Do not create separate Excel files for each case_id

### update_master_file.py

Update the completion status of annotations in the master file:

```bash
# Update from a CSV file with status information
./update_master_file.py --master-file data/master.xlsx from-file data/completion_updates.csv

# Update specific entries
./update_master_file.py --master-file data/master.xlsx specific \
                        --case-ids "1-12ABCDEF" "1-15XYZWQP" \
                        --annotators "annotator1" \
                        --status yes
```

### generate_report.py

Generate reports based on the annotation progress:

```bash
# Generate all available reports
./generate_report.py --master-file data/master.xlsx --output-dir reports

# Generate a specific report type
./generate_report.py --master-file data/master.xlsx --output-dir reports --report-type progress
```

Available report types:
- `progress` - Annotation progress by case
- `annotator` - Annotator productivity
- `all` - Generate all report types (default)

## Troubleshooting Common Issues

### df_check.csv Errors

If you encounter errors like "No data rows found for [page_id] in 'image_id' column", check:
1. The `image_id` values in df_check.csv match exactly with the `page_id` values in annotation_images.csv
2. The df_check.csv exists in the expected location
3. The df_check.csv contains the proper column headers
4. The df_check.csv has entries for all required page_id values

### Excel Hyperlink Issues

If hyperlinks in Excel don't work correctly:

1. **Use mapped drives with complete document path**: 
   ```bash
   ./prepare_annotations.py --network-share "Z:Document Understanding\information_extraction\gold\doc filter\2025 gold eval set"
   ```
   Note: In our environment, Z: is mapped to a network share with the specified subdirectories
   
2. **Check for extra quotes**: If your hyperlinks have double quotes like `""Z:\path""`, this may be due to Excel's CSV handling. The scripts have been updated to prevent this issue.

3. **Manual fix in Excel**: If hyperlinks still don't work, you can select the columns with hyperlinks in Excel, right-click and choose "Remove Hyperlink", then select all cells again and use the HYPERLINK function to recreate them.