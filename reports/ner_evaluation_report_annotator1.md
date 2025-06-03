# LayoutLM NER Evaluation Report

## Evaluation Summary
- **Total Files Evaluated**: 3
- **Annotation Directory**: test_annotations
- **Ground Truth Annotator**: annotator1
- **Label Mapping Found**: True
- **Total Entity Labels**: 8

## Overall Performance Metrics

### Token-Level Performance (Flat Label Comparison)
- **Token Accuracy**: 0.588
- **Total Tokens**: 17
- **Correct Predictions**: 10

### Entity Classification (Flat Labels)
- **Accuracy**: 0.588
- **Macro F1-Score**: 0.437
- **Weighted F1-Score**: 0.569
- **Macro Precision**: 0.514
- **Macro Recall**: 0.426

### Entity Classification (BIO Format)
- **Accuracy**: 0.471
- **Macro F1-Score**: 0.284
- **Weighted F1-Score**: 0.403

### Sequence-Level NER Performance
- **Sequence Accuracy**: 0.588
- **Sequence F1-Score**: 0.000
- **Total Sequences**: 3

## Error Analysis
- **Total Errors**: 7
- **Error Rate**: 0.412

### Top Confusion Patterns

| True Label → Predicted Label | Count |
|-------------------------------|-------|
| I-PER → PER | 2 |
| ADDRESS → ORG | 1 |
| B-PER → PER | 1 |
| FIELD → ADDRESS | 1 |
| FIELD → ORG | 1 |
| VALUE → ORG | 1 |

## Inter-Annotator Agreement
- **Cohen's Kappa**: 0.929
- **Agreement Percentage**: 0.941
- **Total Dual Annotations**: 17

## Per-File Performance Summary

| File | Token Accuracy | Entity F1 (Flat) | Entity F1 (BIO) | Total Tokens |
|------|----------------|------------------|-----------------|-------------|
| test_annotation.xlsx | 0.000 | 0.000 | 0.000 | 3 |
| realistic_test.xlsx | 0.333 | 0.389 | 0.000 | 6 |
| flat_vs_bio_test.xlsx | 1.000 | 1.000 | 1.000 | 8 |
