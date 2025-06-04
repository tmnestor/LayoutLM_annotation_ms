#!/usr/bin/env python3
"""
Update Annotation Files with Top-K Predictions

This script updates existing annotation files by:
1. Decoding numeric predictions using the standard_labels vocabulary
2. Filling annotator columns with the decoded predictions
3. Handling top-k predictions by selecting the best one for each token
4. Preserving existing manual annotations when present

Usage:
    python update_annotations_with_predictions.py annotation_labels --backup
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger('update_annotations')

# Standard labels for annotation (58 values) - from prepare_annotations.py
STANDARD_LABELS = [
    'O', 'B-PER', 'I-PER', 'B-ORG', 'I-ORG', 'B-LOC', 'I-LOC', 'B-DATE', 'I-DATE',
    'B-MONEY', 'I-MONEY', 'B-MISC', 'I-MISC', 'B-ADDRESS', 'I-ADDRESS', 'B-PHONE', 'I-PHONE',
    'B-EMAIL', 'I-EMAIL', 'B-URL', 'I-URL', 'B-PRODUCT', 'I-PRODUCT', 'B-EVENT', 'I-EVENT',
    'B-TITLE', 'I-TITLE', 'B-QUANTITY', 'I-QUANTITY', 'B-ORDINAL', 'I-ORDINAL', 'B-CARDINAL', 'I-CARDINAL',
    'B-FACILITY', 'I-FACILITY', 'B-GPE', 'I-GPE', 'B-LANGUAGE', 'I-LANGUAGE', 'B-NORP', 'I-NORP',
    'B-WORK_OF_ART', 'I-WORK_OF_ART', 'B-LAW', 'I-LAW', 'B-TIME', 'I-TIME', 'B-PERCENT', 'I-PERCENT',
    'HEADER', 'FOOTER', 'TITLE', 'SUBTITLE', 'PARAGRAPH', 'LIST_ITEM', 'TABLE_HEADER', 'TABLE_CELL',
    'CAPTION', 'FOOTNOTE', 'PAGE_NUMBER', 'SECTION'
]


def create_label_mapping() -> Dict[int, str]:
    """
    Create mapping from numeric indices to label strings.
    
    Returns:
        Dictionary mapping index to label
    """
    return {i: label for i, label in enumerate(STANDARD_LABELS)}


def decode_prediction(pred_value, label_mapping: Dict[int, str]) -> str:
    """
    Decode a single prediction value to its corresponding label.
    
    Args:
        pred_value: Numeric prediction value or string
        label_mapping: Dictionary mapping indices to labels
        
    Returns:
        Decoded label string
    """
    try:
        # Handle various input types
        if pd.isna(pred_value):
            return "O"  # Default to O for missing predictions
        
        # Try to convert to integer
        if isinstance(pred_value, str):
            try:
                pred_int = int(pred_value)
            except ValueError:
                # If already a string label, return as-is
                return pred_value
        else:
            pred_int = int(pred_value)
        
        # Look up the label
        return label_mapping.get(pred_int, f"UNK_{pred_int}")
        
    except (ValueError, TypeError):
        # If can't convert, return as string or default
        return str(pred_value) if pred_value is not None else "O"


def deduplicate_top_k_predictions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deduplicate top-k predictions by keeping only the highest probability prediction
    for each unique word/position combination.
    
    Args:
        df: DataFrame with potentially multiple predictions per token
        
    Returns:
        DataFrame with deduplicated predictions
    """
    # Define key columns that identify unique tokens
    key_columns = []
    for col_name in ['image_id', 'block_ids', 'word_ids', 'words', 'bboxes']:
        if col_name in df.columns:
            key_columns.append(col_name)
    
    if not key_columns:
        logger.warning("No key columns found for deduplication - returning original data")
        return df
    
    # Check if prob column exists
    if 'prob' not in df.columns:
        logger.warning("No 'prob' column found - cannot deduplicate by probability")
        return df
    
    logger.info(f"Deduplicating based on columns: {key_columns}")
    
    # Group by unique token and keep highest probability
    def get_best_prediction(group):
        """Get the row with highest probability for this token group."""
        if len(group) == 1:
            return group.iloc[0]
        
        # Find row with highest probability
        max_prob_idx = group['prob'].idxmax()
        return group.loc[max_prob_idx]
    
    # Group by key columns and apply deduplication
    deduplicated = df.groupby(key_columns).apply(get_best_prediction).reset_index(drop=True)
    
    original_count = len(df)
    final_count = len(deduplicated)
    removed_count = original_count - final_count
    
    if removed_count > 0:
        logger.info(f"Deduplicated {original_count} rows to {final_count} rows "
                   f"(removed {removed_count} duplicate top-k predictions)")
    
    return deduplicated


