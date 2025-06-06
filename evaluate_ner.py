#!/usr/bin/env python3
"""
NER Evaluation Script for LayoutLM Model

This script evaluates Named Entity Recognition (NER) performance using annotation files
generated by prepare_annotations.py as ground truth labels.

Focuses specifically on:
- Entity-level classification metrics
- Token-level accuracy  
- NER sequence evaluation with proper BIO tag handling
- Error pattern analysis
- Inter-annotator agreement
- Comprehensive reporting

Key features:
- Configurable annotator selection (annotator1 or annotator2 as ground truth)
- Support for comparing predictions against either annotator's labels
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional, Union

import pandas as pd
from sklearn.metrics import classification_report, cohen_kappa_score

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger('evaluate_ner')


# ============================================================================
# Label Mapping and Decoding Functions
# ============================================================================

def extract_label_vocabulary(annotation_dir: Union[str, Path]) -> Dict[int, str]:
    """
    Extract the label vocabulary from validation sheet in annotation files.
    
    Args:
        annotation_dir: Directory containing annotation files
        
    Returns:
        Dictionary mapping label indices to label names
    """
    annotation_path = Path(annotation_dir)
    annotation_files = list(annotation_path.glob("*.xlsx"))
    
    if not annotation_files:
        logger.warning("No annotation files found for vocabulary extraction")
        return {}
    
    # Try to extract vocabulary from first available file's Validation sheet
    for file_path in annotation_files:
        try:
            validation_df = pd.read_excel(file_path, sheet_name='Validation')
            
            if 'Label Options' in validation_df.columns:
                # Extract labels from Validation sheet
                labels = validation_df['Label Options'].dropna().tolist()
                # Create mapping: index -> label
                label_mapping = {i: label for i, label in enumerate(labels)}
                
                logger.info(f"Extracted {len(labels)} labels from validation vocabulary")
                logger.debug(f"Sample labels: {labels[:10]}")
                
                return label_mapping
                
        except Exception as e:
            logger.debug(f"Could not extract vocabulary from {file_path}: {str(e)}")
            continue
    
    logger.warning("Could not extract label vocabulary from annotation files")
    return {}


def decode_predictions(predictions: pd.Series, label_mapping: Dict[int, str]) -> pd.Series:
    """
    Decode numeric predictions to text labels using label mapping.
    
    Args:
        predictions: Series with numeric prediction values
        label_mapping: Dictionary mapping indices to label names
        
    Returns:
        Series with decoded text labels
    """
    def decode_single_prediction(pred_value):
        try:
            # Handle various numeric types
            if pd.isna(pred_value):
                return "UNK"
            
            pred_int = int(pred_value)
            return label_mapping.get(pred_int, f"UNK_{pred_int}")
            
        except (ValueError, TypeError):
            # If already a string or can't convert, return as-is
            return str(pred_value)
    
    return predictions.apply(decode_single_prediction)


def strip_bio_prefixes(labels: pd.Series) -> pd.Series:
    """
    Strip B- and I- prefixes from BIO-formatted labels to get flat entity types.
    
    Args:
        labels: Series with BIO-formatted labels (B-ADDRESS, I-ADDRESS, O, etc.)
        
    Returns:
        Series with flat labels (ADDRESS, ADDRESS, O, etc.)
    """
    def strip_prefix(label):
        if pd.isna(label) or label == 'nan':
            return 'O'
        
        label_str = str(label).strip()
        
        # Handle BIO prefixes
        if label_str.startswith('B-') or label_str.startswith('I-'):
            return label_str[2:]  # Remove B- or I- prefix
        else:
            return label_str  # Already flat or O tag
    
    return labels.apply(strip_prefix)


def convert_flat_to_bio(flat_labels: pd.Series) -> pd.Series:
    """
    Convert flat entity labels to BIO format based on contiguous sequences.
    
    Contiguous sequences of the same entity type are converted to B-/I- format:
    - First occurrence in sequence: B-ENTITY
    - Subsequent occurrences: I-ENTITY
    - O tags remain O
    
    Args:
        flat_labels: Series with flat entity labels (ADDRESS, ADDRESS, MONEY, O, etc.)
        
    Returns:
        Series with BIO-formatted labels (B-ADDRESS, I-ADDRESS, B-MONEY, O, etc.)
    """
    bio_labels = []
    prev_label = None
    
    for label in flat_labels:
        if pd.isna(label) or label == 'nan':
            label = 'O'
        else:
            label = str(label).strip()
        
        if label == 'O':
            bio_labels.append('O')
        elif label == prev_label:
            # Continuation of the same entity
            bio_labels.append(f"I-{label}")
        else:
            # Start of new entity
            bio_labels.append(f"B-{label}")
        
        prev_label = label
    
    return pd.Series(bio_labels)


# ============================================================================
# Data Loading Functions
# ============================================================================

def load_annotation_file(file_path: Union[str, Path], annotator: str = "annotator1", 
                        label_mapping: Optional[Dict[int, str]] = None) -> pd.DataFrame:
    """
    Load completed annotation file with ground truth labels and decode predictions.
    
    Args:
        file_path: Path to the Excel annotation file
        annotator: Which annotator to use as ground truth ("annotator1" or "annotator2")
        label_mapping: Dictionary mapping prediction indices to label names
        
    Returns:
        DataFrame with columns: words, pred, ground_truth, prob, x1, y1, x2, y2
    """
    try:
        # Load the annotation sheet
        df = pd.read_excel(file_path, sheet_name='Annotation')
        
        # Validate annotator parameter
        if annotator not in ["annotator1", "annotator2"]:
            raise ValueError(f"Invalid annotator: {annotator}. Must be 'annotator1' or 'annotator2'")
        
        # Select ground truth column based on annotator choice
        ground_truth_col = f"{annotator}_label"
        
        if ground_truth_col not in df.columns:
            logger.warning(f"Column {ground_truth_col} not found in {file_path}")
            return pd.DataFrame()
        
        # Use selected annotator as ground truth
        df['ground_truth'] = df[ground_truth_col]
        
        # Decode numeric predictions to text labels if mapping is available
        if label_mapping and 'pred' in df.columns:
            logger.debug(f"Decoding predictions in {Path(file_path).name}")
            df['pred_decoded'] = decode_predictions(df['pred'], label_mapping)
            df['pred'] = df['pred_decoded']  # Replace pred with decoded version
        
        # Convert all label columns to strings to ensure consistent data types
        df['ground_truth'] = df['ground_truth'].astype(str)
        df['pred'] = df['pred'].astype(str)
        
        # Create flat versions for token-level comparison
        # Strip BIO prefixes from predictions for flat comparison
        df['pred_flat'] = strip_bio_prefixes(df['pred'])
        df['ground_truth_flat'] = df['ground_truth']  # Human labels are already flat
        
        # Create BIO versions for entity-level comparison
        # Convert human flat labels to BIO format based on contiguous sequences
        df['ground_truth_bio'] = convert_flat_to_bio(df['ground_truth'])
        df['pred_bio'] = df['pred']  # Model predictions are already in BIO format
        
        # Also keep both annotator columns for inter-annotator agreement analysis
        df['annotator1_labels'] = df.get('annotator1_label', None)
        df['annotator2_labels'] = df.get('annotator2_label', None)
        
        # Convert annotator columns to strings as well
        if 'annotator1_labels' in df.columns:
            df['annotator1_labels'] = df['annotator1_labels'].astype(str)
        if 'annotator2_labels' in df.columns:
            df['annotator2_labels'] = df['annotator2_labels'].astype(str)
        
        # Select relevant columns for NER evaluation
        columns_to_keep = ['words', 'pred', 'ground_truth', 'prob', 
                          'pred_flat', 'ground_truth_flat', 'pred_bio', 'ground_truth_bio',
                          'annotator1_labels', 'annotator2_labels']
        
        # Add spatial coordinates if available
        spatial_cols = ['x1', 'y1', 'x2', 'y2']
        for col in spatial_cols:
            if col in df.columns:
                columns_to_keep.append(col)
        
        # Filter to only include columns that exist
        existing_columns = [col for col in columns_to_keep if col in df.columns]
        
        return df[existing_columns]
        
    except Exception as e:
        logger.error(f"Error loading annotation file {file_path}: {str(e)}")
        return pd.DataFrame()


def load_all_annotation_files(annotation_dir: Union[str, Path], 
                            annotator: str = "annotator1", 
                            label_mapping: Optional[Dict[int, str]] = None) -> Dict[str, pd.DataFrame]:
    """
    Load all annotation files from a directory with prediction decoding.
    
    Args:
        annotation_dir: Directory containing .xlsx annotation files
        annotator: Which annotator to use as ground truth ("annotator1" or "annotator2")
        label_mapping: Dictionary mapping prediction indices to label names
        
    Returns:
        Dictionary mapping filename to DataFrame
    """
    annotation_path = Path(annotation_dir)
    if not annotation_path.exists():
        logger.error(f"Annotation directory not found: {annotation_dir}")
        return {}
    
    annotation_files = list(annotation_path.glob("*.xlsx"))
    if not annotation_files:
        logger.warning(f"No .xlsx files found in {annotation_dir}")
        return {}
    
    logger.info(f"Loading {len(annotation_files)} annotation files using {annotator} as ground truth...")
    if label_mapping:
        logger.info(f"Using label mapping with {len(label_mapping)} labels for prediction decoding")
    
    file_data = {}
    for file_path in annotation_files:
        df = load_annotation_file(file_path, annotator, label_mapping)
        if not df.empty:
            file_data[file_path.name] = df
        else:
            logger.warning(f"Failed to load or empty file: {file_path.name}")
    
    logger.info(f"Successfully loaded {len(file_data)} annotation files")
    return file_data


# ============================================================================
# Entity-Level Classification Metrics
# ============================================================================

def evaluate_entity_classification(df: pd.DataFrame, use_flat_labels: bool = True) -> Dict:
    """
    Evaluate entity classification performance using standard metrics.
    
    Args:
        df: DataFrame with prediction and ground truth columns
        use_flat_labels: If True, use flat label comparison; if False, use BIO comparison
        
    Returns:
        Dictionary with accuracy, F1 scores, and per-class metrics
    """
    # Choose columns based on evaluation type
    if use_flat_labels:
        pred_col = 'pred_flat'
        truth_col = 'ground_truth_flat'
    else:
        pred_col = 'pred_bio'
        truth_col = 'ground_truth_bio'
    
    # Filter out empty/missing annotations and 'nan' string values
    valid_data = df.dropna(subset=[truth_col, pred_col])
    valid_data = valid_data[
        (valid_data[truth_col] != 'nan') & 
        (valid_data[pred_col] != 'nan') &
        (valid_data[truth_col] != '') & 
        (valid_data[pred_col] != '')
    ]
    
    if len(valid_data) == 0:
        logger.warning("No valid ground truth annotations found")
        return {
            'accuracy': 0.0,
            'macro_f1': 0.0,
            'weighted_f1': 0.0,
            'total_samples': 0,
            'per_class_metrics': {}
        }
    
    # Generate classification report
    try:
        report = classification_report(
            valid_data[truth_col], 
            valid_data[pred_col],
            output_dict=True,
            zero_division=0
        )
        
        return {
            'accuracy': report['accuracy'],
            'macro_f1': report['macro avg']['f1-score'],
            'weighted_f1': report['weighted avg']['f1-score'],
            'macro_precision': report['macro avg']['precision'],
            'macro_recall': report['macro avg']['recall'],
            'weighted_precision': report['weighted avg']['precision'],
            'weighted_recall': report['weighted avg']['recall'],
            'total_samples': len(valid_data),
            'per_class_metrics': {k: v for k, v in report.items() 
                                if k not in ['accuracy', 'macro avg', 'weighted avg']}
        }
    except Exception as e:
        logger.error(f"Error in entity classification evaluation: {str(e)}")
        return {
            'accuracy': 0.0,
            'macro_f1': 0.0,
            'weighted_f1': 0.0,
            'total_samples': len(valid_data),
            'per_class_metrics': {}
        }


# ============================================================================
# Token-Level Evaluation Metrics
# ============================================================================

def evaluate_token_level(df: pd.DataFrame) -> Dict:
    """
    Evaluate per-token classification accuracy using flat label comparison.
    
    Args:
        df: DataFrame with pred_flat and ground_truth_flat columns
        
    Returns:
        Dictionary with token-level accuracy metrics
    """
    # Use flat labels for token-level comparison
    valid_data = df.dropna(subset=['ground_truth_flat', 'pred_flat'])
    valid_data = valid_data[
        (valid_data['ground_truth_flat'] != 'nan') & 
        (valid_data['pred_flat'] != 'nan') &
        (valid_data['ground_truth_flat'] != '') & 
        (valid_data['pred_flat'] != '')
    ]
    
    if len(valid_data) == 0:
        return {
            'token_accuracy': 0.0,
            'total_tokens': 0,
            'correct_predictions': 0
        }
    
    correct_predictions = (valid_data['pred_flat'] == valid_data['ground_truth_flat']).sum()
    total_tokens = len(valid_data)
    
    return {
        'token_accuracy': correct_predictions / total_tokens,
        'total_tokens': total_tokens,
        'correct_predictions': correct_predictions
    }


# ============================================================================
# NER Sequence Evaluation (BIO Tags)
# ============================================================================

def evaluate_ner_sequences(file_data: Dict[str, pd.DataFrame]) -> Dict:
    """
    Evaluate NER using sequence-level metrics with proper BIO tag handling.
    
    Args:
        file_data: Dictionary mapping filename to DataFrame
        
    Returns:
        Dictionary with sequence-level NER metrics
    """
    try:
        # Try to import seqeval for proper NER evaluation
        from seqeval.metrics import accuracy_score as seq_accuracy
        from seqeval.metrics import classification_report as seq_report
        from seqeval.metrics import f1_score as seq_f1
        
        all_true_sequences = []
        all_pred_sequences = []
        
        for filename, df in file_data.items():
            # Use BIO format for sequence evaluation
            valid_data = df.dropna(subset=['ground_truth_bio', 'pred_bio'])
            valid_data = valid_data[
                (valid_data['ground_truth_bio'] != 'nan') & 
                (valid_data['pred_bio'] != 'nan') &
                (valid_data['ground_truth_bio'] != '') & 
                (valid_data['pred_bio'] != '')
            ]
            
            if len(valid_data) == 0:
                continue
                
            # Each file represents one document sequence
            true_seq = valid_data['ground_truth_bio'].tolist()
            pred_seq = valid_data['pred_bio'].tolist()
            
            all_true_sequences.append(true_seq)
            all_pred_sequences.append(pred_seq)
        
        if not all_true_sequences:
            logger.warning("No valid sequences found for NER evaluation")
            return {
                'sequence_accuracy': 0.0,
                'sequence_f1': 0.0,
                'total_sequences': 0,
                'detailed_report': {}
            }
        
        # Calculate sequence-level metrics
        seq_acc = seq_accuracy(all_true_sequences, all_pred_sequences)
        seq_f1_score = seq_f1(all_true_sequences, all_pred_sequences)
        
        # Generate detailed sequence report
        detailed_report = seq_report(all_true_sequences, all_pred_sequences, output_dict=True)
        
        return {
            'sequence_accuracy': seq_acc,
            'sequence_f1': seq_f1_score,
            'total_sequences': len(all_true_sequences),
            'detailed_report': detailed_report
        }
        
    except ImportError:
        logger.warning("seqeval not available - falling back to token-level evaluation")
        # Fall back to token-level evaluation
        all_data = pd.concat(file_data.values(), ignore_index=True)
        token_results = evaluate_token_level(all_data)
        
        return {
            'sequence_accuracy': token_results['token_accuracy'],
            'sequence_f1': 0.0,  # Cannot calculate without seqeval
            'total_sequences': len(file_data),
            'detailed_report': {},
            'note': 'Sequence evaluation unavailable - using token-level accuracy'
        }
    except Exception as e:
        logger.error(f"Error in NER sequence evaluation: {str(e)}")
        return {
            'sequence_accuracy': 0.0,
            'sequence_f1': 0.0,
            'total_sequences': 0,
            'detailed_report': {}
        }


# ============================================================================
# Error Pattern Analysis
# ============================================================================

def analyze_error_patterns(df: pd.DataFrame) -> Dict:
    """
    Identify systematic errors in NER model predictions using flat label comparison.
    
    Args:
        df: Combined DataFrame from all annotation files
        
    Returns:
        Dictionary with error pattern analysis
    """
    # Filter to only misclassified tokens using flat labels
    errors = df.dropna(subset=['ground_truth_flat', 'pred_flat'])
    errors = errors[
        (errors['ground_truth_flat'] != 'nan') & 
        (errors['pred_flat'] != 'nan') &
        (errors['ground_truth_flat'] != '') & 
        (errors['pred_flat'] != '')
    ]
    errors = errors[errors['pred_flat'] != errors['ground_truth_flat']]
    
    if len(errors) == 0:
        return {
            'total_errors': 0,
            'error_rate': 0.0,
            'confusion_patterns': {},
            'most_confused_entities': []
        }
    
    total_predictions = len(df.dropna(subset=['ground_truth_flat', 'pred_flat']))
    error_rate = len(errors) / total_predictions if total_predictions > 0 else 0.0
    
    # Most common misclassification patterns
    error_patterns = errors.groupby(['ground_truth_flat', 'pred_flat']).size().sort_values(ascending=False)
    confusion_patterns = error_patterns.head(20).to_dict()
    
    # Convert tuple keys to string format for JSON serialization
    confusion_patterns_str = {
        f"{true_label} → {pred_label}": count 
        for (true_label, pred_label), count in confusion_patterns.items()
    }
    
    # Most confused entity types
    confused_entities = errors['ground_truth_flat'].value_counts().head(10).to_dict()
    
    return {
        'total_errors': len(errors),
        'error_rate': error_rate,
        'confusion_patterns': confusion_patterns_str,
        'most_confused_entities': confused_entities
    }


# ============================================================================
# Inter-Annotator Agreement
# ============================================================================

def calculate_inter_annotator_agreement(df: pd.DataFrame) -> Optional[Dict]:
    """
    Measure agreement between annotator1 and annotator2.
    
    Args:
        df: DataFrame with annotator1_labels and annotator2_labels columns
        
    Returns:
        Dictionary with kappa score and agreement metrics, or None if insufficient data
    """
    # Check if both annotator columns exist
    if 'annotator1_labels' not in df.columns or 'annotator2_labels' not in df.columns:
        logger.info("Inter-annotator agreement: Missing annotator columns")
        return None
    
    # Filter rows where both annotators provided labels
    both_labeled = df.dropna(subset=['annotator1_labels', 'annotator2_labels'])
    
    if len(both_labeled) == 0:
        logger.info("Inter-annotator agreement: No overlapping annotations found")
        return None
    
    try:
        # Calculate Cohen's kappa
        kappa = cohen_kappa_score(
            both_labeled['annotator1_labels'], 
            both_labeled['annotator2_labels']
        )
        
        # Calculate simple agreement percentage
        agreement_count = (both_labeled['annotator1_labels'] == 
                          both_labeled['annotator2_labels']).sum()
        agreement_percentage = agreement_count / len(both_labeled)
        
        return {
            'kappa_score': kappa,
            'agreement_percentage': agreement_percentage,
            'total_dual_annotations': len(both_labeled),
            'agreement_count': agreement_count
        }
        
    except Exception as e:
        logger.error(f"Error calculating inter-annotator agreement: {str(e)}")
        return None


# ============================================================================
# Comprehensive Evaluation Pipeline
# ============================================================================

def run_ner_evaluation(annotation_dir: Union[str, Path], annotator: str = "annotator1") -> Dict:
    """
    Run complete NER evaluation suite on all annotation files with prediction decoding.
    
    Args:
        annotation_dir: Directory containing annotation files
        annotator: Which annotator to use as ground truth ("annotator1" or "annotator2")
        
    Returns:
        Dictionary with comprehensive evaluation results
    """
    logger.info(f"Starting NER evaluation using {annotator} as ground truth...")
    
    # Extract label vocabulary for prediction decoding
    logger.info("Extracting label vocabulary from annotation files...")
    label_mapping = extract_label_vocabulary(annotation_dir)
    
    if label_mapping:
        logger.info(f"Successfully extracted {len(label_mapping)} invoice/receipt entity labels")
        logger.debug(f"Label mapping: {dict(list(label_mapping.items())[:5])}...")  # Show first 5
    else:
        logger.warning("No label mapping found - predictions will not be decoded")
    
    # Load all annotation files with prediction decoding
    file_data = load_all_annotation_files(annotation_dir, annotator, label_mapping)
    
    if not file_data:
        logger.error("No annotation files loaded - cannot proceed with evaluation")
        return {}
    
    results = {
        'evaluation_summary': {
            'total_files': len(file_data),
            'annotation_directory': str(annotation_dir),
            'ground_truth_annotator': annotator,
            'label_mapping_found': label_mapping is not None,
            'total_entity_labels': len(label_mapping) if label_mapping else 0
        },
        'overall_metrics': {},
        'per_file_metrics': {},
        'error_analysis': {},
        'inter_annotator_agreement': None
    }
    
    all_data = []
    
    # Process each annotation file
    logger.info("Evaluating individual files...")
    for filename, df in file_data.items():
        if df.empty:
            continue
            
        all_data.append(df)
        
        # Per-file evaluation
        file_results = {
            'entity_metrics_flat': evaluate_entity_classification(df, use_flat_labels=True),
            'entity_metrics_bio': evaluate_entity_classification(df, use_flat_labels=False),
            'token_metrics': evaluate_token_level(df),
        }
        
        # Add inter-annotator agreement if available
        agreement = calculate_inter_annotator_agreement(df)
        if agreement:
            file_results['inter_annotator_agreement'] = agreement
        
        results['per_file_metrics'][filename] = file_results
    
    # Overall evaluation across all files
    if all_data:
        logger.info("Computing overall metrics...")
        combined_df = pd.concat(all_data, ignore_index=True)
        
        results['overall_metrics'] = {
            'entity_classification_flat': evaluate_entity_classification(combined_df, use_flat_labels=True),
            'entity_classification_bio': evaluate_entity_classification(combined_df, use_flat_labels=False),
            'token_level': evaluate_token_level(combined_df),
            'ner_sequences': evaluate_ner_sequences(file_data)
        }
        
        # Error analysis
        logger.info("Analyzing error patterns...")
        results['error_analysis'] = analyze_error_patterns(combined_df)
        
        # Overall inter-annotator agreement
        overall_agreement = calculate_inter_annotator_agreement(combined_df)
        if overall_agreement:
            results['inter_annotator_agreement'] = overall_agreement
    
    logger.info("NER evaluation completed")
    return results


# ============================================================================
# Reporting Functions
# ============================================================================

def generate_evaluation_report(results: Dict, output_path: Union[str, Path]) -> None:
    """
    Generate comprehensive NER evaluation report.
    
    Args:
        results: Evaluation results dictionary
        output_path: Path where the report will be saved
    """
    if not results:
        logger.error("No results to report")
        return
    
    overall = results.get('overall_metrics', {})
    entity_metrics_flat = overall.get('entity_classification_flat', {})
    entity_metrics_bio = overall.get('entity_classification_bio', {})
    token_metrics = overall.get('token_level', {})
    sequence_metrics = overall.get('ner_sequences', {})
    error_analysis = results.get('error_analysis', {})
    summary = results.get('evaluation_summary', {})
    
    report = f"""# LayoutLM NER Evaluation Report

