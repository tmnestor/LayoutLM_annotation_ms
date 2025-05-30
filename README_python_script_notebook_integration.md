# Python Script and Jupyter Notebook Integration Guide

This guide covers best practices and patterns for integrating Python scripts (.py files) with Jupyter notebooks (.ipynb files).

## Best Practices for Python Script + Notebook Integration

### 1. **Modular Function Design**
- Write scripts with importable functions, not just executable code
- Use `if __name__ == "__main__":` to separate CLI from library functionality
- Design functions to return data rather than just print

### 2. **Import Patterns**
[Detailed below](#import-patterns)

### 3. **Shell Integration**
```python
# Run scripts from notebooks
!python my_script.py --arg value
result = !python my_script.py --output-format json
```

### 4. **Shared Configuration**
- Use config files (JSON/YAML) that both scripts and notebooks can read
- Environment variables for paths and settings
- Consistent logging setup

### 5. **Data Exchange**
- Scripts save intermediate results to files (CSV, JSON, pickle)
- Notebooks read these files for further analysis
- Use standard formats both can handle

### 6. **Development Workflow**
1. Prototype in notebooks
2. Extract stable code to scripts
3. Import script functions back to notebooks
4. Use scripts for production, notebooks for exploration

## Import Patterns for Python Scripts and Notebooks

### 1. **Direct Module Import**
When your script is in the same directory or Python path:
```python
# my_utils.py contains functions
import my_utils
result = my_utils.process_data(data)

# Or import specific functions
from my_utils import process_data, validate_input
result = process_data(data)
```

### 2. **Path Manipulation**
When scripts are in different directories:
```python
import sys
import os

# Add script directory to Python path
sys.path.append('/absolute/path/to/scripts')
sys.path.append('../scripts')  # relative path
sys.path.append(os.path.join(os.getcwd(), 'utils'))

from my_script import my_function
```

### 3. **Package Structure**
Organize as packages with `__init__.py`:
```
project/
├── notebooks/
│   └── analysis.ipynb
├── scripts/
│   ├── __init__.py
│   ├── data_processing.py
│   └── utils.py
```

```python
# In notebook
sys.path.append('..')
from scripts.data_processing import clean_data
from scripts.utils import load_config
```

### 4. **Dynamic Import with importlib**
For more flexible imports:
```python
import importlib.util
import sys

# Load module from file path
spec = importlib.util.spec_from_file_location("my_module", "/path/to/script.py")
my_module = importlib.util.module_from_spec(spec)
sys.modules["my_module"] = my_module
spec.loader.exec_module(my_module)

# Use the module
result = my_module.my_function(data)
```

### 5. **Conditional Imports**
Handle missing dependencies gracefully:
```python
try:
    from scripts.advanced_utils import complex_function
    HAS_ADVANCED = True
except ImportError:
    HAS_ADVANCED = False
    
if HAS_ADVANCED:
    result = complex_function(data)
else:
    # Fallback implementation
    result = simple_process(data)
```

### 6. **Reload Pattern for Development**
When modifying scripts during notebook development:
```python
import importlib
import my_script

# After modifying my_script.py
importlib.reload(my_script)
result = my_script.updated_function(data)
```

### 7. **Environment-Based Imports**
```python
import os

if os.getenv('ENVIRONMENT') == 'development':
    from scripts.dev_utils import debug_function
else:
    from scripts.prod_utils import optimized_function
```

## Common Gotchas

- **Relative imports**: Use absolute paths when possible
- **Module caching**: Python caches imports; use `importlib.reload()` during development
- **Circular imports**: Avoid scripts importing each other
- **Path persistence**: `sys.path` changes persist throughout notebook session

## Recommended Project Structure

```
project/
├── README.md
├── requirements.txt
├── notebooks/
│   ├── exploration.ipynb
│   ├── analysis.ipynb
│   └── visualization.ipynb
├── scripts/
│   ├── __init__.py
│   ├── data_processing.py
│   ├── utils.py
│   └── main.py
├── config/
│   ├── settings.json
│   └── logging.conf
└── data/
    ├── raw/
    ├── processed/
    └── output/
```

## Example Integration

### Script (scripts/data_processor.py)
```python
import pandas as pd
from pathlib import Path

def load_data(file_path):
    """Load data from CSV file."""
    return pd.read_csv(file_path)

def clean_data(df):
    """Clean the dataframe."""
    return df.dropna()

def save_results(df, output_path):
    """Save processed data."""
    df.to_csv(output_path, index=False)

def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    
    df = load_data(args.input)
    cleaned_df = clean_data(df)
    save_results(cleaned_df, args.output)

if __name__ == "__main__":
    main()
```

### Notebook Usage
```python
# Cell 1: Setup
import sys
sys.path.append('../scripts')
from data_processor import load_data, clean_data

# Cell 2: Interactive processing
df = load_data('../data/raw/dataset.csv')
print(f"Original shape: {df.shape}")

cleaned_df = clean_data(df)
print(f"Cleaned shape: {cleaned_df.shape}")

# Cell 3: Analysis
cleaned_df.describe()

# Cell 4: Run full script
!python ../scripts/data_processor.py --input ../data/raw/dataset.csv --output ../data/processed/clean_dataset.csv
```

This approach maximizes code reuse while keeping the strengths of each format - scripts for automation and production, notebooks for exploration and interactive analysis.