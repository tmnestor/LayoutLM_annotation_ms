#!/usr/bin/env python3
"""
Script to update the annotation status in the master CSV file.

This script allows updating the completion status of specific assignments in the master
annotation tracking file. It can be used to:
1. Mark assignments as completed for specific annotators
2. Update annotations for specific cases or images
3. Batch update multiple entries from a CSV file

The script preserves all Excel HYPERLINK formulas and other data in the master file.
"""

import argparse
import csv
import os
import sys
from typing import Dict, List, Optional, Set, Tuple


def load_master_file(master_file: str) -> Tuple[List[Dict[str, str]], List[str]]:
    """
    Load the master CSV file into memory.
    
    Args:
        master_file: Path to the master CSV file
        
    Returns:
        Tuple of (rows, fieldnames) where rows is a list of dictionaries and 
        fieldnames is the list of column names
    """
    if not os.path.exists(master_file):
        print(f"Error: Master file not found: {master_file}")
        sys.exit(1)
        
    rows = []
    fieldnames = []
    
    with open(master_file, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
            
    return rows, fieldnames


def save_master_file(master_file: str, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    """
    Save the updated master CSV file.
    
    Args:
        master_file: Path to the master CSV file
        rows: List of row dictionaries to write
        fieldnames: List of column names
    """
    # Create a backup of the original file
    if os.path.exists(master_file):
        backup_file = f"{master_file}.bak"
        try:
            with open(master_file, 'r', newline='') as src:
                with open(backup_file, 'w', newline='') as dst:
                    dst.write(src.read())
            print(f"Created backup: {backup_file}")
        except Exception as e:
            print(f"Warning: Failed to create backup: {e}")
    
    # Write the updated file
    with open(master_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def update_from_file(master_file: str, update_file: str) -> None:
    """
    Update the master file using a CSV file with update information.
    
    The update file should have columns:
    - case_id: Case identifier
    - image_id: Image identifier
    - annotator: Annotator name (optional, will match both annotators if not specified)
    - status: New status value (yes/no)
    
    Args:
        master_file: Path to the master CSV file
        update_file: Path to the update CSV file
    """
    if not os.path.exists(update_file):
        print(f"Error: Update file not found: {update_file}")
        sys.exit(1)
        
    # Load the update file
    updates = []
    with open(update_file, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Validate required fields
            if 'case_id' not in row or 'image_id' not in row or 'status' not in row:
                print("Error: Update file must contain case_id, image_id, and status columns")
                sys.exit(1)
                
            updates.append(row)
    
    # Load the master file
    master_rows, fieldnames = load_master_file(master_file)
    
    # Track which updates were applied
    applied_updates = 0
    
    # Apply updates
    for update in updates:
        case_id = update['case_id']
        image_id = update['image_id']
        annotator = update.get('annotator', None)  # Optional
        status = update['status'].lower()
        
        # Validate status
        if status not in ['yes', 'no']:
            print(f"Warning: Invalid status '{status}' for {case_id}/{image_id}, must be 'yes' or 'no'. Skipping.")
            continue
        
        # Find matching rows
        for row in master_rows:
            if row['case_id'] == case_id and row['image_id'] == image_id:
                if annotator is None or annotator == row['assignee1']:
                    row['has_assignee1_completed'] = status
                    applied_updates += 1
                    
                if annotator is None or annotator == row['assignee2']:
                    row['has_assignee2_completed'] = status
                    applied_updates += 1
    
    # Save the updated master file
    save_master_file(master_file, master_rows, fieldnames)
    print(f"Applied {applied_updates} updates to {master_file}")


def update_specific_entries(
    master_file: str, 
    case_ids: Optional[List[str]] = None,
    image_ids: Optional[List[str]] = None,
    annotators: Optional[List[str]] = None,
    status: str = "yes"
) -> None:
    """
    Update specific entries in the master file.
    
    Args:
        master_file: Path to the master CSV file
        case_ids: List of case IDs to update (optional)
        image_ids: List of image IDs to update (optional)
        annotators: List of annotator names to update (optional)
        status: New status value (yes/no)
    """
    # Validate status
    status = status.lower()
    if status not in ['yes', 'no']:
        print(f"Error: Invalid status '{status}', must be 'yes' or 'no'")
        sys.exit(1)
        
    # Load the master file
    master_rows, fieldnames = load_master_file(master_file)
    
    # Convert input lists to sets for faster lookups
    case_id_set = set(case_ids) if case_ids else None
    image_id_set = set(image_ids) if image_ids else None
    annotator_set = set(annotators) if annotators else None
    
    # Track which updates were applied
    updated_count = 0
    
    # Apply updates
    for row in master_rows:
        # Check if this row should be updated
        case_match = case_id_set is None or row['case_id'] in case_id_set
        image_match = image_id_set is None or row['image_id'] in image_id_set
        
        if case_match and image_match:
            # Update assignee1 if needed
            if annotator_set is None or row['assignee1'] in annotator_set:
                row['has_assignee1_completed'] = status
                updated_count += 1
                
            # Update assignee2 if needed
            if annotator_set is None or row['assignee2'] in annotator_set:
                row['has_assignee2_completed'] = status
                updated_count += 1
    
    # Save the updated master file
    save_master_file(master_file, master_rows, fieldnames)
    print(f"Updated {updated_count} entries in {master_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update annotation completion status in the master CSV file"
    )
    parser.add_argument(
        "--master-file",
        default=os.path.expanduser("~/Desktop/annotation_master.csv"),
        help="Path to the master CSV file (default: ~/Desktop/annotation_master.csv)",
    )
    
    # Create subparsers for different update methods
    subparsers = parser.add_subparsers(dest="command", help="Update method")
    
    # Subparser for updating from a file
    file_parser = subparsers.add_parser("from-file", help="Update from a CSV file")
    file_parser.add_argument(
        "update_file",
        help="Path to a CSV file with update information",
    )
    
    # Subparser for updating specific entries
    specific_parser = subparsers.add_parser("specific", help="Update specific entries")
    specific_parser.add_argument(
        "--case-ids",
        nargs="+",
        help="List of case IDs to update",
    )
    specific_parser.add_argument(
        "--image-ids",
        nargs="+",
        help="List of image IDs to update",
    )
    specific_parser.add_argument(
        "--annotators",
        nargs="+",
        help="List of annotator names to update",
    )
    specific_parser.add_argument(
        "--status",
        default="yes",
        choices=["yes", "no"],
        help="New completion status (default: yes)",
    )
    
    args = parser.parse_args()
    
    # Default to "specific" if no command is provided
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Process command
    if args.command == "from-file":
        update_from_file(args.master_file, args.update_file)
    elif args.command == "specific":
        if not any([args.case_ids, args.image_ids, args.annotators]):
            print("Error: At least one of --case-ids, --image-ids, or --annotators must be specified")
            sys.exit(1)
            
        update_specific_entries(
            args.master_file,
            args.case_ids,
            args.image_ids,
            args.annotators,
            args.status
        )


if __name__ == "__main__":
    main()