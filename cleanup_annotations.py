#!/usr/bin/env python3
"""
Annotation Cleanup Script for LayoutLM Annotation Files

This script post-processes annotation files to:
1. Remove duplicate rows based on key columns
2. Standardize annotator selection across all files
3. Clean up data inconsistencies
4. Backup original files before modification

Usage:
    python cleanup_annotations.py annotation_labels --annotator annotator1 --deduplicate
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger('cleanup_annotations')


def backup_file(file_path: Union[str, Path], backup_suffix: str = "_backup") -> Path:
    """
    Create a backup copy of the original file.
    
    Args:
        file_path: Path to the file to backup
        backup_suffix: Suffix to add to backup filename
        
    Returns:
        Path to the backup file
    """
    original_path = Path(file_path)
    backup_path = original_path.parent / f"{original_path.stem}{backup_suffix}{original_path.suffix}"
    
    # Create backup
    shutil.copy2(original_path, backup_path)
    logger.info(f"Created backup: {backup_path.name}")
    
    return backup_path


def deduplicate_rows(df: pd.DataFrame, key_columns: List[str] = None) -> Tuple[pd.DataFrame, int]:
    """
    Remove duplicate rows based on key columns.
    
    Args:
        df: DataFrame to deduplicate
        key_columns: Columns to use for duplicate detection. If None, uses all columns.
        
    Returns:
        Tuple of (deduplicated_df, num_duplicates_removed)
    """
    if key_columns is None:
        # Use all columns except annotation columns for deduplication
        key_columns = [col for col in df.columns 
                      if not col.endswith('_label') and col not in ['annotator1_labels', 'annotator2_labels']]
    
    # Filter to only existing columns
    existing_key_columns = [col for col in key_columns if col in df.columns]
    
    if not existing_key_columns:
        logger.warning("No valid key columns found for deduplication")
        return df, 0
    
    original_count = len(df)
    
    # Remove duplicates, keeping first occurrence
    df_deduplicated = df.drop_duplicates(subset=existing_key_columns, keep='first')
    
    duplicates_removed = original_count - len(df_deduplicated)
    
    if duplicates_removed > 0:
        logger.info(f"Removed {duplicates_removed} duplicate rows based on: {existing_key_columns}")
    
    return df_deduplicated, duplicates_removed


def standardize_annotator_labels(df: pd.DataFrame, target_annotator: str) -> pd.DataFrame:
    """
    Standardize annotation labels to use a specific annotator.
    
    Args:
        df: DataFrame with annotation data
        target_annotator: Which annotator to use ('annotator1' or 'annotator2')
        
    Returns:
        DataFrame with standardized annotator labels
    """
    if target_annotator not in ['annotator1', 'annotator2']:
        raise ValueError(f"Invalid target_annotator: {target_annotator}. Must be 'annotator1' or 'annotator2'")
    
    target_col = f"{target_annotator}_label"
    other_annotator = "annotator2" if target_annotator == "annotator1" else "annotator1"
    other_col = f"{other_annotator}_label"
    
    # Create a copy to avoid modifying original
    df_clean = df.copy()
    
    changes_made = 0
    
    # If target column doesn't exist but other does, copy it over
    if target_col not in df_clean.columns and other_col in df_clean.columns:
        df_clean[target_col] = df_clean[other_col]
        logger.info(f"Copied {other_col} to {target_col}")
        changes_made += len(df_clean)
    
    # Fill missing values in target column with values from other annotator
    elif target_col in df_clean.columns and other_col in df_clean.columns:
        missing_mask = df_clean[target_col].isna() | (df_clean[target_col] == '') | (df_clean[target_col] == 'nan')
        available_mask = df_clean[other_col].notna() & (df_clean[other_col] != '') & (df_clean[other_col] != 'nan')
        
        fill_mask = missing_mask & available_mask
        
        if fill_mask.any():
            df_clean.loc[fill_mask, target_col] = df_clean.loc[fill_mask, other_col]
            changes_made = fill_mask.sum()
            logger.info(f"Filled {changes_made} missing {target_col} values from {other_col}")
    
    # Ensure the target annotator column exists
    if target_col not in df_clean.columns:
        logger.warning(f"Target column {target_col} not found in data")
        df_clean[target_col] = ''
    
    return df_clean


def clean_annotation_file(file_path: Union[str, Path], 
                         target_annotator: str = "annotator1",
                         deduplicate: bool = True,
                         backup: bool = True) -> Dict:
    """
    Clean a single annotation file.
    
    Args:
        file_path: Path to the annotation file
        target_annotator: Which annotator to standardize to
        deduplicate: Whether to remove duplicate rows
        backup: Whether to create backup before modifying
        
    Returns:
        Dictionary with cleanup statistics
    """
    file_path = Path(file_path)
    
    try:
        # Read the annotation file
        df = pd.read_excel(file_path, sheet_name='Annotation')
        original_rows = len(df)
        
        stats = {
            'file': file_path.name,
            'original_rows': original_rows,
            'duplicates_removed': 0,
            'labels_standardized': 0,
            'final_rows': original_rows,
            'success': False,
            'error': None
        }
        
        # Create backup if requested
        if backup:
            backup_file(file_path)
        
        # Deduplicate rows
        if deduplicate:
            df, duplicates_removed = deduplicate_rows(df)
            stats['duplicates_removed'] = duplicates_removed
        
        # Standardize annotator labels
        df_clean = standardize_annotator_labels(df, target_annotator)
        
        stats['final_rows'] = len(df_clean)
        
        # Write back to file
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_clean.to_excel(writer, sheet_name='Annotation', index=False)
        
        stats['success'] = True
        logger.info(f"Successfully cleaned {file_path.name}")
        
        return stats
        
    except Exception as e:
        error_msg = f"Error processing {file_path.name}: {str(e)}"
        logger.error(error_msg)
        return {
            'file': file_path.name,
            'original_rows': 0,
            'duplicates_removed': 0,
            'labels_standardized': 0,
            'final_rows': 0,
            'success': False,
            'error': error_msg
        }


def cleanup_annotation_directory(annotation_dir: Union[str, Path],
                                target_annotator: str = "annotator1",
                                deduplicate: bool = True,
                                backup: bool = True) -> Dict:
    """
    Clean all annotation files in a directory.
    
    Args:
        annotation_dir: Directory containing annotation files
        target_annotator: Which annotator to standardize to
        deduplicate: Whether to remove duplicate rows
        backup: Whether to create backups before modifying
        
    Returns:
        Dictionary with overall cleanup statistics
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
    
    logger.info(f"Found {len(xlsx_files)} annotation files to process")
    logger.info(f"Target annotator: {target_annotator}")
    logger.info(f"Deduplication: {'enabled' if deduplicate else 'disabled'}")
    logger.info(f"Backup: {'enabled' if backup else 'disabled'}")
    
    # Process each file
    file_results = []
    total_stats = {
        'files_processed': 0,
        'files_successful': 0,
        'files_failed': 0,
        'total_original_rows': 0,
        'total_final_rows': 0,
        'total_duplicates_removed': 0,
        'failed_files': []
    }
    
    for file_path in xlsx_files:
        logger.info(f"Processing {file_path.name}...")
        
        result = clean_annotation_file(
            file_path, 
            target_annotator=target_annotator,
            deduplicate=deduplicate,
            backup=backup
        )
        
        file_results.append(result)
        total_stats['files_processed'] += 1
        
        if result['success']:
            total_stats['files_successful'] += 1
            total_stats['total_original_rows'] += result['original_rows']
            total_stats['total_final_rows'] += result['final_rows']
            total_stats['total_duplicates_removed'] += result['duplicates_removed']
        else:
            total_stats['files_failed'] += 1
            total_stats['failed_files'].append(result['file'])
    
    # Generate summary
    logger.info("\n" + "="*50)
    logger.info("CLEANUP SUMMARY")
    logger.info("="*50)
    logger.info(f"Files processed: {total_stats['files_processed']}")
    logger.info(f"Files successful: {total_stats['files_successful']}")
    logger.info(f"Files failed: {total_stats['files_failed']}")
    logger.info(f"Total rows (original): {total_stats['total_original_rows']:,}")
    logger.info(f"Total rows (final): {total_stats['total_final_rows']:,}")
    logger.info(f"Total duplicates removed: {total_stats['total_duplicates_removed']:,}")
    
    if total_stats['failed_files']:
        logger.warning(f"Failed files: {', '.join(total_stats['failed_files'])}")
    
    return {
        'summary': total_stats,
        'file_details': file_results
    }


