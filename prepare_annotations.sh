#!/bin/bash
#
# prepare_annotations.sh - Prepare annotation files and tracking data
#
# This script handles the essential tasks needed for annotators:
# 1. Reads the list of images to annotate from annotation_images.csv
# 2. Generates label files for only those specific images
# 3. Creates a master tracking file with those images

# Default values
CASES_DIR="du_cases"
LABELS_DIR="annotation_labels"
IMAGES_DIR="annotation_images"
IMAGES_FILE="data/annotation_images.csv"
MASTER_FILE="data/master.csv"
NETWORK_SHARE="\\\\server\\share"
COPY_IMAGES=true
ANNOTATORS=("annotator1" "annotator2")
CSV_PATH_TEMPLATE=""
IMAGE_PATH_TEMPLATE=""

# Help message
usage() {
  echo "Usage: $0 [OPTIONS]"
  echo
  echo "Options:"
  echo "  --cases-dir DIR       Directory containing the case structure (default: du_cases)"
  echo "  --labels-dir DIR      Directory where annotation files will be saved (default: annotation_labels)"
  echo "  --images-dir DIR      Directory where image files will be copied (default: annotation_images)"
  echo "  --images-file FILE    CSV file listing images to annotate (default: data/annotation_images.csv)"
  echo "  --master-file FILE    Path for the master tracking file (default: data/master.csv)"
  echo "  --network-share PATH  Network share path where files will be copied (default: \\\\server\\share)"
  echo "  --csv-path-template TEMPLATE  Template for CSV file paths. Variables: {case_dir}, {case_id}, {page_id}"
  echo "  --image-path-template TEMPLATE  Template for image file paths. Variables: {case_dir}, {case_id}, {page_id}, {image_file}"
  echo "  --no-copy-images      Skip copying image files to the annotation_images directory"
  echo "  --annotators LIST     Space-separated list of annotator names (default: 'annotator1 annotator2')"
  echo "  --help                Display this help message and exit"
  exit 1
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cases-dir)
      CASES_DIR="$2"
      shift 2
      ;;
    --labels-dir)
      LABELS_DIR="$2"
      shift 2
      ;;
    --images-dir)
      IMAGES_DIR="$2"
      shift 2
      ;;
    --images-file)
      IMAGES_FILE="$2"
      shift 2
      ;;
    --master-file)
      MASTER_FILE="$2"
      shift 2
      ;;
    --network-share)
      NETWORK_SHARE="$2"
      shift 2
      ;;
    --csv-path-template)
      CSV_PATH_TEMPLATE="$2"
      shift 2
      ;;
    --image-path-template)
      IMAGE_PATH_TEMPLATE="$2"
      shift 2
      ;;
    --no-copy-images)
      COPY_IMAGES=false
      shift
      ;;
    --annotators)
      # Read the annotators into an array
      ANNOTATORS=()
      shift
      while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do
        ANNOTATORS+=("$1")
        shift
      done
      ;;
    --help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

