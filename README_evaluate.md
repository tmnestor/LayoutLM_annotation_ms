# LayoutLM Evaluation Script

A comprehensive evaluation script for LayoutLM form understanding tasks. This script computes both token-level and page-level metrics from CSV prediction files and provides detailed analysis of model performance.

## Features

- **Token-level metrics**: Accuracy, F1-scores (macro, micro, weighted), classification report, confusion matrix
- **Page-level metrics**: Per-page accuracy and F1 scores with statistical summaries
- **Flexible input**: Processes multiple CSV files containing predictions and ground truth labels
- **Detailed reporting**: Optional detailed results including per-class and per-page breakdowns
- **Logging**: Comprehensive logging with configurable levels
- **JSON output**: Machine-readable summary metrics for downstream analysis

## Requirements

- Python 3.6+
- pandas
- numpy
- scikit-learn

## Installation

Install the required dependencies:

```bash
pip install pandas numpy scikit-learn
```

## Input Data Format

The script expects CSV files with the following required columns:

- `bboxes`: Bounding box coordinates (format varies)
- `pred`: Predicted class labels (integer or string)
- `prob`: Prediction probabilities/confidence scores
- `labels`: Ground truth labels (integer or string)

### Example CSV structure:
```csv
image_id,block_ids,word_ids,words,bboxes,labels,pred,prob
9876543210_01_0,1,1,"Invoice","(100,200,300,400)",header,header,0.95
9876543210_01_0,2,2,"Date","(400,200,500,300)",field_name,field_name,0.87
```

## Usage

### Basic Usage

Evaluate predictions from CSV files in a directory:

```bash
python evaluate.py --predictions_dir data/predictions/
```

### Command Line Options

```
usage: evaluate.py [-h] --predictions_dir PREDICTIONS_DIR [--output_dir OUTPUT_DIR]
                   [--num_classes NUM_CLASSES] [--class_names_file CLASS_NAMES_FILE]
                   [--log_level {DEBUG,INFO,WARNING,ERROR}] [--save_detailed_results]

Evaluate LayoutLM predictions from CSV files

required arguments:
  --predictions_dir PREDICTIONS_DIR
                        Directory containing CSV prediction files (one per page)

optional arguments:
  -h, --help            show this help message and exit
  --output_dir OUTPUT_DIR
                        Directory to save evaluation results (default: ./results)
  --num_classes NUM_CLASSES
                        Number of classification categories (default: 58)
  --class_names_file CLASS_NAMES_FILE
                        Path to file containing class names
  --log_level {DEBUG,INFO,WARNING,ERROR}
                        Logging level (default: INFO)
  --save_detailed_results
                        Save detailed per-class and per-page results
```

### Examples

#### 1. Basic Evaluation

Evaluate predictions with default settings:

```bash
python evaluate.py --predictions_dir du_cases/1-12ABCDEF/processing/form-recogniser/
```

#### 2. Custom Output Directory

Save results to a specific directory:

```bash
python evaluate.py --predictions_dir predictions/ --output_dir evaluation_results/
```

#### 3. Detailed Analysis

Generate detailed per-class and per-page results:

```bash
python evaluate.py --predictions_dir predictions/ --save_detailed_results
```

#### 4. Custom Logging Level

Run with debug logging for troubleshooting:

```bash
python evaluate.py --predictions_dir predictions/ --log_level DEBUG
```

#### 5. Specify Number of Classes

For models with different numbers of output classes:

```bash
python evaluate.py --predictions_dir predictions/ --num_classes 25
```

## Output Files

The script generates several output files in the specified output directory:

### Standard Output

1. **`summary_metrics.json`**: Summary of all metrics in JSON format
2. **`eval_config.json`**: Configuration used for evaluation
3. **`evaluation.log`**: Detailed execution log

### Detailed Output (with --save_detailed_results)

4. **`classification_report.csv`**: Per-class precision, recall, F1-score
5. **`confusion_matrix.csv`**: Confusion matrix showing prediction vs ground truth
6. **`per_page_results.csv`**: Individual page-level metrics

### Sample Output Structure

```
results/
├── summary_metrics.json
├── eval_config.json
├── evaluation.log
├── classification_report.csv      # (if --save_detailed_results)
├── confusion_matrix.csv           # (if --save_detailed_results)
└── per_page_results.csv          # (if --save_detailed_results)
```

## Metrics Explained

### Token-Level Metrics

- **Accuracy**: Overall percentage of correctly classified tokens
- **F1 Macro**: Average F1 score across all classes (unweighted)
- **F1 Micro**: F1 score computed globally across all tokens
- **F1 Weighted**: F1 score weighted by class support

### Page-Level Metrics

