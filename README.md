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
│   ├── cases/              # Annotator-specific case files
│   │   ├── annotator1/     # First annotator's files
│   │   │   ├── 1-12ABCDEF.xlsx 
│   │   │   ├── 1-15XYZWQP.xlsx
│   │   │   └── ...
│   │   ├── annotator2/     # Second annotator's files
│   │   │   ├── 1-12ABCDEF.xlsx
│   │   │   ├── 1-15XYZWQP.xlsx
│   │   │   └── ...
│   │   └── index.xlsx      # Index of all cases with links to annotator files
│   └── completion_updates.csv # Template for batch updates
├── /efs/shared/prod/doc-und/cases/  # Main case directory (absolute path)
│   ├── 1-12ABCDEF/         # Example case directory
│   │   ├── images/         # Contains all page images for this case
│   │   │   ├── 9876543210_01_0.jpeg
│   │   │   └── ...
│   │   ├── extracted_text_json/  # JSON extraction results (directly under case)
│   │   │   ├── 9876543210_01_0.json  # JSON data for specific page
│   │   │   ├── 9876543210_02_0.json
│   │   │   └── ...
│   │   └── processing/
│   │       └── form-recogniser/ 
│   │           └── df_check.csv  # LayoutLM processing results
├── annotation_images/      # Image files for annotation
├── annotation_labels/      # Generated annotation files
└── reports/                # Generated reports
```

## Source Data Format: df_check.csv

The system relies on `df_check.csv` files located in each case directory at `/efs/shared/prod/doc-und/cases/{case_id}/processing/form-recogniser/df_check.csv`. These files are critical for creating annotation files.

### df_check.csv Format

Each df_check.csv file contains LayoutLM processing results with the following columns:

- `image_id` - **IMPORTANT**: This column must contain the exact same values as the `page_id` column in `data/annotation_images.csv`. This is used for matching records.
- `block_ids` - Block identifier 
- `word_ids` - Word identifier
- `words` - Text content
- `bboxes` - Bounding box coordinates in format "(ul_x, ul_y, lr_x, lr_y)" where ul = upper-left, lr = lower-right
- `labels` - Original label
- `pred` - Prediction value
- `prob` - Probability score

## How Annotation Files are Constructed

The CSV files in the `annotation_labels` directory are created through the following process:

1. The `prepare_annotations.py` script reads a list of images to annotate from `data/annotation_images.csv`
   - This CSV contains case_id and page_id columns (e.g., 1-12ABCDEF and 9876543210_01_0)

2. For each case and page combination in the list:
   - The script locates the source data in `/efs/shared/prod/doc-und/cases/<case_id>/processing/form-recogniser/df_check.csv`
   - These source files contain data for multiple images within a case

3. The script then:
   - Filters rows from the source file for just the specific image_id (page_id)
   - Creates a new Excel file in the annotation_labels directory named `<case_id>_<page_id>.xlsx`
   - Extracts x1, y1, x2, y2 coordinates from the bboxes column and adds separate columns
   - Adds an additional empty column called "annotator_label" for human annotations
   - Formats the Excel file with auto-filtering and proper column types for sorting

4. The resulting Excel files in annotation_labels contain only the rows relevant to a specific image, making it easier for annotators to focus on just the data they need to annotate and sort/filter content as needed.

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

### data/cases/annotator*/*.xlsx
Annotator-specific Excel files for each case, containing only the columns relevant to a single annotator:
- page_id
- image_file_path (as clickable hyperlinks)
- label_file_path (as clickable hyperlinks)
- assignee (the annotator's name)
- has_completed (completion status for this annotator)
- notes

Each annotator has their own directory containing case files, preventing annotators from overwriting each other's work. This organization makes it easier to distribute specific cases to specific annotators.

### annotation_labels/*.xlsx
Generated Excel files containing:
- All columns from the source df_check.csv (image_id, block_ids, word_ids, words, bboxes, labels, pred, prob)
- Four additional coordinate columns (x1, y1, x2, y2) extracted from the bboxes column
- An empty "annotator_label" column for human annotations

Features:
- Excel format allows sorting by any column, including the coordinate columns
- Auto-filtering enabled to easily filter rows
- Numeric coordinate columns for proper sorting by position
- Column widths adjusted for readability
- Frozen header row for easier navigation

Example row:
```
image_id,block_ids,word_ids,words,bboxes,x1,y1,x2,y2,labels,pred,prob,annotator_label
9876543210_01_0,1,10,form,"(10, 20, 100, 40)",10,20,100,40,FIELD,0,0.95,
```

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

# Using an external output directory (for KFP prod environments)
./prepare_annotations.py --output-dir /efs/shared/dev-de/ude5g

# Quiet mode (minimal output)
./prepare_annotations.py --quiet
```

