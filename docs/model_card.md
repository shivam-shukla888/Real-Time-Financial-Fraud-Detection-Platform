# Model Card: Supervised Financial Fraud Classifier

## 1. Model Details

- **Model Name**: AEGIS XGBoost Fraud Classifier
- **Model Version**: 1.0.0
- **Model Architecture**: Extreme Gradient Boosting (`xgboost.XGBClassifier`) with CPU histogram tree method (`tree_method='hist'`)
- **Fallback Architecture**: scikit-learn `HistGradientBoostingClassifier`
- **Trained By**: AEGIS Machine Learning Pipeline (`scripts/train_model.py`)
- **Release Date**: October 2026
- **License**: MIT
- **Artifact Format**: Native XGBoost JSON (`artifacts/fraud_model.json`) & Scikit-Learn Joblib fallback

---

## 2. Intended Use & Scope

- **Primary Objective**: Real-time fraud probability scoring for retail transactions, e-commerce checkouts, and mobile wallet transfers.
- **Out of Scope**: Not intended for direct automated blocking of consumer funds without human-in-the-loop analyst review. Not designed for real-world production banking without training on bank-specific historical fraud logs.

---

## 3. Training & Validation Setup

- **Partitioning Strategy**: Strictly **time-based** (temporal ordering):
  - **Train Partition**: First 70% (4,200 transactions, 75 fraud events)
  - **Validation Partition**: Middle 15% (900 transactions, 27 fraud events)
  - **Held-out Test Partition**: Final 15% (900 transactions, 29 fraud events)
- **Class Imbalance Strategy**:
  - `scale_pos_weight = 55.0` (computed dynamically as `neg_train / pos_train`).
  - **SMOTE was NOT applied** prior to splitting data, strictly preventing synthetic leakage into test evaluation.
- **Hyperparameters**:
  - `n_estimators`: 120
  - `max_depth`: 5
  - `learning_rate`: 0.08
  - `subsample`: 0.85
  - `colsample_bytree`: 0.85
  - `tree_method`: `hist`
  - `random_state`: 42

---

## 4. Measured Test Evaluation Metrics

Evaluated on 900 held-out test transactions (ground truth fraud prevalence = 3.22%):

| Metric | Measured Value | Meaning & Context |
| :--- | :--- | :--- |
| **PR-AUC (Average Precision)** | **0.9978** | Primary metric for imbalanced fraud ranking |
| **ROC-AUC** | **0.9999** | Receiver Operating Characteristic Area |
| **Precision (at t=0.50)** | **1.0000** | 100% of generated alerts were actual fraud |
| **Recall (at t=0.50)** | **0.9655** | 28 out of 29 test fraud cases caught |
| **F1 Score** | **0.9825** | Harmonic mean of precision and recall |
| **Training Time** | **0.16 seconds** | Fast CPU execution suitable for edge or local laptop |
| **Inference Latency** | **6.2 ms (avg)** | Real-time FastAPI scoring pipeline |

### Confusion Matrix (Test Set, n=900)
```
                          Predicted Legitimate (0)    Predicted Fraud (1)
Actual Legitimate (0)             871 (TN)                     0 (FP)
Actual Fraud (1)                    1 (FN)                    28 (TP)
```

---

## 5. Operational Trade-Offs: Precision vs. Recall

In financial fraud operations:
1. **False Positives (0 in test)**: Each false positive triggers an analyst review ticket or customer SMS step-up, causing customer friction and operational expense.
2. **False Negatives (1 in test)**: Uncaught fraud represents chargeback losses and unrecoverable fund outflows.
3. **Threshold Tuning**:
   - Setting threshold lower (e.g., $t=0.30$) maximizes recall (catching 100% of frauds) at the cost of higher analyst investigation volume.
   - Setting threshold higher (e.g., $t=0.70$) minimizes analyst fatigue.
   - **Ensemble Advantage**: AEGIS blends the ML score with the NetworkX syndicate ring score (35% weight), elevating multi-account emulator rings even when raw transaction features appear borderline.

---

## 6. Limitations & Bias

1. **Synthetic Data**: Measured metrics reflect performance on a deterministic synthetic benchmark. Real-world fraud distributions feature sophisticated adversarial evasion.
2. **Concept Drift**: Financial fraud evolves rapidly (new payment rails, novel phishing schemes). Continuous drift monitoring via `app/services/drift.py` is required.
