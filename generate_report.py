#!/usr/bin/env python3
"""
Script to generate reports from the annotation master file.

This script analyzes the master CSV file and generates reports including:
1. Annotation progress by case
2. Annotator productivity
3. Disagreement analysis between annotators
4. Overall completion statistics
"""

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Tuple


def load_master_file(master_file: str) -> List[Dict[str, str]]:
    """
    Load the master CSV file into memory.
    
    Args:
        master_file: Path to the master CSV file
        
    Returns:
        List of row dictionaries from the master file
    """
    if not os.path.exists(master_file):
        print(f"Error: Master file not found: {master_file}")
        sys.exit(1)
        
    rows = []
    with open(master_file, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append(row)
            
    return rows


def generate_progress_report(rows: List[Dict[str, str]], output_file: str) -> None:
    """
    Generate a report on annotation progress by case.
    
    Args:
        rows: List of row dictionaries from the master file
        output_file: Path to the output report file
    """
    # Initialize counters
    cases = defaultdict(lambda: {'total': 0, 'completed1': 0, 'completed2': 0, 'completed_both': 0})
    
    # Collect statistics
    for row in rows:
        case_id = row['case_id']
        cases[case_id]['total'] += 1
        
        if row['has_assignee1_completed'].lower() == 'yes':
            cases[case_id]['completed1'] += 1
            
        if row['has_assignee2_completed'].lower() == 'yes':
            cases[case_id]['completed2'] += 1
            
        if (row['has_assignee1_completed'].lower() == 'yes' and 
            row['has_assignee2_completed'].lower() == 'yes'):
            cases[case_id]['completed_both'] += 1
    
    # Generate the report
    with open(output_file, 'w') as f:
        f.write("# Annotation Progress Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Overall Statistics\n")
        total_images = sum(case['total'] for case in cases.values())
        total_completed1 = sum(case['completed1'] for case in cases.values())
        total_completed2 = sum(case['completed2'] for case in cases.values())
        total_completed_both = sum(case['completed_both'] for case in cases.values())
        
        f.write(f"- Total images: {total_images}\n")
        f.write(f"- Annotator 1 completion: {total_completed1}/{total_images} ({total_completed1/total_images*100:.1f}%)\n")
        f.write(f"- Annotator 2 completion: {total_completed2}/{total_images} ({total_completed2/total_images*100:.1f}%)\n")
        f.write(f"- Both annotators completion: {total_completed_both}/{total_images} ({total_completed_both/total_images*100:.1f}%)\n\n")
        
        f.write("## Progress by Case\n")
        f.write("| Case ID | Total Images | Annotator 1 | Annotator 2 | Both Complete |\n")
        f.write("|---------|--------------|-------------|-------------|---------------|\n")
        
        for case_id, stats in sorted(cases.items()):
            f.write(f"| {case_id} | {stats['total']} | {stats['completed1']}/{stats['total']} "
                   f"({stats['completed1']/stats['total']*100:.1f}%) | {stats['completed2']}/{stats['total']} "
                   f"({stats['completed2']/stats['total']*100:.1f}%) | {stats['completed_both']}/{stats['total']} "
                   f"({stats['completed_both']/stats['total']*100:.1f}%) |\n")
    
    print(f"Generated progress report: {output_file}")


def generate_annotator_report(rows: List[Dict[str, str]], output_file: str) -> None:
    """
    Generate a report on annotator productivity.
    
    Args:
        rows: List of row dictionaries from the master file
        output_file: Path to the output report file
    """
    # Collect all unique annotators
    annotators = set()
    for row in rows:
        annotators.add(row['assignee1'])
        annotators.add(row['assignee2'])
    
    # Initialize counters
    stats = {annotator: {'assigned': 0, 'completed': 0} for annotator in annotators}
    
    # Collect statistics
    for row in rows:
        # First annotator
        annotator = row['assignee1']
        stats[annotator]['assigned'] += 1
        if row['has_assignee1_completed'].lower() == 'yes':
            stats[annotator]['completed'] += 1
        
        # Second annotator
        annotator = row['assignee2']
        stats[annotator]['assigned'] += 1
        if row['has_assignee2_completed'].lower() == 'yes':
            stats[annotator]['completed'] += 1
    
    # Generate the report
    with open(output_file, 'w') as f:
        f.write("# Annotator Productivity Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Annotator Statistics\n")
        f.write("| Annotator | Assigned | Completed | Completion Rate |\n")
        f.write("|-----------|----------|-----------|----------------|\n")
        
        for annotator, data in sorted(stats.items()):
            if data['assigned'] > 0:
                completion_rate = data['completed'] / data['assigned'] * 100
                f.write(f"| {annotator} | {data['assigned']} | {data['completed']} | {completion_rate:.1f}% |\n")
    
    print(f"Generated annotator report: {output_file}")


def generate_all_reports(master_file: str, output_dir: str) -> None:
    """
    Generate all available reports.
    
    Args:
        master_file: Path to the master CSV file
        output_dir: Directory where reports will be saved
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load the master file
    rows = load_master_file(master_file)
    
    # Generate reports
    generate_progress_report(rows, os.path.join(output_dir, "progress_report.md"))
    generate_annotator_report(rows, os.path.join(output_dir, "annotator_report.md"))
    
    print(f"All reports generated in: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate reports from the annotation master file"
    )
    parser.add_argument(
        "--master-file",
        default=os.path.expanduser("~/Desktop/annotation_master.csv"),
        help="Path to the master CSV file (default: ~/Desktop/annotation_master.csv)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.expanduser("~/Desktop/annotation_reports"),
        help="Directory where reports will be saved (default: ~/Desktop/annotation_reports)",
    )
    parser.add_argument(
        "--report-type",
        choices=["all", "progress", "annotator"],
        default="all",
        help="Type of report to generate (default: all)",
    )
    
    args = parser.parse_args()
    
    # Verify that the master file exists
    if not os.path.exists(args.master_file):
        print(f"Error: Master file not found: {args.master_file}")
        sys.exit(1)
    
    # Create the output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load the master file
    rows = load_master_file(args.master_file)
    
    # Generate the requested report(s)
    if args.report_type == "all" or args.report_type == "progress":
        generate_progress_report(rows, os.path.join(args.output_dir, "progress_report.md"))
        
    if args.report_type == "all" or args.report_type == "annotator":
        generate_annotator_report(rows, os.path.join(args.output_dir, "annotator_report.md"))
    

if __name__ == "__main__":
    main()