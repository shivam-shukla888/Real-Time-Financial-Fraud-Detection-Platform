"""
Model Training and Precision-Recall Evaluation Pipeline.
Trains an imbalanced-aware XGBoost classifier (with scikit-learn fallback)
using strict time-based splits and zero target leakage.
Logs runs to MLflow and exports confusion matrix, PR curve, and evaluation reports.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server/script use
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    confusion_matrix,
    precision_recall_curve
)

# Project imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from configs.settings import settings, ARTIFACTS_DIR, REPORTS_DIR
from app.features.pipeline import FeaturePipeline


def train_and_evaluate(data_path: Path = settings.DATA_PATH):
    print("=" * 70)
    print(" REAL-TIME FINANCIAL FRAUD DETECTION -- MODEL TRAINING PIPELINE")
    print("=" * 70)

    start_wall_time = time.time()

    # 1. Load Data
    print(f"[*] Loading dataset from: {data_path}")
    df = pd.read_csv(data_path)
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    n_total = len(df)
    n_fraud = int(df["is_fraud"].sum())
    fraud_prevalence = n_fraud / n_total
    print(f"[INFO] Loaded {n_total:,} transactions. Total fraud: {n_fraud} ({fraud_prevalence:.2%})")

    # 2. Extract Features Chronologically (Strict zero-leakage stateful pipeline)
    print("[*] Extracting features via FeaturePipeline...")
    pipeline = FeaturePipeline(cold_start_avg_amount=settings.COLD_START_AVERAGE_AMOUNT)
    X, y = pipeline.transform_batch(df)
    feature_names = list(X.columns)
    print(f"[OK] Extracted {len(feature_names)} features: {feature_names}")

    # 3. Time-Based Split (70% Train, 15% Validation, 15% Test)
    idx_train_end = int(n_total * 0.70)
    idx_val_end = int(n_total * 0.85)

    X_train, y_train = X.iloc[:idx_train_end], y.iloc[:idx_train_end]
    X_val, y_val = X.iloc[idx_train_end:idx_val_end], y.iloc[idx_train_end:idx_val_end]
    X_test, y_test = X.iloc[idx_val_end:], y.iloc[idx_val_end:]

    print(f"[INFO] Split sizes: Train={len(X_train)} (fraud={y_train.sum()}), "
          f"Val={len(X_val)} (fraud={y_val.sum()}), "
          f"Test={len(X_test)} (fraud={y_test.sum()})")

    # Calculate class imbalance weighting
    neg_train = int((y_train == 0).sum())
    pos_train = int((y_train == 1).sum())
    scale_pos_weight = float(neg_train / max(1, pos_train))
    print(f"[INFO] Class balance ratio: {scale_pos_weight:.2f} (negative / positive)")

    # 4. Train Model (XGBoost with HistGradientBoosting fallback)
    model_type = "XGBoost"
    params = {
        "n_estimators": 120,
        "max_depth": 5,
        "learning_rate": 0.08,
        "scale_pos_weight": scale_pos_weight,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "random_state": settings.RANDOM_SEED,
        "tree_method": "hist",
        "eval_metric": "logloss"
    }

    train_start = time.time()
    try:
        import xgboost as xgb
        print(f"[*] Fitting XGBClassifier (tree_method='hist', scale_pos_weight={scale_pos_weight:.2f})...")
        model = xgb.XGBClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
    except Exception as e:
        print(f"[WARN] XGBoost fit error ({e}). Falling back to scikit-learn HistGradientBoostingClassifier.")
        from sklearn.ensemble import HistGradientBoostingClassifier
        model_type = "HistGradientBoosting"
        params = {"max_iter": 120, "max_depth": 5, "learning_rate": 0.08, "random_state": settings.RANDOM_SEED}
        model = HistGradientBoostingClassifier(**params)
        model.fit(X_train, y_train)

    train_duration_sec = time.time() - train_start
    print(f"[OK] Model training complete in {train_duration_sec:.2f} seconds.")

    # 5. Evaluate on Test Set
    print("[*] Evaluating on held-out test set...")
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Evaluate at decision threshold
    threshold = 0.50
    y_pred = (y_pred_proba >= threshold).astype(int)

    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    pr_auc = float(average_precision_score(y_test, y_pred_proba))
    roc_auc = float(roc_auc_score(y_test, y_pred_proba))

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    test_fraud_prevalence = float(y_test.sum() / len(y_test))

    print("\n" + "-" * 40)
    print(f" MODEL EVALUATION METRICS (Test Set, n={len(y_test)})")
    print("-" * 40)
    print(f" Model Architecture   : {model_type}")
    print(f" PR-AUC / Avg Prec    : {pr_auc:.4f}")
    print(f" ROC-AUC              : {roc_auc:.4f}")
    print(f" Precision (at t={threshold:.2f}) : {precision:.4f} ({tp}/{tp+fp} alerts were real fraud)")
    print(f" Recall    (at t={threshold:.2f}) : {recall:.4f} ({tp}/{tp+fn} actual frauds detected)")
    print(f" F1-Score             : {f1:.4f}")
    print(f" Confusion Matrix     : TN={tn}, FP={fp}, FN={fn}, TP={tp}")
    print(f" Test Fraud Prevalence: {test_fraud_prevalence:.2%}")
    print("-" * 40 + "\n")

    # 6. Save Artifacts
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Save model
    if model_type == "XGBoost":
        model.save_model(str(settings.MODEL_PATH))
    else:
        import joblib
        joblib.dump(model, str(settings.MODEL_PATH.with_suffix(".joblib")))
    print(f"[OK] Saved model to: {settings.MODEL_PATH}")

    # Save feature names
    with open(settings.FEATURE_NAMES_PATH, "w") as f:
        json.dump(feature_names, f, indent=2)
    print(f"[OK] Saved feature names to: {settings.FEATURE_NAMES_PATH}")

    # Save metadata
    metadata = {
        "model_type": model_type,
        "trained_at": datetime.now().isoformat(),
        "training_duration_seconds": round(train_duration_sec, 2),
        "random_seed": settings.RANDOM_SEED,
        "n_train": len(X_train),
        "n_val": len(X_val),
        "n_test": len(X_test),
        "scale_pos_weight": scale_pos_weight,
        "hyperparameters": {k: str(v) for k, v in params.items()},
        "feature_count": len(feature_names),
        "dataset_is_synthetic": True,
        "operational_threshold": threshold
    }
    with open(settings.MODEL_METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[OK] Saved model metadata to: {settings.MODEL_METADATA_PATH}")

    # Save metrics JSON
    metrics_data = {
        "timestamp": datetime.now().isoformat(),
        "model_type": model_type,
        "dataset_type": "synthetic_educational_sample",
        "test_records": len(y_test),
        "test_fraud_count": int(y_test.sum()),
        "test_fraud_prevalence": round(test_fraud_prevalence, 4),
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "confusion_matrix": {
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "true_positives": tp
        },
        "false_positive_rate": round(fp / max(1, fp + tn), 4),
        "false_negative_rate": round(fn / max(1, fn + tp), 4),
        "training_time_seconds": round(train_duration_sec, 2)
    }
    with open(settings.METRICS_PATH, "w") as f:
        json.dump(metrics_data, f, indent=2)
    print(f"[OK] Saved metrics to: {settings.METRICS_PATH}")

    # 7. Generate Evaluation Visualizations
    # 7a. Confusion Matrix Plot
    plt.figure(figsize=(6, 5))
    cm_display = np.array([[tn, fp], [fn, tp]])
    sns.heatmap(
        cm_display,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["Legitimate (0)", "Fraud (1)"],
        yticklabels=["Legitimate (0)", "Fraud (1)"]
    )
    plt.title(f"Confusion Matrix — Test Set (Threshold = {threshold})", fontsize=12, pad=12)
    plt.xlabel("Predicted Label", fontsize=10)
    plt.ylabel("Actual Label", fontsize=10)
    plt.tight_layout()
    cm_path = REPORTS_DIR / "confusion_matrix.png"
    plt.savefig(cm_path, dpi=180)
    plt.close()
    print(f"[OK] Saved confusion matrix plot to: {cm_path}")

    # 7b. Precision-Recall Curve Plot
    precisions, recalls, pr_thresholds = precision_recall_curve(y_test, y_pred_proba)
    plt.figure(figsize=(7, 5))
    plt.plot(recalls, precisions, color="#0284c7", lw=2, label=f"XGBoost PR Curve (PR-AUC = {pr_auc:.3f})")
    plt.axhline(y=test_fraud_prevalence, color="#ef4444", linestyle="--", lw=1.5,
                label=f"Baseline Prevalence ({test_fraud_prevalence:.2%})")
    plt.title("Precision-Recall Curve (Imbalanced Financial Fraud)", fontsize=12, pad=12)
    plt.xlabel("Recall (Detection Rate)", fontsize=10)
    plt.ylabel("Precision (Positive Predictive Value)", fontsize=10)
    plt.ylim([0.0, 1.05])
    plt.xlim([0.0, 1.0])
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    pr_path = REPORTS_DIR / "precision_recall_curve.png"
    plt.savefig(pr_path, dpi=180)
    plt.close()
    print(f"[OK] Saved Precision-Recall curve plot to: {pr_path}")

    # 8. Log Run to MLflow (Local SQLite tracking)
    try:
        import mlflow
        db_path = (ARTIFACTS_DIR / "mlflow.db").as_posix()
        mlflow.set_tracking_uri(f"sqlite:///{db_path}")
        mlflow.set_experiment("real-time-fraud-detection")
        with mlflow.start_run(run_name=f"{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            mlflow.log_params(params)
            mlflow.log_param("model_type", model_type)
            mlflow.log_param("train_samples", len(X_train))
            mlflow.log_param("test_samples", len(X_test))
            mlflow.log_param("scale_pos_weight", scale_pos_weight)
            mlflow.log_metric("pr_auc", pr_auc)
            mlflow.log_metric("roc_auc", roc_auc)
            mlflow.log_metric("precision", precision)
            mlflow.log_metric("recall", recall)
            mlflow.log_metric("f1_score", f1)
            mlflow.log_metric("training_duration_sec", train_duration_sec)
            mlflow.log_artifact(str(cm_path))
            mlflow.log_artifact(str(pr_path))
            mlflow.log_artifact(str(settings.METRICS_PATH))
            print("[OK] Logged run parameters, metrics, and artifacts to MLflow experiment tracking.")
    except Exception as e:
        print(f"[INFO] MLflow tracking skipped or failed ({e}); local artifact storage used.")

    # 9. Generate Evaluation Report Markdown
    eval_report_path = REPORTS_DIR / "evaluation_report.md"
    report_content = f"""# Fraud Detection Model Evaluation Report