- **Page Accuracy Mean/Std**: Statistics of per-page accuracy scores
- **Page F1 Mean/Std**: Statistics of per-page F1 scores
- **Perfect Accuracy Pages**: Number of pages with 100% accuracy
- **Total Pages**: Number of pages evaluated

## Console Output

The script provides a comprehensive summary printed to the console:

```
==================================================
LAYOUTLM EVALUATION SUMMARY
==================================================
Total tokens evaluated: 15420
Total pages evaluated: 142
Average tokens per page: 108.6

TOKEN-LEVEL METRICS:
  Accuracy: 0.8945
  F1 (macro): 0.7821
  F1 (micro): 0.8945
  F1 (weighted): 0.8834

PAGE-LEVEL METRICS:
  Accuracy (mean): 0.7324
  Accuracy (std): 0.2145
  F1 (mean): 0.6892
  F1 (std): 0.2398
  Perfect accuracy pages: 23
==================================================
```

## Use Cases

### 1. Model Development

Evaluate model performance during development:

```bash
# Quick evaluation during development
python evaluate.py --predictions_dir model_outputs/epoch_10/

# Detailed analysis for model comparison
python evaluate.py --predictions_dir model_outputs/final/ --save_detailed_results --output_dir final_eval/
```

### 2. Hyperparameter Tuning

Compare different model configurations:

```bash
# Evaluate different model variants
for model in model_v1 model_v2 model_v3; do
    python evaluate.py --predictions_dir outputs/$model/ --output_dir results/$model/
done
```

### 3. Production Monitoring

Monitor model performance in production:

```bash
# Weekly evaluation
python evaluate.py --predictions_dir production_outputs/week_42/ --output_dir monitoring/week_42/ --save_detailed_results
```

### 4. Research Analysis

Detailed analysis for research papers:

```bash
# Full analysis with all metrics
python evaluate.py \
    --predictions_dir research_outputs/ \
    --output_dir paper_results/ \
    --save_detailed_results \
    --log_level DEBUG
```

## Troubleshooting

### Common Issues

1. **Missing columns error**:
   ```
   ValueError: Missing columns in file.csv: ['pred', 'prob']
   ```
   - Ensure all CSV files have required columns: `bboxes`, `pred`, `prob`, `labels`

2. **No CSV files found**:
   ```
   ValueError: No CSV files found in directory
   ```
   - Check that the predictions directory contains .csv files
   - Verify the directory path is correct

3. **Memory issues with large datasets**:
   - Process files in smaller batches
   - Use more efficient data types if possible

### Performance Tips

1. **Large datasets**: For very large datasets, consider processing in chunks
2. **File organization**: Organize prediction files with meaningful names for easier tracking
3. **Logging**: Use appropriate log levels (INFO for normal use, DEBUG for troubleshooting)

## Integration with Other Scripts

This evaluation script works well with other scripts in the annotation pipeline:

```bash
# 1. Prepare annotations
python prepare_annotations.py

# 2. Run model inference (external)
# your_model_inference.py --input annotations/ --output predictions/

# 3. Evaluate results
python evaluate.py --predictions_dir predictions/ --save_detailed_results
```

## Advanced Usage

### Custom Class Names

If you have a file with class names (one per line):

```bash
python evaluate.py --predictions_dir predictions/ --class_names_file classes.txt
```

### Batch Evaluation

Evaluate multiple directories:

```bash
#!/bin/bash
for case_dir in du_cases/*/processing/form-recogniser/; do
    case_name=$(basename $(dirname $(dirname "$case_dir")))
    python evaluate.py \
        --predictions_dir "$case_dir" \
        --output_dir "results/$case_name" \
        --save_detailed_results
done
```

## Output Analysis

### JSON Metrics

The `summary_metrics.json` file contains all metrics in a structured format for programmatic analysis:

```json
{
  "token_accuracy": 0.8945,
  "token_f1_macro": 0.7821,
  "token_f1_micro": 0.8945,
  "token_f1_weighted": 0.8834,
  "page_accuracy_mean": 0.7324,
  "page_accuracy_std": 0.2145,
  "pages_perfect_accuracy": 23,
  "total_pages": 142,
  "total_tokens": 15420,
  "avg_tokens_per_page": 108.6
}
```

### CSV Analysis

Use the detailed CSV outputs for deeper analysis:

```python
import pandas as pd

# Load per-page results
page_results = pd.read_csv('results/per_page_results.csv')

# Find pages with low accuracy
low_accuracy_pages = page_results[page_results['accuracy'] < 0.5]

# Load classification report
class_report = pd.read_csv('results/classification_report.csv', index_col=0)
worst_classes = class_report.sort_values('f1-score').head(10)
```

## License

This evaluation script is provided as-is for LayoutLM model evaluation tasks. Modify and distribute as needed.