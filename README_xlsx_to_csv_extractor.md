# Excel to CSV Column Extractor

A Python script that reads Excel (.xlsx) files from a directory and extracts specified columns by name to CSV files. Fully configurable via command line arguments.

## Features

- Extract specific columns by name (not index) from Excel files
- Process all Excel files in a directory
- Configurable input/output directories
- Support for specific Excel sheets
- Recursive directory search
- Column discovery mode to list available columns
- Flexible output naming options
- Error handling for missing columns

## Requirements

- Python 3.6+
- pandas
- xlsxwriter

## Installation

Install the required dependencies:

```bash
pip install pandas xlsxwriter
```

## Usage

### Basic Usage

Extract specific columns from all Excel files in the current directory:

```bash
python xlsx_to_csv_extractor.py --columns "Name,Email,Phone"
```

### Command Line Options

```
usage: xlsx_to_csv_extractor.py [-h] [--columns COLUMNS] [--input-dir INPUT_DIR]
                                [--output-dir OUTPUT_DIR] [--sheet SHEET]
                                [--keep-original-name] [--recursive]
                                [--list-columns FILE]

Extract specified columns from Excel files and save as CSV

optional arguments:
  -h, --help            show this help message and exit
  --columns COLUMNS     Comma-separated list of column names to extract
  --input-dir INPUT_DIR Directory containing Excel files (default: current directory)
  --output-dir OUTPUT_DIR Directory to save CSV files (default: current directory)
  --sheet SHEET         Name of the Excel sheet to read (default: first sheet)
  --keep-original-name  Keep original filename for CSV output (default: add "_extracted" suffix)
  --recursive           Search for Excel files recursively in subdirectories
  --list-columns FILE   List all column names in the specified Excel file and exit
```

### Examples

#### 1. List Available Columns

Before extracting, see what columns are available in an Excel file:

```bash
python xlsx_to_csv_extractor.py --list-columns data/sample.xlsx
```

Output:
```
Columns in sample.xlsx:
   1. Name
   2. Email
   3. Phone
   4. Department
   5. Salary

Total columns: 5
```

#### 2. Extract Specific Columns

Extract Name, Email, and Phone columns from all Excel files:

```bash
python xlsx_to_csv_extractor.py --columns "Name,Email,Phone"
```

#### 3. Custom Input/Output Directories

Process files from a specific directory and save to another:

```bash
python xlsx_to_csv_extractor.py --columns "ID,Status,Date" --input-dir data/excel/ --output-dir output/csv/
```

#### 4. Extract from Specific Sheet

Extract columns from a specific worksheet:

```bash
python xlsx_to_csv_extractor.py --columns "A,B,C" --sheet "Sheet2"
```

#### 5. Keep Original Filenames

By default, the script adds "_extracted" suffix to output files. To keep original names:

```bash
python xlsx_to_csv_extractor.py --columns "Name,Value" --keep-original-name
```

#### 6. Recursive Directory Search

Search for Excel files in subdirectories:

```bash
python xlsx_to_csv_extractor.py --columns "Name,Age" --recursive --input-dir projects/
```

#### 7. Process Multiple Directories

Process files from multiple locations:

```bash
# Process data directory
python xlsx_to_csv_extractor.py --columns "case_id,status" --input-dir data/cases/annotator1/ --output-dir output/annotator1/

# Process another directory
python xlsx_to_csv_extractor.py --columns "case_id,status" --input-dir data/cases/annotator2/ --output-dir output/annotator2/
```

## Output

### Default Behavior
- Input: `report.xlsx` → Output: `report_extracted.csv`
- Missing columns are reported but don't stop processing
- Only available columns are extracted

### With --keep-original-name
- Input: `report.xlsx` → Output: `report.csv`

## Error Handling

The script handles several error conditions gracefully:

1. **Missing Columns**: If some requested columns don't exist, the script:
   - Warns about missing columns
   - Extracts only the available columns
   - Continues processing

2. **No Matching Columns**: If none of the requested columns exist:
   - Reports an error for that file
   - Skips the file
   - Continues with other files

3. **File Read Errors**: If an Excel file can't be read:
   - Reports the specific error
   - Skips the file
   - Continues processing

## Use Cases

### 1. Data Analysis Pipeline
Extract specific columns for analysis while keeping original data intact:

```bash
# Extract only the columns needed for analysis
python xlsx_to_csv_extractor.py --columns "timestamp,value,category" --input-dir raw_data/ --output-dir analysis/
```

### 2. Data Migration
Convert Excel reports to CSV format for database import:

```bash
# Extract database-relevant columns
python xlsx_to_csv_extractor.py --columns "id,name,email,created_date" --input-dir exports/ --output-dir import_ready/
```

### 3. Report Generation
Extract summary columns from detailed reports:

```bash
# Extract summary information
python xlsx_to_csv_extractor.py --columns "project_id,status,completion_date,budget" --input-dir reports/ --output-dir summaries/
```

### 4. Quality Assurance
Extract specific columns for validation:

```bash
# Extract columns for QA review
python xlsx_to_csv_extractor.py --columns "case_id,assignee1,has_assignee1_completed,assignee2,has_assignee2_completed" --input-dir data/cases/
```

## Tips

1. **Discover Columns First**: Always use `--list-columns` to see available column names before extraction

2. **Handle Spaces**: Column names with spaces should be quoted:
   ```bash
   python xlsx_to_csv_extractor.py --columns "First Name,Last Name,Email Address"
   ```

3. **Batch Processing**: Use shell loops for complex batch operations:
   ```bash
   for dir in data/cases/*/; do
       python xlsx_to_csv_extractor.py --columns "id,status" --input-dir "$dir" --output-dir "output/$(basename "$dir")/"
   done
   ```

4. **Check Output**: The script reports successful and failed extractions at the end

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Install required packages:
   ```bash
   pip install pandas xlsxwriter
   ```

2. **No Excel files found**: Check the input directory path and ensure it contains .xlsx files

3. **Permission errors**: Ensure you have read access to input files and write access to output directory

4. **Column name mismatch**: Use `--list-columns` to see exact column names (case-sensitive)

### Debug Mode

For detailed error information, you can modify the script to add more verbose output or run with Python's verbose flag:

```bash
python -v xlsx_to_csv_extractor.py --columns "Name,Email"
```

## License

This script is provided as-is for data processing tasks. Modify and distribute as needed.