This single script will:
1. Read the list of images from `data/annotation_images.csv`
2. Generate annotation files with extracted bounding box coordinates
3. Create a master tracking file with clickable hyperlinks
4. Create separate annotator directories for each annotator
5. Generate annotator-specific Excel files for each case
6. Create an index file with links to all annotator-specific case files
7. Provide a summary of how many images were processed

## Scripts

### prepare_annotations.py

Create annotation files for the specified images and generate a master tracking file:

```bash
# Using mapped Z: drive with complete path
./prepare_annotations.py --network-share "Z:Document Understanding\information_extraction\gold\doc filter\2025 gold eval set"
```

Options:
- `--cases-dir`: Directory containing the DU-SSD LayoutLM outputs (default: /efs/shared/prod/doc-und/cases)
- `--labels-dir`: Directory where annotation files will be saved (default: annotation_labels)
- `--images-dir`: Directory where image files will be copied (default: annotation_images)
- `--images-file`: CSV file listing images to annotate (default: data/annotation_images.csv)
- `--output-dir`: Output directory for all generated files (override defaults for master-file, labels-dir, etc.)
- `--master-file`: Path for the master tracking file (default: data/master.xlsx)
- `--network-share`: Network share path where files will be copied
- `--csv-path-template`: Template for CSV file paths with variables {case_dir}, {case_id}, {page_id}
- `--image-path-template`: Template for image file paths with variables {case_dir}, {case_id}, {page_id}, {image_file}
- `--no-copy-images`: Skip copying image files to the annotation_images directory
- `--annotators`: List of annotator names (default: annotator1 annotator2)
- `--split-by-case`: Split the master file into separate Excel files for each case_id (default: enabled)
- `--no-split-by-case`: Do not create separate Excel files for each case_id
- `--verbose`: Enable verbose logging (DEBUG level)
- `--quiet`: Reduce output to warnings and errors only

#### Specifying an Output Directory

The `--output-dir` parameter allows you to specify an external location for all output files. This is particularly useful for KFP production environments where data needs to be stored outside the source directory:

```bash
./prepare_annotations.py --output-dir /efs/shared/dev-de/ude5g --cases-dir /efs/shared/prod/doc-und/cases
```

This will create the following structure:
```
/efs/shared/dev-de/ude5g/
├── annotation_images/      # Copied images
├── annotation_labels/      # Generated CSV files 
├── master.xlsx             # Master tracking file
└── cases/                  # Case-specific files
    ├── annotator1/         
    ├── annotator2/         
    └── index.xlsx          # Index of cases
```

#### Controlling Output Verbosity

The script supports three levels of output verbosity:

- **Normal mode** - Standard information messages:
  ```bash
  ./prepare_annotations.py
  ```

- **Verbose mode** - Detailed debug information:
  ```bash
  ./prepare_annotations.py --verbose
  ```

- **Quiet mode** - Only warnings and errors:
  ```bash
  ./prepare_annotations.py --quiet
  ```

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

## Annotation File Format Enhancements

The annotation files now feature two key improvements:

### 1. Excel Format with Sorting Capabilities

Annotation files are now saved as Excel (.xlsx) files instead of CSV, which provides:
- Ability to sort data by any column, including coordinate values
- Auto-filtering to quickly isolate specific items
- Formatted headers for better readability
- Proper numeric data types for coordinates
- Frozen header row to keep column names visible while scrolling

### 2. Extracted Coordinate Columns

The files include separate columns for bounding box coordinates, making it easier to work with the data:

- **Original bboxes column** - Contains the raw bounding box coordinates: `"(10, 20, 100, 40)"`
- **Extracted coordinate columns**:
  - `x1`: Upper-left x-coordinate (10)
  - `y1`: Upper-left y-coordinate (20)
  - `x2`: Lower-right x-coordinate (100)
  - `y2`: Lower-right y-coordinate (40)

This format simplifies data processing and analysis, especially when:
- Sorting items by their position on the page (e.g., top-to-bottom using y1)
- Finding elements within specific regions
- Calculating areas, overlaps, or visualizing the bounding boxes

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

### Output Directory Issues

If you're using the `--output-dir` parameter and see incorrect paths:

1. Make sure the output directory exists or has write permissions
2. Check for path separators in network share paths - use double backslashes on Windows (\\\\)
3. For absolute paths, ensure they start with "/" (Unix) or a drive letter (Windows)