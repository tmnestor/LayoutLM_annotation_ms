#!/usr/bin/env python3
"""
JSON Explorer - Tool for exploring and extracting data from JSON files
"""

import json
import sys
from pprint import pprint


def explore_json(data, path="", max_depth=3, current_depth=0):
    """
    Recursively explore a JSON structure and print its contents with path information.

    Args:
        data: The JSON data structure
        path: Current path in the JSON structure
        max_depth: Maximum recursion depth
        current_depth: Current recursion depth
    """
    if current_depth >= max_depth:
        print(f"{path} ... (max depth reached)")
        return

    if isinstance(data, dict):
        print(f"{path} (dict with {len(data)} keys)")
        for key, value in list(data.items())[:5]:  # Show first 5 keys
            new_path = f"{path}.{key}" if path else key
            explore_json(value, new_path, max_depth, current_depth + 1)
        if len(data) > 5:
            print(f"{path} ... ({len(data) - 5} more keys)")
    elif isinstance(data, list):
        print(f"{path} (list with {len(data)} items)")
        if data and len(data) > 0:
            # Show structure of first item
            explore_json(data[0], f"{path}[0]", max_depth, current_depth + 1)
            if len(data) > 1:
                print(f"{path} ... ({len(data) - 1} more items)")
    else:
        # For primitive values, show type and truncated content
        value_str = str(data)
        if len(value_str) > 50:
            value_str = value_str[:47] + "..."
        print(f"{path} = {type(data).__name__}: {value_str}")


def extract_text_values(data):
    """
    Extract text values from extracted_lines in a JSON structure.

    Args:
        data: The JSON data structure

    Returns:
        List of extracted text values or None if not found
    """
    if "extracted_lines" not in data:
        print("Error: No 'extracted_lines' key found in JSON")
        return None

    extracted_lines = data["extracted_lines"]
    
    if isinstance(extracted_lines, list):
        # Handle list structure
        text_values = []
        for item in extracted_lines:
            if isinstance(item, dict) and "text" in item:
                text_values.append(item["text"])
        
        if not text_values:
            print("Warning: No 'text' fields found in 'extracted_lines' list items")
        
        return text_values
    
    elif isinstance(extracted_lines, dict):
        # Handle dictionary structure
        text_values = []
        for key, item in extracted_lines.items():
            if isinstance(item, dict) and "text" in item:
                text_values.append(item["text"])
        
        if not text_values:
            print("Warning: No 'text' fields found in 'extracted_lines' dictionary values")
        
        return text_values
    
    else:
        print(f"Error: 'extracted_lines' is neither a list nor a dictionary (type: {type(extracted_lines).__name__})")
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python my_json_explorer.py filename.json [--extract-text] [--depth N]")
        sys.exit(1)
    
    filename = sys.argv[1]
    extract_text = "--extract-text" in sys.argv
    max_depth = 3  # Default depth
    
    # Check for depth argument
    if "--depth" in sys.argv:
        depth_index = sys.argv.index("--depth")
        if depth_index + 1 < len(sys.argv):
            try:
                max_depth = int(sys.argv[depth_index + 1])
            except ValueError:
                print(f"Invalid depth value: {sys.argv[depth_index + 1]}")
                sys.exit(1)
    
    try:
        with open(filename, "r") as f:
            data = json.load(f)
        
        print(f"\nExploring JSON file: {filename}")
        print(f"Top level type: {type(data).__name__}")
        
        if isinstance(data, dict):
            print(f"Keys: {', '.join(list(data.keys()))}")
        elif isinstance(data, list):
            print(f"List length: {len(data)}")
        
        print("\nStructure exploration:")
        explore_json(data, max_depth=max_depth)
        
        if extract_text:
            print("\nExtracting text values from 'extracted_lines':")
            text_values = extract_text_values(data)
            if text_values:
                print(f"Found {len(text_values)} text values:")
                for i, text in enumerate(text_values[:10]):
                    print(f"  {i+1}. {text}")
                if len(text_values) > 10:
                    print(f"  ... and {len(text_values) - 10} more")
        
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{filename}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()