> **EDUCATIONAL DEMO NOTICE**: All metrics reported below were measured on a **deterministic synthetic transaction dataset** (`data/sample_transactions.csv`). These numbers illustrate the mechanics of imbalanced ML evaluation and fraud-ring detection, but do not imply real-world banking performance.

---

## 1. Executive Summary & Measured Results

| Metric | Measured Value | Benchmark Interpretation |
| :--- | :--- | :--- |
| **Model Architecture** | `{model_type}` | Gradient boosted decision trees |
| **Test Set Size** | {len(y_test):,} transactions | Held-out 15% chronological test partition |
| **Test Fraud Cases** | {int(y_test.sum())} transactions | {test_fraud_prevalence:.2%} ground truth fraud prevalence |
| **PR-AUC (Average Precision)** | **{pr_auc:.4f}** | Primary ranking metric for severe class imbalance |
| **ROC-AUC** | **{roc_auc:.4f}** | Area under receiver operating characteristic |
| **Precision (Threshold = {threshold})** | **{precision:.4f}** | {tp} true frauds out of {tp + fp} raised alerts |
| **Recall (Threshold = {threshold})** | **{recall:.4f}** | {tp} detected frauds out of {tp + fn} total actual frauds |
| **F1 Score** | **{f1:.4f}** | Harmonic mean of precision and recall |
| **Training Duration** | {train_duration_sec:.2f} s | Fast CPU execution suitable for local development |

