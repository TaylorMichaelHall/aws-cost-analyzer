"""
Anomaly detection for cost patterns
"""

import numpy as np
from scipy.stats import zscore

from .base import BaseAnalyzer

# Constants for anomaly detection thresholds
HIGH_SEVERITY_THRESHOLD = 3.0
SERVICE_ANOMALY_THRESHOLD = 2.5
MIN_SERVICE_COST_THRESHOLD = 10.0
MIN_SERVICE_VARIANCE = 1.0


class AnomalyDetector(BaseAnalyzer):
    """Detects unusual cost patterns and anomalies"""

    def analyze(self, df):
        """Run anomaly detection"""
        return self.run_anomaly_detection(df)

    def run_anomaly_detection(self, df):  # noqa: PLR0912,PLR0915
        """Detect unusual cost spikes or drops using statistical methods.

        Accounts for monthly billing patterns to reduce false positives.
        """
        if df is None:
            return None

        self.print_section_header("ANOMALY DETECTION")

        anomalies = []

        # Check total daily costs for anomalies, excluding known first-of-month spikes
        total_costs = df["Total costs($)"]

        # Use different approaches based on whether we have monthly billing pattern data
        monthly_billing_stats = self.data_processor.get_monthly_billing_stats()
        if monthly_billing_stats is not None and "HasMonthlyBillingSpike" in df.columns:
            # Exclude known monthly billing spikes from anomaly detection
            clean_costs = df[~df["HasMonthlyBillingSpike"]]["Total costs($)"]
            if len(clean_costs) > 0:
                z_scores = np.abs(zscore(clean_costs))
                # Map back to original dataframe
                clean_outliers = z_scores > self.config.anomaly_threshold
                outliers = np.zeros(len(total_costs), dtype=bool)
                outliers[~df["HasMonthlyBillingSpike"]] = clean_outliers
            else:
                z_scores = np.abs(zscore(total_costs))
                outliers = z_scores > self.config.anomaly_threshold
        else:
            z_scores = np.abs(zscore(total_costs))
            outliers = z_scores > self.config.anomaly_threshold

        if outliers.any():
            print(
                "Unusual daily total cost patterns (excluding monthly billing spikes):"
            )
            print("-" * 55)

            # Recalculate z-scores for outliers for display purposes
            outlier_z_scores = np.abs(zscore(total_costs))

            for idx, is_outlier in enumerate(outliers):
                if is_outlier:
                    date = df.iloc[idx]["Date"].strftime("%Y-%m-%d")
                    cost = total_costs.iloc[idx]
                    z_score = outlier_z_scores[idx]
                    anomaly_type = "📈 HIGH" if cost > total_costs.mean() else "📉 LOW"

                    # Check if this is a monthly billing spike that we're aware of
                    is_known_spike = (
                        monthly_billing_stats is not None
                        and "HasMonthlyBillingSpike" in df.columns
                        and df.iloc[idx]["HasMonthlyBillingSpike"]
                    )

                    spike_note = " (known monthly billing)" if is_known_spike else ""

                    print(
                        f"{anomaly_type} {date}: ${cost:,.2f} "
                        f"(z-score: {z_score:.2f}){spike_note}"
                    )
                    anomalies.append(
                        {
                            "date": date,
                            "type": "total_cost",
                            "value": cost,
                            "z_score": z_score,
                            "severity": (
                                "high"
                                if z_score > HIGH_SEVERITY_THRESHOLD
                                else "medium"
                            ),
                            "is_monthly_billing": is_known_spike,
                        }
                    )

        # Check individual services for anomalies
        service_cols = self.get_service_columns(df)

        service_anomalies = 0
        for service_col in service_cols[:10]:  # Check top 10 services by volume
            service_name = service_col.replace("($)", "").strip()
            service_data = df[service_col]

            # Only check services with meaningful cost variations
            if (
                service_data.sum() < MIN_SERVICE_COST_THRESHOLD
                or service_data.std() < MIN_SERVICE_VARIANCE
            ):
                continue

            z_scores = np.abs(zscore(service_data))
            service_outliers = z_scores > SERVICE_ANOMALY_THRESHOLD

            if service_outliers.any():
                service_anomalies += service_outliers.sum()
                for idx, is_outlier in enumerate(service_outliers):
                    if is_outlier:
                        date = df.iloc[idx]["Date"].strftime("%Y-%m-%d")
                        cost = service_data.iloc[idx]
                        z_score = z_scores[idx]

                        anomalies.append(
                            {
                                "date": date,
                                "type": "service",
                                "service": service_name,
                                "value": cost,
                                "z_score": z_score,
                                "severity": (
                                    "high"
                                    if z_score > HIGH_SEVERITY_THRESHOLD
                                    else "medium"
                                ),
                            }
                        )

        if service_anomalies > 0:
            print(
                f"\nFound {service_anomalies} service-level anomalies (showing top 5):"
            )
            print("-" * 50)
            # Show top 5 service anomalies by z-score
            service_anom = [a for a in anomalies if a["type"] == "service"]
            service_anom.sort(key=lambda x: x["z_score"], reverse=True)

            for anom in service_anom[:5]:
                anomaly_type = (
                    "📈 SPIKE"
                    if anom["value"] > df[f"{anom['service']}($)"].mean()
                    else "📉 DROP"
                )
                print(
                    f"{anomaly_type} {anom['date']}: {anom['service']} = "
                    f"${anom['value']:.2f} (z-score: {anom['z_score']:.2f})"
                )

        if not anomalies:
            print("✅ No significant anomalies detected in cost patterns")

        return anomalies
