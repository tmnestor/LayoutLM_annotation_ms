# DU-SSD Cases Directory Structure

This document outlines the directory structure for the Document Understanding (DU) cases stored at `/efs/shared/prod/doc-und/cases/`.

## Directory Structure

```
/efs/shared/prod/doc-und/cases/
├── 1-12ABCDEF/                # Example case directory (case ID)
│   ├── images/                # Original document images
│   │   ├── 9876543210_01_0.jpeg
│   │   ├── 9876543210_02_0.jpeg
│   │   └── ...
│   ├── image_id/              # Image ID directory inside case directory
│   │   └── extracted_text_json/   # JSON extraction results directory
│   │       ├── 9876543210_01_0.json  # JSON data for specific page
│   │       ├── 9876543210_02_0.json
│   │       └── ...
│   └── processing/            # Processing results
│       └── form-recogniser/   # LayoutLM processing outputs
│           └── df_check.csv   # Results for all pages in this case
├── 1-15XYZWQP/                # Another case directory
│   ├── images/
│   │   └── ...
│   ├── image_id/
│   │   └── extracted_text_json/
│   │       └── ...
│   └── processing/
│       └── form-recogniser/
│           └── df_check.csv
└── ...                        # More case directories
```

## Structure Details

### Case Directories

Each case is stored in its own directory, named using the case ID format `1-1DAAAAAA` where:
- `A` is an uppercase alphanumeric character
- `D` is a digit

### Image Files

The `images/` subdirectory contains the original document images with the naming convention:
- Format: `DDDDDDDDDD_DD_D.jpeg`
- Example: `9876543210_01_0.jpeg`
- All files are JPEG format

### JSON Files

The `image_id/extracted_text_json/` directory within each case contains:
- JSON data files for each page within that specific case
- Each JSON file is named after its corresponding image
- Format: `DDDDDDDDDD_DD_D.json`
- Contains structured extracted text data from the corresponding image

### Processing Results

The `processing/form-recogniser/` subdirectory within each case contains:
- `df_check.csv`: A CSV file with LayoutLM processing results for all images in the case
- This file contains columns for image_id, block_ids, word_ids, words, bboxes, labels, pred, and prob

## CSV Data Format

The `df_check.csv` file has the following columns:

| Column    | Description |
|-----------|-------------|
| image_id  | Identifier for the image (matches page_id in annotation_images.csv) |
| block_ids | Block identifier |
| word_ids  | Word identifier |
| words     | Text content |
| bboxes    | Bounding box coordinates in format "(ul_x, ul_y, lr_x, lr_y)" |
| labels    | Original label |
| pred      | Prediction value |
| prob      | Probability score |

Where bounding box coordinates use these conventions:
- ul_x, ul_y: Upper-left corner coordinates 
- lr_x, lr_y: Lower-right corner coordinates
- All coordinates are in the range 1-1000