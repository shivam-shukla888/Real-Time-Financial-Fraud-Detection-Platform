# Fraud Detection Model Evaluation Report

> **EDUCATIONAL DEMO NOTICE**: All metrics reported below were measured on a **deterministic synthetic transaction dataset** (`data/sample_transactions.csv`). These numbers illustrate the mechanics of imbalanced ML evaluation and fraud-ring detection, but do not imply real-world banking performance.

---

## 1. Executive Summary & Measured Results

| Metric | Measured Value | Benchmark Interpretation |
| :--- | :--- | :--- |
| **Model Architecture** | `XGBoost` | Gradient boosted decision trees |
| **Test Set Size** | 900 transactions | Held-out 15% chronological test partition |
| **Test Fraud Cases** | 29 transactions | 3.22% ground truth fraud prevalence |
| **PR-AUC (Average Precision)** | **0.9978** | Primary ranking metric for severe class imbalance |
| **ROC-AUC** | **0.9999** | Area under receiver operating characteristic |
| **Precision (Threshold = 0.5)** | **1.0000** | 28 true frauds out of 28 raised alerts |
| **Recall (Threshold = 0.5)** | **0.9655** | 28 detected frauds out of 29 total actual frauds |
| **F1 Score** | **0.9825** | Harmonic mean of precision and recall |
| **Training Duration** | 0.16 s | Fast CPU execution suitable for local development |

---

## 2. Confusion Matrix & Operational Trade-Offs

```
                      Predicted Legitimate (0)    Predicted Fraud (1)
Actual Legitimate (0)         871    (TN)                 0      (FP)
Actual Fraud (1)              1      (FN)                 28     (TP)
```

### The Analyst Fatigue vs. Financial Loss Balance
In real-time fraud operations, model evaluation cannot be reduced to simple accuracy (which is trivially >98% on this imbalanced dataset):
1. **False Positives (0)**: Every false positive routes a legitimate customer to manual review, creating **analyst investigation burden** and customer friction.
2. **False Negatives (1)**: Every false negative is a **chargeback or unrecovered fraudulent transfer**, directly impacting loss reserves.
3. **Threshold Tuning**: Lowering the decision threshold increases recall (catching more fraud) but increases false positives. In this system, we blend the supervised probability with the graph fraud-ring score to prioritize high-confidence alerts.

---

## 3. Evaluation Artifacts

- **Confusion Matrix Visualization**: `reports/confusion_matrix.png`
- **Precision-Recall Curve**: `reports/precision_recall_curve.png`
- **Machine-Readable Metrics**: `reports/metrics.json`
- **Trained Model Binary**: `artifacts/fraud_model.json`