## Evaluation Summary
- **Total Files Evaluated**: {summary.get('total_files', 0)}
- **Annotation Directory**: {summary.get('annotation_directory', 'N/A')}
- **Ground Truth Annotator**: {summary.get('ground_truth_annotator', 'N/A')}
- **Label Mapping Found**: {summary.get('label_mapping_found', False)}
- **Total Entity Labels**: {summary.get('total_entity_labels', 0)}

## Overall Performance Metrics

### Token-Level Performance (Flat Label Comparison)
- **Token Accuracy**: {token_metrics.get('token_accuracy', 0):.3f}
- **Total Tokens**: {token_metrics.get('total_tokens', 0):,}
- **Correct Predictions**: {token_metrics.get('correct_predictions', 0):,}

### Entity Classification (Flat Labels)
- **Accuracy**: {entity_metrics_flat.get('accuracy', 0):.3f}
- **Macro F1-Score**: {entity_metrics_flat.get('macro_f1', 0):.3f}
- **Weighted F1-Score**: {entity_metrics_flat.get('weighted_f1', 0):.3f}
- **Macro Precision**: {entity_metrics_flat.get('macro_precision', 0):.3f}
- **Macro Recall**: {entity_metrics_flat.get('macro_recall', 0):.3f}

### Entity Classification (BIO Format)
- **Accuracy**: {entity_metrics_bio.get('accuracy', 0):.3f}
- **Macro F1-Score**: {entity_metrics_bio.get('macro_f1', 0):.3f}
- **Weighted F1-Score**: {entity_metrics_bio.get('weighted_f1', 0):.3f}