def generate_cleanup_report(results: Dict, output_path: Union[str, Path]) -> None:
    """
    Generate a detailed cleanup report.
    
    Args:
        results: Results from cleanup_annotation_directory
        output_path: Path to save the report
    """
    if not results:
        logger.error("No results to report")
        return
    
    summary = results.get('summary', {})
    file_details = results.get('file_details', [])
    
    report = f"""# Annotation Cleanup Report

## Summary Statistics
- **Files Processed**: {summary.get('files_processed', 0)}
- **Files Successful**: {summary.get('files_successful', 0)}
- **Files Failed**: {summary.get('files_failed', 0)}
- **Total Original Rows**: {summary.get('total_original_rows', 0):,}
- **Total Final Rows**: {summary.get('total_final_rows', 0):,}
- **Total Duplicates Removed**: {summary.get('total_duplicates_removed', 0):,}

## Per-File Details

| File | Status | Original Rows | Final Rows | Duplicates Removed | Error |
|------|--------|---------------|------------|-------------------|-------|
"""
    
    for result in file_details:
        status = "✓ Success" if result['success'] else "✗ Failed"
        error = result.get('error', '') or '-'
        report += f"| {result['file']} | {status} | {result['original_rows']:,} | {result['final_rows']:,} | {result['duplicates_removed']:,} | {error} |\n"
    
    if summary.get('failed_files'):
        report += f"\n## Failed Files\n"
        for failed_file in summary['failed_files']:
            report += f"- {failed_file}\n"
    
    # Save report
    try:
        with open(output_path, 'w') as f:
            f.write(report)
        logger.info(f"Cleanup report saved to: {output_path}")
    except Exception as e:
        logger.error(f"Error saving report: {str(e)}")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Clean up annotation files by removing duplicates and standardizing annotator selection"
    )
    parser.add_argument(
        "annotation_dir",
        help="Directory containing .xlsx annotation files"
    )
    parser.add_argument(
        "--annotator",
        choices=["annotator1", "annotator2"],
        default="annotator1",
        help="Which annotator to standardize to (default: annotator1)"
    )
    parser.add_argument(
        "--deduplicate",
        action="store_true",
        help="Remove duplicate rows based on key columns"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup files (not recommended)"
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory for cleanup reports (default: reports)"
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
    """Main entry point for the cleanup script."""
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
    
    # Run cleanup
    logger.info(f"Starting annotation cleanup for: {args.annotation_dir}")
    
    results = cleanup_annotation_directory(
        args.annotation_dir,
        target_annotator=args.annotator,
        deduplicate=args.deduplicate,
        backup=not args.no_backup
    )
    
    if not results:
        logger.error("Cleanup failed - no results generated")
        sys.exit(1)
    
    # Generate report
    report_path = output_dir / f"cleanup_report_{args.annotator}.md"
    generate_cleanup_report(results, report_path)
    
    # Print final summary
    summary = results.get('summary', {})
    print(f"\n=== Annotation Cleanup Complete ===")
    print(f"Target annotator: {args.annotator}")
    print(f"Files processed: {summary.get('files_processed', 0)}")
    print(f"Files successful: {summary.get('files_successful', 0)}")
    print(f"Total duplicates removed: {summary.get('total_duplicates_removed', 0):,}")
    print(f"Cleanup report: {report_path}")


if __name__ == "__main__":
    main()