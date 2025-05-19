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
- LayoutLM output results are stored in CSV format with a page_id column
- Annotation data is extracted to individual files for human review

## LayoutLM Annotation Management System Directory Structure

```
/
├── data/                   # Configuration and template files
│   ├── annotation_images.csv  # List of images to annotate
│   ├── master.csv          # Master tracking file
│   └── completion_updates.csv # Template for batch updates
├── du_cases/               # Main case directory structure
│   ├── 1-12ABCDEF/         # Example case directory
│   │   ├── images/         # Contains all page images for this case
│   │   │   ├── 9876543210_01_0.jpeg
│   │   │   └── ...
│   │   └── processing/
│   │       └── form-recogniser/ 
│   │           └── df_check.csv  # LayoutLM processing results
├── annotation_labels/       # Generated annotation files
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

### How df_check.csv is Used

1. The system reads `data/annotation_images.csv` to get a list of images to process
2. For each (case_id, page_id) pair, it looks for matching records in `df_check.csv` where:
   - The system looks for the `image_id` column in df_check.csv
   - It searches for rows where `image_id` **exactly matches** the `page_id` value from annotation_images.csv
3. All matching rows are extracted to create individual annotation CSV files
4. An additional `annotator_label` column is added for human annotations

### Troubleshooting Common Issues

#### df_check.csv Errors

If you encounter errors like "No data rows found for [page_id] in 'image_id' column", check:
1. The `image_id` values in df_check.csv match exactly with the `page_id` values in annotation_images.csv
2. The df_check.csv exists in the expected location
3. The df_check.csv contains the proper column headers
4. The df_check.csv has entries for all required page_id values

#### Excel Hyperlink Issues

If hyperlinks in Excel don't work correctly:

1. **Use mapped drives instead of UNC paths**: 
   ```bash
   ./prepare_annotations.py --network-share Z:
   ```
   
2. **Check for extra quotes**: If your hyperlinks have double quotes like `""Z:\path""`, this may be due to Excel's CSV handling. The scripts have been updated to prevent this issue.

3. **Manual fix in Excel**: If hyperlinks still don't work, you can select the columns with hyperlinks in Excel, right-click and choose "Remove Hyperlink", then select all cells again and use the HYPERLINK function to recreate them.

## Quick Start

To prepare annotation files for a specific list of images:

```bash
./prepare_annotations.py
```

This single script will:
1. Read the list of images from `data/annotation_images.csv`
2. Generate annotation files only for those images in the `annotation_labels/` directory
3. Create a master tracking file in `data/master.csv`
4. Provide a summary of how many images were processed

## Example Use Cases

### 1. Standard Workflow

```bash
# Standard usage with default paths
./prepare_annotations.py
```

### 2. Custom File Locations

When images and CSV files are in non-standard locations:

```bash
./prepare_annotations.py \
  --csv-path-template "/data/{case_id}/results/{page_id}_analysis.csv" \
  --image-path-template "/scans/{case_id}/pages/{page_id}.jpeg"
```

### 3. Windows Network Share

Generate hyperlinks pointing to a Windows share:

```bash
# Using UNC path
./prepare_annotations.py --network-share "\\\\server\\share"

# Using mapped network drive (recommended for Excel compatibility)
./prepare_annotations.py --network-share Z:
```

### 4. Full Custom Configuration

```bash
./prepare_annotations.py \
  --network-share "\\\\server\\share" \
  --csv-path-template "/data/{case_id}/results/{page_id}_analysis.csv" \
  --image-path-template "/scans/{case_id}/pages/{page_id}.jpeg" \
  --labels-dir "custom_labels" \
  --annotators "john" "sarah" "mike"
```

## Workflow

The typical workflow for using this system is:

1. **Specify images to annotate**
   - Edit `data/annotation_images.csv` to list the case_id and page_id of each image to annotate
   - Format: CSV with columns 'case_id' and 'page_id'

2. **Generate annotation files and master tracking file**
   - Run `./prepare_annotations.py` to create individual annotation files and the master tracking file
   - Each annotation file contains LayoutLM data with an additional column for annotations
   - The master tracking file (data/master.csv) will be automatically generated with the necessary information

3. **Track annotation progress**
   - Use `./update_master_file.py` to update the completion status of annotations
   - Generate reports with `./generate_report.py` to monitor progress

4. **Perform annotation**
   - Annotators review each image and add labels
   - Update the master file to track progress

## Cross-System Workflow

When images and labels will be accessed from a different system than where you prepare them:

1. **Prepare files locally**
   - Edit `data/annotation_images.csv` with the images to annotate
   - Run prepare_annotations.py with the network share option and copy-images option:
   
     **For Windows mapped drives (recommended for Excel compatibility):**
     ```bash
     ./prepare_annotations.py --network-share Z:
     ```
     
     This approach uses a mapped network drive (Z:) instead of a UNC path, which often works better with Excel hyperlinks.
     The Excel HYPERLINK formulas will have paths like: `Z:\annotation_images\...`
     
     **For Windows network share with UNC path:**
     ```bash
     ./prepare_annotations.py --network-share "\\\\server\\share"
     ```
     
     This automatically enables Windows path format in the master file and copies images.
     
     **Note:** Double backslashes are needed in the paths to escape them properly.
     The Excel HYPERLINK formulas will have paths like: `\\server\share\annotation_images\...`
     
     **Alternative UNC path format:**
     ```bash
     ./prepare_annotations.py --network-share "//server/share"
     ```
     
     **Custom image and CSV file locations:**
     
     If your files are in non-standard locations, you can use templates to specify where to find them:
     
     ```bash
     ./prepare_annotations.py --network-share "\\\\server\\share" \
       --csv-path-template "/data/form_results/{case_id}/analysis/{page_id}_form.csv" \
       --image-path-template "/archives/scans/{case_id}/pages/{page_id}.jpeg"
     ```
     
     The templates support these variables:
     - `{case_dir}`: The full path to the case directory
     - `{case_id}`: The case ID
     - `{page_id}`: The page ID
     - `{image_file}`: The image filename including extension (for image template only)
   
   - This generates:
     - Local annotation files in your local `annotation_labels/` directory
     - Image files copied to your local `annotation_images/` directory
     - A master file with hyperlinks pointing to the Windows network paths

2. **Copy files to network location**
   - Copy/move your local `annotation_images` directory to the Windows share
   - Copy/move your local `annotation_labels` directory to the Windows share
   
   **Using Windows Explorer:**
   - Map the network drive or access it via `\\server\share\`
   - Copy the files using Windows Explorer
   
   **Using command line (if applicable):**
   - For Windows Command Prompt:
     ```cmd
     xcopy annotation_images \\server\share\annotation_images /E /I /Y
     xcopy annotation_labels \\server\share\annotation_labels /E /I /Y
     ```
   - For PowerShell:
     ```powershell
     Copy-Item -Path "annotation_images" -Destination "\\server\share\annotation_images" -Recurse -Force
     Copy-Item -Path "annotation_labels" -Destination "\\server\share\annotation_labels" -Recurse -Force
     ```

3. **Distribute master file to annotators**
   - Share the master.csv file with annotators
   - The hyperlinks will correctly point to the Windows network share paths
   - Annotators can click the links to access images and label files directly from the Windows share

This approach separates the file generation process from the locations where files will be used. The HYPERLINK formulas in the master file will contain Windows UNC paths (e.g., `\\server\share\...`) that will work properly when opened in Excel on Windows systems.

## Scripts

### prepare_annotations.py

Create annotation files for the specified images and generate a master tracking file:

```bash
# Basic usage (local paths)
./prepare_annotations.py