# Ensure we have at least 2 annotators
if [[ ${#ANNOTATORS[@]} -lt 2 ]]; then
  echo "Warning: At least 2 annotators are required. Using default names."
  ANNOTATORS=("annotator1" "annotator2")
fi

# Verify cases directory exists
if [[ ! -d "$CASES_DIR" ]]; then
  echo "Error: Cases directory not found: $CASES_DIR"
  exit 1
fi

# Print configuration
echo "Using network share: $NETWORK_SHARE"
echo "- Images will be linked to: ${NETWORK_SHARE}\\annotation_images\\"
echo "- Labels will be linked to: ${NETWORK_SHARE}\\annotation_labels\\"

# Step 1: Create the output directories if they don't exist
mkdir -p "$LABELS_DIR"
mkdir -p "$IMAGES_DIR"
mkdir -p "$(dirname "$MASTER_FILE")"

# Step 2: Load the list of images to annotate
if [[ ! -f "$IMAGES_FILE" ]]; then
  echo "Error: Images file not found: $IMAGES_FILE"
  exit 1
fi

# Check for required columns in the images file
header=$(head -n 1 "$IMAGES_FILE")
if [[ ! "$header" =~ case_id ]] || [[ ! "$header" =~ page_id ]]; then
  echo "Error: Images file must contain 'case_id' and 'page_id' columns"
  exit 1
fi

# Read the images file, using awk to parse the CSV more reliably
echo "Loading images to annotate from $IMAGES_FILE"
images=()

# Use awk to extract and process the CSV data, skipping the header line
while read -r line; do
  if [[ -n "$line" ]]; then
    images+=("$line")
    echo "  - $line"
  fi
done < <(awk -F, 'NR>1 {gsub(/[" ]/, "", $1); gsub(/[" ]/, "", $2); print $1 "," $2}' "$IMAGES_FILE")

echo "Loaded ${#images[@]} images to annotate"

# Step 3: Process each image
successful_files=()
successful_copies=()
failed_copies=()
missing_files=()

for img in "${images[@]}"; do
  IFS=, read -r case_id page_id <<< "$img"
  
  case_dir="$CASES_DIR/$case_id"
  if [[ ! -d "$case_dir" ]]; then
    missing_files+=("$case_id/$page_id: Case directory not found")
    continue
  fi
  
  # Build the CSV file path
  # Default CSV path
  csv_path="$case_dir/processing/form-recognizer/df_check.csv"
  
  # If a custom CSV path template is provided
  if [[ -n "$CSV_PATH_TEMPLATE" ]]; then
    # Replace variables in the template
    csv_path_template="$CSV_PATH_TEMPLATE"
    csv_path_template="${csv_path_template//\{case_dir\}/$case_dir}"
    csv_path_template="${csv_path_template//\{case_id\}/$case_id}"
    csv_path_template="${csv_path_template//\{page_id\}/$page_id}"
    csv_path="$csv_path_template"
  fi
  
  if [[ ! -f "$csv_path" ]]; then
    missing_files+=("$case_id/$page_id: CSV file not found at $csv_path")
    continue
  fi
  
  # Build the image file path 
  image_file="${page_id}.jpeg"
  # Default image path
  image_path="$case_dir/images/$image_file"
  
  # If a custom image path template is provided
  if [[ -n "$IMAGE_PATH_TEMPLATE" ]]; then
    # Replace variables in the template
    image_path_template="$IMAGE_PATH_TEMPLATE"
    image_path_template="${image_path_template//\{case_dir\}/$case_dir}"
    image_path_template="${image_path_template//\{case_id\}/$case_id}"
    image_path_template="${image_path_template//\{page_id\}/$page_id}"
    image_path_template="${image_path_template//\{image_file\}/$image_file}"
    image_path="$image_path_template"
  fi
  
  if [[ ! -f "$image_path" ]]; then
    missing_files+=("$case_id/$page_id: Image file not found at $image_path")
    continue
  fi
  
  # Copy the image file if requested
  if [[ "$COPY_IMAGES" = true ]]; then
    dest_file="${case_id}_${image_file}"
    dest_path="$IMAGES_DIR/$dest_file"
    
    if cp "$image_path" "$dest_path"; then
      echo "Copied image: $dest_path"
      successful_copies+=("$case_id,$page_id,$dest_file")
    else
      failed_copies+=("$case_id/$page_id: Error copying image")
      continue
    fi
  fi
  
  # Create the annotation file for this image
  label_file="${case_id}_${page_id}.csv"
  annotation_file="$LABELS_DIR/$label_file"
  
  # Extract data for this image from df_check.csv
  # 1. Get header line
  header=$(head -n 1 "$csv_path")
  # 2. Add the annotator_label column
  header_with_label="$header,annotator_label"
  
  # Get rows matching this image's id
  # First, check if the CSV uses page_id or image_id column
  if echo "$header" | grep -q "page_id"; then
    # Get column index for page_id (1-based for awk)
    id_col=$(echo "$header" | tr ',' '\n' | grep -n -i "page_id" | cut -d':' -f1)
  elif echo "$header" | grep -q "image_id"; then
    # Get column index for image_id (1-based for awk)
    id_col=$(echo "$header" | tr ',' '\n' | grep -n -i "image_id" | cut -d':' -f1)
  else
    # If neither page_id nor image_id found, use the first column
    id_col=1
  fi
  
  # Print debug information
  col_name=$(echo "$header" | tr ',' '\n' | sed -n "${id_col}p")
  echo "Looking for page_id '$page_id' in column $id_col ('$col_name')"
  available_values=$(awk -F, -v col="$id_col" '{print $col}' "$csv_path" | grep -v "^$col_name")
  echo "Available values in this column: $available_values"

  # Find rows matching this image's id (either page_id or image_id) with case-insensitive comparison
  # Using the 'tolower' function in awk for case-insensitive comparison
  image_rows=$(awk -F, -v col="$id_col" -v id="$page_id" 'tolower($col) == tolower(id) {print $0}' "$csv_path" | grep -v "^$header")
  
  if [[ -z "$image_rows" ]]; then
    missing_files+=("$case_id/$page_id: No data rows found for '$page_id' in '$col_name' column")
    continue
  fi
  
  # Create the annotation file
  echo "$header_with_label" > "$annotation_file"
  
  # Add all rows for this image, with an empty annotation column
  echo "$image_rows" | while read -r line; do
    echo "$line," >> "$annotation_file"
  done
  
  echo "Created annotation file: $annotation_file"
  successful_files+=("$case_id,$page_id,$image_file,$label_file")
done

# Report on failed copies
if [[ ${#failed_copies[@]} -gt 0 ]]; then
  echo -e "\nWarning: Could not copy these image files:"
  for msg in "${failed_copies[@]}"; do
    echo "  - $msg"
  done
fi

# Report on missing files
if [[ ${#missing_files[@]} -gt 0 ]]; then
  echo -e "\nWarning: Could not create annotation files for these images:"
  for msg in "${missing_files[@]}"; do
    echo "  - $msg"
  done
fi

echo -e "\nSuccessfully created ${#successful_files[@]} annotation files"

# Step 4: Create master tracking file
if [[ ${#successful_files[@]} -gt 0 ]]; then
  # Create CSV header
  echo "case_id,page_id,image_file_path,label_file_path,assignee1,has_assignee1_completed,assignee2,has_assignee2_completed,notes" > "$MASTER_FILE"
  
  # Add rows for each successful file
  for entry in "${successful_files[@]}"; do
    IFS=, read -r case_id page_id image_file label_file <<< "$entry"
    
    # Create the hyperlinks with Windows path format
    image_path="${NETWORK_SHARE}\\annotation_images\\${case_id}_${page_id}.jpeg"
    label_path="${NETWORK_SHARE}\\annotation_labels\\${case_id}_${page_id}.csv"
    
    # Create the CSV row with Excel HYPERLINK formulas
    echo "$case_id,$page_id,=HYPERLINK(\"$image_path\",\"View image\"),=HYPERLINK(\"$label_path\",\"View labels\"),${ANNOTATORS[0]},no,${ANNOTATORS[1]},no," >> "$MASTER_FILE"
  done
  
  echo "Created master tracking file with ${#successful_files[@]} entries: $MASTER_FILE"
fi

# Summary
echo -e "\nAnnotation preparation complete!"
if [[ "$COPY_IMAGES" = true ]]; then
  echo "- Copied ${#successful_copies[@]} image files to $IMAGES_DIR"
fi
echo "- Generated ${#successful_files[@]} annotation files in $LABELS_DIR"
echo "- Created master tracking file: $MASTER_FILE"
echo "- Images path in master file: ${NETWORK_SHARE}\\annotation_images\\"
echo "- Labels path in master file: ${NETWORK_SHARE}\\annotation_labels\\"

# Show warning if not all images were processed
if [[ ${#successful_files[@]} -lt ${#images[@]} ]]; then
  echo -e "\nWarning: $((${#images[@]} - ${#successful_files[@]})) images from $IMAGES_FILE were not found"
fi