---

## 2. Confusion Matrix & Operational Trade-Offs

```
                      Predicted Legitimate (0)    Predicted Fraud (1)
Actual Legitimate (0)         {tn:<6} (TN)                 {fp:<6} (FP)
Actual Fraud (1)              {fn:<6} (FN)                 {tp:<6} (TP)
```

### The Analyst Fatigue vs. Financial Loss Balance
In real-time fraud operations, model evaluation cannot be reduced to simple accuracy (which is trivially >98% on this imbalanced dataset):
1. **False Positives ({fp})**: Every false positive routes a legitimate customer to manual review, creating **analyst investigation burden** and customer friction.
2. **False Negatives ({fn})**: Every false negative is a **chargeback or unrecovered fraudulent transfer**, directly impacting loss reserves.
3. **Threshold Tuning**: Lowering the decision threshold increases recall (catching more fraud) but increases false positives. In this system, we blend the supervised probability with the graph fraud-ring score to prioritize high-confidence alerts.

---

## 3. Evaluation Artifacts

- **Confusion Matrix Visualization**: `reports/confusion_matrix.png`
- **Precision-Recall Curve**: `reports/precision_recall_curve.png`
- **Machine-Readable Metrics**: `reports/metrics.json`
- **Trained Model Binary**: `artifacts/fraud_model.json`
"""
    with open(eval_report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"[OK] Written evaluation report to: {eval_report_path}")

    total_time = time.time() - start_wall_time
    print(f"\n[SUMMARY] Model training and evaluation successfully completed in {total_time:.2f}s.\n")
    return metrics_data


if __name__ == "__main__":
    train_and_evaluate()