# Standard network share option (recommended)
./prepare_annotations.py --network-share "\\\\server\\share"

# For Unix/Linux paths in the master file (with network share)
./prepare_annotations.py --network-share "//server/share"

# With custom CSV and image paths
./prepare_annotations.py --csv-path-template "{case_dir}/custom/path/{case_id}_data.csv" \
                       --image-path-template "{case_dir}/documents/{page_id}.jpeg"
```

**Important Notes**:
- The script creates local annotation files and copies images to annotation_images/ for transfer
- The hyperlinks in the master file point to the Windows network share locations
- Images are copied to annotation_images/ by default (use --no-copy-images to skip)
- You'll need to copy the annotation_labels/ and annotation_images/ directories to the Windows share location after running the script

Options:
- `--cases-dir`: Directory containing the DU-SSD LayoutLM outputs (default: du_cases)
- `--labels-dir`: Directory where annotation files will be saved (default: annotation_labels)
- `--images-dir`: Directory where image files will be copied (default: annotation_images)
- `--images-file`: CSV file listing images to annotate (default: data/annotation_images.csv)
- `--master-file`: Path for the master tracking file (default: data/master.csv)
- `--network-share`: Network share path where files will be copied (default: \\\\server\\share)
- `--csv-path-template`: Template for CSV file paths with variables {case_dir}, {case_id}, {page_id}
- `--image-path-template`: Template for image file paths with variables {case_dir}, {case_id}, {page_id}, {image_file}
- `--no-copy-images`: Skip copying image files to the annotation_images directory
- `--annotators`: List of annotator names (default: annotator1 annotator2)

### update_master_file.py

Update the completion status of annotations in the master file:

```bash
# Update from a CSV file with status information
./update_master_file.py --master-file data/master.csv from-file data/completion_updates.csv

# Update specific entries
./update_master_file.py --master-file data/master.csv specific \
                        --case-ids "1-12ABCDEF" "1-15XYZWQP" \
                        --annotators "annotator1" \
                        --status yes
```

The update file should contain the following columns:
```
case_id,image_id,annotator,status
1-12ABCDEF,9876543210_01_0,annotator1,yes
```

If the annotator column is left empty, both annotators will be updated.

### generate_report.py

Generate reports based on the annotation progress:

```bash
# Generate all available reports
./generate_report.py --master-file data/master.csv --output-dir reports

# Generate a specific report type
./generate_report.py --master-file data/master.csv --output-dir reports --report-type progress
```

Available report types:
- `progress` - Annotation progress by case
- `annotator` - Annotator productivity
- `all` - Generate all report types (default)

Reports are generated in Markdown format and include:
- Overall completion statistics
- Per-case progress
- Per-annotator productivity metrics

## File Formats

### data/annotation_images.csv
```
case_id,image_id
1-12ABCDEF,9876543210_01_0
1-12ABCDEF,9876543210_02_0
```

### data/master.csv
Contains columns:
- case_id
- image_id
- image_file_path (as an Excel HYPERLINK formula)
- label_file_path (as an Excel HYPERLINK formula)
- assignee1
- has_assignee1_completed
- assignee2
- has_assignee2_completed
- notes

### annotation_labels/*.csv
Contains form recognition data with an added annotator_label column.

### du_cases/{case_id}/processing/form-recogniser/df_check.csv
Contains the LayoutLM model output data with columns:
```
image_id,block_ids,word_ids,words,bboxes,labels,pred,prob
9876543210_01_0,1,10,form,"(10, 20, 100, 40)",FIELD,0,0.95
```

**CRITICAL**: The `image_id` column in this file must contain values that exactly match the `page_id` values in `data/annotation_images.csv`. This is the key matching field used to extract the right data for each image. If this matching fails, you'll see errors like "No data rows found for [page_id] in 'image_id' column".