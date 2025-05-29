"""Main evaluation script for LayoutLM form understanding."""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)


def setup_logging(log_level: str = "INFO") -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("evaluation.log"),
        ],
    )


def load_prediction_files(predictions_dir: Path) -> List[pd.DataFrame]:
    """Load all CSV prediction files from directory.
    
    Args:
        predictions_dir: Directory containing CSV prediction files
        
    Returns:
        List of DataFrames, one per page
    """
    csv_files = list(predictions_dir.glob("*.csv"))
    if not csv_files:
        raise ValueError(f"No CSV files found in {predictions_dir}")
    
    dataframes = []
    for csv_file in sorted(csv_files):
        page_df = pd.read_csv(csv_file)
        # Validate required columns
        required_cols = ['bboxes', 'pred', 'prob', 'labels']
        missing_cols = [col for col in required_cols if col not in page_df.columns]
        if missing_cols:
            raise ValueError(f"Missing columns in {csv_file}: {missing_cols}")
        dataframes.append(page_df)
    
    return dataframes


def compute_token_metrics(all_predictions: np.ndarray, all_labels: np.ndarray) -> Dict:
    """Compute token-level evaluation metrics.
    
    Args:
        all_predictions: Array of predicted class labels
        all_labels: Array of ground truth class labels
        
    Returns:
        Dictionary containing token-level metrics
    """
    accuracy = accuracy_score(all_labels, all_predictions)
    f1_macro = f1_score(all_labels, all_predictions, average='macro', zero_division=0)
    f1_micro = f1_score(all_labels, all_predictions, average='micro', zero_division=0)
    f1_weighted = f1_score(all_labels, all_predictions, average='weighted', zero_division=0)
    
    # Classification report for per-class metrics
    class_report = classification_report(all_labels, all_predictions, output_dict=True, zero_division=0)
    
    return {
        'token_accuracy': accuracy,
        'token_f1_macro': f1_macro,
        'token_f1_micro': f1_micro,
        'token_f1_weighted': f1_weighted,
        'classification_report': class_report,
        'confusion_matrix': confusion_matrix(all_labels, all_predictions).tolist()
    }


def compute_page_metrics(page_dataframes: List[pd.DataFrame]) -> Dict:
    """Compute page-level evaluation metrics.
    
    Args:
        page_dataframes: List of DataFrames, one per page
        
    Returns:
        Dictionary containing page-level metrics
    """
    page_accuracies = []
    page_f1_scores = []
    perfect_accuracy_pages = 0
    
    for page_df in page_dataframes:
        if len(page_df) == 0:
            continue
            
        page_acc = accuracy_score(page_df['labels'], page_df['pred'])
        page_f1 = f1_score(page_df['labels'], page_df['pred'], average='macro', zero_division=0)
        
        page_accuracies.append(page_acc)
        page_f1_scores.append(page_f1)
        
        if page_acc == 1.0:
            perfect_accuracy_pages += 1
    
    return {
        'page_accuracy_mean': np.mean(page_accuracies) if page_accuracies else 0,
        'page_accuracy_std': np.std(page_accuracies) if page_accuracies else 0,
        'page_f1_mean': np.mean(page_f1_scores) if page_f1_scores else 0,
        'page_f1_std': np.std(page_f1_scores) if page_f1_scores else 0,
        'pages_perfect_accuracy': perfect_accuracy_pages,
        'total_pages': len([page_df for page_df in page_dataframes if len(page_df) > 0])
    }


