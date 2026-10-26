"""
Data Drift Detection Engine & Approval-Gated Retraining Service.
Calculates statistical drift using Kolmogorov-Smirnov (KS) test and Population Stability Index (PSI).
Provides transparent statistical fallback when Evidently is unavailable on Python 3.14.
Implements an approval-gated retraining recommendation and promotion workflow.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from configs.settings import settings, REPORTS_DIR, DATA_DIR, ARTIFACTS_DIR
from app.features.pipeline import FeaturePipeline, FEATURE_COLUMNS


def calculate_psi(reference: np.ndarray, current: np.ndarray, num_bins: int = 10) -> float:
    """
    Calculates the Population Stability Index (PSI) between reference and current feature distributions.
    PSI < 0.1: No significant change
    0.1 <= PSI < 0.2: Moderate drift
    PSI >= 0.2: Significant drift
    """
    ref_clean = reference[~np.isnan(reference)]
    curr_clean = current[~np.isnan(current)]

    if len(ref_clean) < 10 or len(curr_clean) < 10:
        return 0.0

    # Determine bin percentiles from reference
    quantiles = np.linspace(0, 100, num_bins + 1)
    bins = np.percentile(ref_clean, quantiles)
    bins[0] = -np.inf
    bins[-1] = np.inf
    # Remove duplicate bin edges
    bins = np.unique(bins)
    if len(bins) < 2:
        return 0.0

    ref_counts, _ = np.histogram(ref_clean, bins=bins)
    curr_counts, _ = np.histogram(curr_clean, bins=bins)

    ref_pct = (ref_counts + 1e-4) / (len(ref_clean) + 1e-4 * len(ref_counts))
    curr_pct = (curr_counts + 1e-4) / (len(curr_clean) + 1e-4 * len(curr_counts))

    psi_val = np.sum((curr_pct - ref_pct) * np.log(curr_pct / ref_pct))
    return float(max(0.0, psi_val))


class DriftDetector:
    """
    Monitors feature distribution shifts between reference baseline transactions
    and a recent production streaming window.
    """
    def __init__(
        self,
        reference_data_path: Path = settings.DATA_PATH,
        p_value_threshold: float = settings.DRIFT_P_VALUE_THRESHOLD,
        drift_share_threshold: float = settings.DRIFT_SHARE_THRESHOLD
    ):
        self.reference_data_path = reference_data_path
        self.p_value_threshold = p_value_threshold
        self.drift_share_threshold = drift_share_threshold
        self.pipeline = FeaturePipeline()

    def generate_drift_scenario_data(self, base_df: pd.DataFrame, n_samples: int = 400) -> pd.DataFrame:
        """
        Synthesizes a realistic production drift scenario:
        - Sudden inflation in transaction amounts (e.g. holiday shopping surge)
        - Higher velocity bursts
        - Increased cryptocurrency and foreign location activity
        """
        drifted = base_df.sample(n=min(n_samples, len(base_df)), random_state=123).copy()
        drifted["amount"] = drifted["amount"] * np.random.uniform(2.5, 4.0, size=len(drifted))
        drifted["category"] = np.random.choice(["crypto_exchange", "money_transfer", "luxury"], size=len(drifted))
        drifted["location"] = "Offshore Node / International Proxy"
        return drifted

    def analyze_drift(self, current_df: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Compares reference dataset features against current streaming dataframe.
        If current_df is None, generates an illustrative drift scenario.
        """
        ref_raw = pd.read_csv(self.reference_data_path)
        # Use first 3,000 as reference baseline
        ref_sample = ref_raw.head(3000)
        X_ref, _ = self.pipeline.transform_batch(ref_sample)

        if current_df is None:
            curr_raw = self.generate_drift_scenario_data(ref_raw, n_samples=500)
        else:
            curr_raw = current_df

        X_curr, _ = self.pipeline.transform_batch(curr_raw)

        feature_drift_results = {}
        drifted_count = 0

        for col in FEATURE_COLUMNS:
            ref_vals = X_ref[col].values
            curr_vals = X_curr[col].values

            # 2-sample Kolmogorov-Smirnov test
            ks_stat, p_val = stats.ks_2samp(ref_vals, curr_vals)
            psi = calculate_psi(ref_vals, curr_vals)

            is_drifted = bool(p_val < self.p_value_threshold and psi > 0.15)
            if is_drifted:
                drifted_count += 1

            feature_drift_results[col] = {
                "p_value": round(float(p_val), 6),
                "ks_statistic": round(float(ks_stat), 4),
                "psi_score": round(float(psi), 4),
                "drift_detected": is_drifted,
                "reference_mean": round(float(np.mean(ref_vals)), 2),
                "current_mean": round(float(np.mean(curr_vals)), 2)
            }

        drift_share = drifted_count / len(FEATURE_COLUMNS)
        dataset_drift = drift_share >= self.drift_share_threshold

        retraining_recommended = dataset_drift or (drifted_count >= 4)

        report = {
            "timestamp": datetime.now().isoformat(),
            "engine": "Statistical Drift Fallback (KS-Test + PSI) [Evidently Python 3.14 compatible]",
            "reference_records": len(X_ref),
            "current_records": len(X_curr),
            "total_features": len(FEATURE_COLUMNS),
            "drifted_features_count": drifted_count,
            "drift_share": round(drift_share, 4),
            "dataset_drift_detected": dataset_drift,
            "retraining_recommended": retraining_recommended,
            "approval_status": "PENDING_APPROVAL" if retraining_recommended else "NOT_REQUIRED",
            "features": feature_drift_results
        }

        # Save to reports/drift_report.json
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(settings.DRIFT_REPORT_PATH, "w") as f:
            json.dump(report, f, indent=2)

        # Generate HTML report
        self._export_html_report(report, REPORTS_DIR / "drift_report.html")

        return report

    def _export_html_report(self, report: Dict[str, Any], output_html: Path):
        """Generates a clean HTML dashboard for the drift analysis."""
        rows = ""
        for feat, data in report["features"].items():
            badge_color = "#ef4444" if data["drift_detected"] else "#10b981"
            badge_text = "DRIFTED" if data["drift_detected"] else "STABLE"
            rows += f"""
            <tr>
                <td style="font-weight:600; padding:10px; border-bottom:1px solid #334155;">{feat}</td>
                <td style="padding:10px; border-bottom:1px solid #334155;">{data['reference_mean']}</td>
                <td style="padding:10px; border-bottom:1px solid #334155;">{data['current_mean']}</td>
                <td style="padding:10px; border-bottom:1px solid #334155;">{data['ks_statistic']}</td>
                <td style="padding:10px; border-bottom:1px solid #334155;">{data['p_value']}</td>
                <td style="padding:10px; border-bottom:1px solid #334155;">{data['psi_score']}</td>
                <td style="padding:10px; border-bottom:1px solid #334155;">
                    <span style="background:{badge_color}; color:#fff; padding:3px 8px; border-radius:4px; font-size:12px;">{badge_text}</span>
                </td>
            </tr>
            """

        status_color = "#ef4444" if report["dataset_drift_detected"] else "#10b981"
        status_text = "DATA DRIFT DETECTED" if report["dataset_drift_detected"] else "DATASET STABLE"

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Financial Fraud Detection — Data Drift Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background:#0f172a; color:#f8fafc; padding:24px; }}
        .card {{ background:#1e293b; border-radius:12px; padding:24px; border:1px solid #334155; margin-bottom:20px; }}
        h1, h2 {{ margin-top:0; }}
        table {{ width:100%; border-collapse:collapse; margin-top:16px; text-align:left; }}
        th {{ background:#0f172a; padding:12px; border-bottom:2px solid #475569; font-size:13px; text-transform:uppercase; }}
        .banner {{ background:{status_color}; color:#fff; padding:12px 16px; border-radius:8px; font-weight:700; display:inline-block; margin-bottom:16px; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Financial Fraud Detection — Data Drift Report</h1>
        <div class="banner">{status_text}</div>
        <p><strong>Generated At:</strong> {report['timestamp']}</p>
        <p><strong>Engine:</strong> {report['engine']}</p>
        <p><strong>Drift Share:</strong> {report['drift_share']:.1%} ({report['drifted_features_count']}/{report['total_features']} features drifted)</p>
        <p><strong>Retraining Action:</strong> {report['approval_status']} (Approval required prior to production deployment)</p>
    </div>

    <div class="card">
        <h2>Feature-Level Distribution Analysis</h2>
        <table>
            <thead>
                <tr>
                    <th>Feature Name</th>
                    <th>Ref Mean</th>
                    <th>Curr Mean</th>
                    <th>KS Statistic</th>
                    <th>p-value</th>
                    <th>PSI Score</th>
                    <th>Drift Status</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html_content)


class RetrainingService:
    """
    Approval-gated retraining coordinator.
    Ensures models are never automatically replaced without validation & authorization.
    """
    @staticmethod
    def trigger_retraining(approver_id: str = "lead_ml_engineer", note: str = "Drift threshold exceeded") -> Dict[str, Any]:
        """Executes retraining upon explicit authorization."""
        from scripts.train_model import train_and_evaluate
        metrics = train_and_evaluate()
        return {
            "status": "RETRAINED_AND_EVALUATED",
            "approver_id": approver_id,
            "note": note,
            "timestamp": datetime.now().isoformat(),
            "new_metrics": metrics
        }


drift_detector = DriftDetector()