def update_annotation_file(file_path: Union[str, Path], 
                          label_mapping: Dict[int, str],
                          backup: bool = True) -> Dict:
    """
    Update a single annotation file with decoded predictions.
    
    Args:
        file_path: Path to the annotation Excel file
        label_mapping: Dictionary mapping prediction indices to labels
        backup: Whether to create backup before updating
        
    Returns:
        Dictionary with update statistics
    """
    file_path = Path(file_path)
    
    stats = {
        'file': file_path.name,
        'original_rows': 0,
        'final_rows': 0,
        'predictions_decoded': 0,
        'annotator1_filled': 0,
        'annotator2_filled': 0,
        'duplicates_removed': 0,
        'success': False,
        'error': None
    }
    
    try:
        # Create backup if requested
        if backup:
            backup_path = file_path.parent / f"{file_path.stem}_backup{file_path.suffix}"
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Created backup: {backup_path.name}")
        
        # Read the annotation file
        df = pd.read_excel(file_path, sheet_name='Annotation')
        stats['original_rows'] = len(df)
        
        logger.info(f"Processing {file_path.name} with {len(df)} rows")
        
        # Deduplicate top-k predictions first
        df_dedup = deduplicate_top_k_predictions(df)
        stats['duplicates_removed'] = len(df) - len(df_dedup)
        df = df_dedup
        
        # Decode predictions if pred column exists
        if 'pred' in df.columns:
            logger.debug("Decoding numeric predictions to labels")
            df['pred_decoded'] = df['pred'].apply(lambda x: decode_prediction(x, label_mapping))
            
            # Count how many predictions were decoded
            stats['predictions_decoded'] = (~df['pred_decoded'].isna()).sum()
        else:
            logger.warning(f"No 'pred' column found in {file_path.name}")
            df['pred_decoded'] = 'O'  # Default value
        
        # Ensure annotator columns exist
        if 'annotator1_label' not in df.columns:
            df['annotator1_label'] = ''
        if 'annotator2_label' not in df.columns:
            df['annotator2_label'] = ''
        
        # Fill annotator columns with decoded predictions where empty
        # Only fill if the cell is empty/NaN/blank
        ann1_mask = (df['annotator1_label'].isna()) | (df['annotator1_label'] == '') | (df['annotator1_label'] == 'nan')
        ann2_mask = (df['annotator2_label'].isna()) | (df['annotator2_label'] == '') | (df['annotator2_label'] == 'nan')
        
        if ann1_mask.any():
            df.loc[ann1_mask, 'annotator1_label'] = df.loc[ann1_mask, 'pred_decoded']
            stats['annotator1_filled'] = ann1_mask.sum()
        
        if ann2_mask.any():
            df.loc[ann2_mask, 'annotator2_label'] = df.loc[ann2_mask, 'pred_decoded']
            stats['annotator2_filled'] = ann2_mask.sum()
        
        # Remove the temporary decoded column
        if 'pred_decoded' in df.columns:
            df = df.drop('pred_decoded', axis=1)
        
        stats['final_rows'] = len(df)
        
        # Write back to Excel file
        # Read other sheets to preserve them
        try:
            with pd.ExcelFile(file_path) as excel_file:
                sheets = excel_file.sheet_names
        except Exception:
            sheets = ['Annotation']  # Fallback if can't read sheets
        
        # Write back with all sheets
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Write the updated annotation sheet
            df.to_excel(writer, sheet_name='Annotation', index=False)
            
            # Copy other sheets if they exist
            for sheet_name in sheets:
                if sheet_name != 'Annotation':
                    try:
                        sheet_df = pd.read_excel(file_path, sheet_name=sheet_name)
                        sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
                    except Exception as e:
                        logger.debug(f"Could not copy sheet {sheet_name}: {e}")
        
        stats['success'] = True
        logger.info(f"Successfully updated {file_path.name}")
        
    except Exception as e:
        error_msg = f"Error processing {file_path.name}: {str(e)}"
        logger.error(error_msg)
        stats['error'] = error_msg
    
    return stats