def main() -> None:
    """Main evaluation function."""
    parser = argparse.ArgumentParser(description="Evaluate LayoutLM predictions from CSV files")
    
    # Data arguments
    parser.add_argument("--predictions_dir", type=str, required=True,
                       help="Directory containing CSV prediction files (one per page)")
    parser.add_argument("--output_dir", type=str, default="./results",
                       help="Directory to save evaluation results")
    
    # Model arguments
    parser.add_argument("--num_classes", type=int, default=58,
                       help="Number of classification categories")
    parser.add_argument("--class_names_file", type=str, default=None,
                       help="Path to file containing class names")
    
    # Other arguments
    parser.add_argument("--log_level", type=str, default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    parser.add_argument("--save_detailed_results", action="store_true",
                       help="Save detailed per-class and per-page results")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save evaluation configuration
    config = vars(args)
    config_path = output_dir / "eval_config.json"
    config_path.write_text(json.dumps(config, indent=2))
    
    # Load class names if provided (currently unused but kept for future extension)
    if args.class_names_file:
        class_names_path = Path(args.class_names_file)
        class_names_path.read_text().strip().split('\n')
    
    # Load prediction files
    logger.info(f"Loading prediction files from {args.predictions_dir}")
    predictions_dir = Path(args.predictions_dir)
    page_dataframes = load_prediction_files(predictions_dir)
    logger.info(f"Loaded {len(page_dataframes)} prediction files")
    
    # Combine all predictions and labels for token-level metrics
    all_predictions = []
    all_labels = []
    total_tokens = 0
    
    for page_df in page_dataframes:
        if len(page_df) > 0:
            all_predictions.extend(page_df['pred'].tolist())
            all_labels.extend(page_df['labels'].tolist())
            total_tokens += len(page_df)
    
    logger.info(f"Total tokens across all pages: {total_tokens}")
    
    # Compute token-level metrics
    logger.info("Computing token-level metrics...")
    token_metrics = compute_token_metrics(
        np.array(all_predictions), 
        np.array(all_labels)
    )
    
    # Compute page-level metrics
    logger.info("Computing page-level metrics...")
    page_metrics = compute_page_metrics(page_dataframes)
    
    # Combine all metrics
    final_metrics = {
        **token_metrics,
        **page_metrics,
        'total_tokens': total_tokens,
        'avg_tokens_per_page': total_tokens / page_metrics['total_pages'] if page_metrics['total_pages'] > 0 else 0
    }
    
    # Save detailed results if requested
    if args.save_detailed_results:
        # Save classification report
        class_report_df = pd.DataFrame(token_metrics['classification_report']).transpose()
        class_report_df.to_csv(output_dir / "classification_report.csv")
        
        # Save confusion matrix
        confusion_df = pd.DataFrame(token_metrics['confusion_matrix'])
        confusion_df.to_csv(output_dir / "confusion_matrix.csv", index=False)
        
        # Save per-page results
        page_results = []
        for i, page_df in enumerate(page_dataframes):
            if len(page_df) > 0:
                page_acc = accuracy_score(page_df['labels'], page_df['pred'])
                page_f1 = f1_score(page_df['labels'], page_df['pred'], average='macro', zero_division=0)
                page_results.append({
                    'page_id': i,
                    'num_tokens': len(page_df),
                    'accuracy': page_acc,
                    'f1_macro': page_f1
                })
        
        page_results_df = pd.DataFrame(page_results)
        page_results_df.to_csv(output_dir / "per_page_results.csv", index=False)
    
    # Save summary metrics
    # Remove non-serializable items for JSON
    json_metrics = {k: v for k, v in final_metrics.items() 
                   if k not in ['classification_report', 'confusion_matrix']}
    
    summary_path = output_dir / "summary_metrics.json"
    summary_path.write_text(json.dumps(json_metrics, indent=2))
    
    # Print summary
    print("\n" + "="*50)
    print("LAYOUTLM EVALUATION SUMMARY")
    print("="*50)
    print(f"Total tokens evaluated: {final_metrics.get('total_tokens', 0)}")
    print(f"Total pages evaluated: {final_metrics.get('total_pages', 0)}")
    print(f"Average tokens per page: {final_metrics.get('avg_tokens_per_page', 0):.1f}")
    print()
    print("TOKEN-LEVEL METRICS:")
    print(f"  Accuracy: {final_metrics.get('token_accuracy', 0):.4f}")
    print(f"  F1 (macro): {final_metrics.get('token_f1_macro', 0):.4f}")
    print(f"  F1 (micro): {final_metrics.get('token_f1_micro', 0):.4f}")
    print(f"  F1 (weighted): {final_metrics.get('token_f1_weighted', 0):.4f}")
    print()
    print("PAGE-LEVEL METRICS:")
    print(f"  Accuracy (mean): {final_metrics.get('page_accuracy_mean', 0):.4f}")
    print(f"  Accuracy (std): {final_metrics.get('page_accuracy_std', 0):.4f}")
    print(f"  F1 (mean): {final_metrics.get('page_f1_mean', 0):.4f}")
    print(f"  F1 (std): {final_metrics.get('page_f1_std', 0):.4f}")
    print(f"  Perfect accuracy pages: {final_metrics.get('pages_perfect_accuracy', 0)}")
    print("="*50)
    
    logger.info("Evaluation completed successfully!")
    logger.info(f"Results saved to: {output_dir}")
    logger.info(f"Token accuracy: {final_metrics.get('token_accuracy', 0):.4f}")
    logger.info(f"Token F1 (macro): {final_metrics.get('token_f1_macro', 0):.4f}")
    logger.info(f"Page accuracy (mean): {final_metrics.get('page_accuracy_mean', 0):.4f}")


if __name__ == "__main__":
    main()