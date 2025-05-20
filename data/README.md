# Data Files

This directory contains configuration and template files for the document annotation system.

## Important Files

- **annotation_images.csv**: List of images to annotate, with case_id and image_id columns
- **completion_updates.csv**: Template for batch-updating annotation status in the master file
- **master.csv**: Master file tracking annotation assignments and completion status

## Directory Structure

```
/
├── data/                   # Configuration and template files
│   ├── annotation_images.csv  # List of images to annotate
│   ├── master.csv          # Master tracking file
│   └── completion_updates.csv # Template for batch updates
├── du_cases/               # Main case directory structure
│   ├── case1/
│   │   ├── images/
│   │   │   ├── 9876543210_01_0.jpeg
│   │   │   └── ...
│   │   └── processing/
│   │       └── form-recogniser/
│   │           └── df_check.csv
│   └── ...
├── annotation_images/      # Image files for annotation
├── annotation_labels/      # Generated annotation files
└── reports/                # Generated reports
```

## File Formats

### annotation_images.csv
```
case_id,image_id
1-12ABCDEF,9876543210_01_0
1-12ABCDEF,9876543210_02_0
```

### completion_updates.csv
```
case_id,image_id,annotator,status
1-12ABCDEF,9876543210_01_0,annotator1,yes
1-15XYZWQP,1122334455_03_1,,yes
```

### master.csv
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

## Usage

1. Edit `annotation_images.csv` to specify which images need annotation
2. Run `./prepare_annotations.py` to create annotation files and update the master file
3. Use `completion_updates.csv` as a template for batch updates to annotation status