def update_annotation_directory(annotation_dir: Union[str, Path],
                               backup: bool = True) -> Dict:
    """
    Update all annotation files in a directory with decoded predictions.
    
    Args:
        annotation_dir: Directory containing annotation files
        backup: Whether to create backups before updating
        
    Returns:
        Dictionary with overall update statistics
    """
    annotation_path = Path(annotation_dir)
    
    if not annotation_path.exists():
        logger.error(f"Directory not found: {annotation_dir}")
        return {}
    
    # Find all Excel files
    xlsx_files = list(annotation_path.glob("*.xlsx"))
    
    if not xlsx_files:
        logger.warning(f"No .xlsx files found in {annotation_dir}")
        return {}
    
    logger.info(f"Found {len(xlsx_files)} annotation files to update")
    logger.info(f"Using {len(STANDARD_LABELS)} standard labels for decoding")
    logger.info(f"Backup: {'enabled' if backup else 'disabled'}")
    
    # Create label mapping
    label_mapping = create_label_mapping()
    logger.debug(f"Label mapping created: 0-{len(label_mapping)-1} -> {STANDARD_LABELS[:3]}...")
    
    # Process each file
    file_results = []
    total_stats = {
        'files_processed': 0,
        'files_successful': 0,
        'files_failed': 0,
        'total_original_rows': 0,
        'total_final_rows': 0,
        'total_predictions_decoded': 0,
        'total_annotator1_filled': 0,
        'total_annotator2_filled': 0,
        'total_duplicates_removed': 0,
        'failed_files': []
    }
    
    for file_path in xlsx_files:
        logger.info(f"Processing {file_path.name}...")
        
        result = update_annotation_file(file_path, label_mapping, backup)
        file_results.append(result)
        total_stats['files_processed'] += 1
        
        if result['success']:
            total_stats['files_successful'] += 1
            total_stats['total_original_rows'] += result['original_rows']
            total_stats['total_final_rows'] += result['final_rows']
            total_stats['total_predictions_decoded'] += result['predictions_decoded']
            total_stats['total_annotator1_filled'] += result['annotator1_filled']
            total_stats['total_annotator2_filled'] += result['annotator2_filled']
            total_stats['total_duplicates_removed'] += result['duplicates_removed']
        else:
            total_stats['files_failed'] += 1
            total_stats['failed_files'].append(result['file'])
    
    # Generate summary
    logger.info("\n" + "="*50)
    logger.info("UPDATE SUMMARY")
    logger.info("="*50)
    logger.info(f"Files processed: {total_stats['files_processed']}")
    logger.info(f"Files successful: {total_stats['files_successful']}")
    logger.info(f"Files failed: {total_stats['files_failed']}")
    logger.info(f"Total rows (original): {total_stats['total_original_rows']:,}")
    logger.info(f"Total rows (final): {total_stats['total_final_rows']:,}")
    logger.info(f"Total predictions decoded: {total_stats['total_predictions_decoded']:,}")
    logger.info(f"Total annotator1 filled: {total_stats['total_annotator1_filled']:,}")
    logger.info(f"Total annotator2 filled: {total_stats['total_annotator2_filled']:,}")
    logger.info(f"Total duplicates removed: {total_stats['total_duplicates_removed']:,}")
    
    if total_stats['failed_files']:
        logger.warning(f"Failed files: {', '.join(total_stats['failed_files'])}")
    
    return {
        'summary': total_stats,
        'file_details': file_results
    }