### Sequence-Level NER Performance
- **Sequence Accuracy**: {sequence_metrics.get('sequence_accuracy', 0):.3f}
- **Sequence F1-Score**: {sequence_metrics.get('sequence_f1', 0):.3f}
- **Total Sequences**: {sequence_metrics.get('total_sequences', 0)}

## Error Analysis
- **Total Errors**: {error_analysis.get('total_errors', 0):,}
- **Error Rate**: {error_analysis.get('error_rate', 0):.3f}

### Top Confusion Patterns
"""
    
    # Add top confusion patterns
    confusion_patterns = error_analysis.get('confusion_patterns', {})
    if confusion_patterns:
        report += "\n| True Label → Predicted Label | Count |\n|-------------------------------|-------|\n"
        for pattern, count in list(confusion_patterns.items())[:10]:
            report += f"| {pattern} | {count} |\n"
    else:
        report += "\nNo confusion patterns found.\n"
    
    # Add inter-annotator agreement if available
    agreement = results.get('inter_annotator_agreement')
    if agreement:
        report += f"""
## Inter-Annotator Agreement
- **Cohen's Kappa**: {agreement.get('kappa_score', 0):.3f}
- **Agreement Percentage**: {agreement.get('agreement_percentage', 0):.3f}
- **Total Dual Annotations**: {agreement.get('total_dual_annotations', 0):,}
"""
    
    # Add per-file summary
    per_file = results.get('per_file_metrics', {})
    if per_file:
        report += "\n## Per-File Performance Summary\n\n"
        report += "| File | Token Accuracy | Entity F1 (Flat) | Entity F1 (BIO) | Total Tokens |\n"
        report += "|------|----------------|------------------|-----------------|-------------|\n"
        
        for filename, metrics in per_file.items():
            token_acc = metrics.get('token_metrics', {}).get('token_accuracy', 0)
            entity_f1_flat = metrics.get('entity_metrics_flat', {}).get('weighted_f1', 0)
            entity_f1_bio = metrics.get('entity_metrics_bio', {}).get('weighted_f1', 0)
            total_tokens = metrics.get('token_metrics', {}).get('total_tokens', 0)
            report += f"| {filename} | {token_acc:.3f} | {entity_f1_flat:.3f} | {entity_f1_bio:.3f} | {total_tokens:,} |\n"
    
    # Save report
    try:
        with open(output_path, 'w') as f:
            f.write(report)
        logger.info(f"Evaluation report saved to: {output_path}")
    except Exception as e:
        logger.error(f"Error saving report: {str(e)}")


def save_results_json(results: Dict, output_path: Union[str, Path]) -> None:
    """
    Save detailed results as JSON for further analysis.
    
    Args:
        results: Evaluation results dictionary
        output_path: Path where JSON will be saved
    """
    try:
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Detailed results saved to: {output_path}")
    except Exception as e:
        logger.error(f"Error saving JSON results: {str(e)}")


# ============================================================================
# Main Function and CLI
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Evaluate NER performance using LayoutLM annotation files"
    )
    parser.add_argument(
        "annotation_dir",
        help="Directory containing .xlsx annotation files"
    )
    parser.add_argument(
        "--annotator",
        choices=["annotator1", "annotator2"],
        default="annotator1",
        help="Which annotator to use as ground truth (default: annotator1)"
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory for output reports (default: reports)"
    )
    parser.add_argument(
        "--report-name",
        default="ner_evaluation_report",
        help="Base name for output files (default: ner_evaluation_report)"
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
    """Main entry point for the NER evaluation script."""
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
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run evaluation
    results = run_ner_evaluation(args.annotation_dir, args.annotator)
    
    if not results:
        logger.error("Evaluation failed - no results generated")
        sys.exit(1)
    
    # Generate reports
    report_path = output_dir / f"{args.report_name}_{args.annotator}.md"
    json_path = output_dir / f"{args.report_name}_{args.annotator}.json"
    
    generate_evaluation_report(results, report_path)
    save_results_json(results, json_path)
    
    # Print summary
    overall = results.get('overall_metrics', {})
    entity_metrics_flat = overall.get('entity_classification_flat', {})
    entity_metrics_bio = overall.get('entity_classification_bio', {})
    token_metrics = overall.get('token_level', {})
    summary = results.get('evaluation_summary', {})
    
    print("\n=== NER Evaluation Summary ===")
    print(f"Ground truth annotator: {args.annotator}")
    print(f"Files evaluated: {summary.get('total_files', 0)}")
    print(f"Label mapping: {summary.get('total_entity_labels', 0)} invoice/receipt entities")
    print(f"Total tokens: {token_metrics.get('total_tokens', 0):,}")
    print(f"Token accuracy: {token_metrics.get('token_accuracy', 0):.3f}")
    print(f"Entity F1 (flat): {entity_metrics_flat.get('weighted_f1', 0):.3f}")
    print(f"Entity F1 (BIO): {entity_metrics_bio.get('weighted_f1', 0):.3f}")
    print("\nReports saved:")
    print(f"  - Markdown: {report_path}")
    print(f"  - JSON: {json_path}")


if __name__ == "__main__":
    main()