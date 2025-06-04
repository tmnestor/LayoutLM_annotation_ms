#!/usr/bin/env python3
"""
Check final status of updated annotation files.
"""

import pandas as pd
import os

def check_final_status():
    # Check only non-backup files
    annotation_dir = 'annotation_labels'
    files = [f for f in os.listdir(annotation_dir) if f.endswith('.xlsx') and 'backup' not in f]

    print('=== UPDATED ANNOTATION FILES STATUS ===')
    total_files = 0
    total_rows = 0
    total_ann1_completed = 0
    total_ann2_completed = 0

    for file in files:
        try:
            df = pd.read_excel(f'{annotation_dir}/{file}', sheet_name='Annotation')
            file_rows = len(df)
            
            # Check annotator1
            ann1_completed = 0
            if 'annotator1_label' in df.columns:
                ann1_mask = (~df['annotator1_label'].isna()) & (df['annotator1_label'] != '')
                ann1_completed = ann1_mask.sum()
            
            # Check annotator2  
            ann2_completed = 0
            if 'annotator2_label' in df.columns:
                ann2_mask = (~df['annotator2_label'].isna()) & (df['annotator2_label'] != '')
                ann2_completed = ann2_mask.sum()
            
            print(f'{file}:')
            print(f'  Total rows: {file_rows}')
            print(f'  Annotator1: {ann1_completed}/{file_rows} ({ann1_completed/file_rows*100:.1f}%)')
            print(f'  Annotator2: {ann2_completed}/{file_rows} ({ann2_completed/file_rows*100:.1f}%)')
            print()
            
            # Sample labels from first file
            if total_files == 0 and ann1_completed > 0:
                print('Sample labels from first file:')
                sample_labels = df['annotator1_label'].head(5).tolist()
                sample_preds = df['pred'].head(5).tolist()
                print(f'  Predictions: {sample_preds}')
                print(f'  Decoded labels: {sample_labels}')
                print()
            
            # Accumulate totals
            total_files += 1
            total_rows += file_rows
            total_ann1_completed += ann1_completed
            total_ann2_completed += ann2_completed
            
        except Exception as e:
            print(f'{file}: Error - {e}')
            print()

    print('=== FINAL SUMMARY ===')
    print(f'Total files: {total_files}')
    print(f'Total rows: {total_rows}')
    print(f'Annotator1 completed: {total_ann1_completed}/{total_rows} ({total_ann1_completed/total_rows*100:.1f}%)')
    print(f'Annotator2 completed: {total_ann2_completed}/{total_rows} ({total_ann2_completed/total_rows*100:.1f}%)')

if __name__ == "__main__":
    check_final_status()