def generate_update_report(results: Dict, output_path: Union[str, Path]) -> None:
    """
    Generate a detailed update report.
    
    Args:
        results: Results from update_annotation_directory
        output_path: Path to save the report
    """
    if not results:
        logger.error("No results to report")
        return
    
    summary = results.get('summary', {})
    file_details = results.get('file_details', [])
    
    report = f"""# Annotation Update Report

## Summary Statistics
- **Files Processed**: {summary.get('files_processed', 0)}
- **Files Successful**: {summary.get('files_successful', 0)}
- **Files Failed**: {summary.get('files_failed', 0)}
- **Total Original Rows**: {summary.get('total_original_rows', 0):,}
- **Total Final Rows**: {summary.get('total_final_rows', 0):,}
- **Total Predictions Decoded**: {summary.get('total_predictions_decoded', 0):,}
- **Total Annotator1 Filled**: {summary.get('total_annotator1_filled', 0):,}
- **Total Annotator2 Filled**: {summary.get('total_annotator2_filled', 0):,}
- **Total Duplicates Removed**: {summary.get('total_duplicates_removed', 0):,}

## Standard Labels Used
The following {len(STANDARD_LABELS)} standard labels were used for prediction decoding:

```
{', '.join(STANDARD_LABELS[:10])}...
```

## Per-File Details

| File | Status | Original Rows | Final Rows | Predictions Decoded | Ann1 Filled | Ann2 Filled | Duplicates Removed | Error |
|------|--------|---------------|------------|-------------------|-------------|-------------|-------------------|-------|
"""
    
    for result in file_details:
        status = "✓ Success" if result['success'] else "✗ Failed"
        error = result.get('error', '') or '-'
        report += f"| {result['file']} | {status} | {result['original_rows']:,} | {result['final_rows']:,} | {result['predictions_decoded']:,} | {result['annotator1_filled']:,} | {result['annotator2_filled']:,} | {result['duplicates_removed']:,} | {error} |\n"
    
    if summary.get('failed_files'):
        report += f"\n## Failed Files\n"
        for failed_file in summary['failed_files']:
            report += f"- {failed_file}\n"
    
    # Save report
    try:
        with open(output_path, 'w') as f:
            f.write(report)
        logger.info(f"Update report saved to: {output_path}")
    except Exception as e:
        logger.error(f"Error saving report: {str(e)}")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Update annotation files with top-k predictions and fill annotator columns"
    )
    parser.add_argument(
        "annotation_dir",
        help="Directory containing .xlsx annotation files"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup files (not recommended)"
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory for update reports (default: reports)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output to warnings and errors only"
    )
    
    return parser.parse_args()


def main() -> None:
    """Main entry point for the update script."""
    args = parse_arguments()
    
    # Set logging level
    if args.verbose and args.quiet:
        logger.warning("Both --verbose and --quiet specified; using --verbose")
        logger.setLevel(logging.DEBUG)
    elif args.verbose:
        logger.setLevel(logging.DEBUG)
    elif args.quiet:
        logger.setLevel(logging.WARNING)
    
    # Validate annotation directory
    annotation_path = Path(args.annotation_dir)
    if not annotation_path.exists():
        logger.error(f"Annotation directory not found: {args.annotation_dir}")
        sys.exit(1)
    
    # Create output directory for reports
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run update
    logger.info(f"Starting annotation update for: {args.annotation_dir}")
    
    results = update_annotation_directory(
        args.annotation_dir,
        backup=not args.no_backup
    )
    
    if not results:
        logger.error("Update failed - no results generated")
        sys.exit(1)
    
    # Generate report
    report_path = output_dir / "annotation_update_report.md"
    generate_update_report(results, report_path)
    
    # Print final summary
    summary = results.get('summary', {})
    print(f"\n=== Annotation Update Complete ===")
    print(f"Files processed: {summary.get('files_processed', 0)}")
    print(f"Files successful: {summary.get('files_successful', 0)}")
    print(f"Predictions decoded: {summary.get('total_predictions_decoded', 0):,}")
    print(f"Annotator1 filled: {summary.get('total_annotator1_filled', 0):,}")
    print(f"Annotator2 filled: {summary.get('total_annotator2_filled', 0):,}")
    print(f"Update report: {report_path}")


if __name__ == "__main__":
    main()