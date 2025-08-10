"""
Data processing and preparation for AWS cost analysis
"""

import pandas as pd

# Constants
WEEKEND_START_DAY = 5  # Saturday is day 5 (0=Monday)
MIN_PATTERN_DETECTION_DAYS = 10


class DataProcessor:
    """Handles data cleaning and preparation for analysis"""

    def __init__(self, config):
        self.config = config
        self.monthly_billing_stats = None

    def prepare_data(self, df):
        """
        Clean and prepare data for analysis

        Args:
            df: Raw DataFrame from AWS or CSV

        Returns:
            bool: True if successful, False otherwise
        """
        if df is None:
            print("✗ No data provided")
            return None

        print("\n" + "=" * 60)
        print("PREPARING DATA FOR ANALYSIS")
        print("=" * 60)

        # Remove service total row if it exists
        processed_df = df[df["Service"] != "Service total"].copy()

        # Convert Service column to datetime
        processed_df["Date"] = pd.to_datetime(processed_df["Service"])
        processed_df = processed_df.drop("Service", axis=1)

        # Move Date to first column
        cols = ["Date"] + [col for col in processed_df.columns if col != "Date"]
        processed_df = processed_df[cols]

        # Convert all cost columns to numeric
        cost_columns = [col for col in processed_df.columns if col != "Date"]
        for col in cost_columns:
            processed_df[col] = pd.to_numeric(
                processed_df[col], errors="coerce"
            ).fillna(0)

        # Add derived columns
        processed_df["DayOfWeek"] = processed_df["Date"].dt.day_name()
        processed_df["DayNum"] = processed_df["Date"].dt.dayofweek
        processed_df["Month"] = processed_df["Date"].dt.strftime("%Y-%m")
        processed_df["Day"] = processed_df["Date"].dt.day
        processed_df["IsWeekend"] = (
            processed_df["Date"].dt.dayofweek >= WEEKEND_START_DAY
        )
        processed_df["IsFirstOfMonth"] = processed_df["Date"].dt.day == 1

        # Flag first-of-month anomalies (savings plans, free tier consumption, etc.)
        self._detect_monthly_billing_patterns(processed_df)

        print(
            f"✓ Data prepared: {len(processed_df)} days from "
            f"{processed_df['Date'].min().date()} to "
            f"{processed_df['Date'].max().date()}"
        )
        return processed_df

    def _detect_monthly_billing_patterns(self, df):
        """Detect and flag first-of-month billing anomalies"""
        if len(df) < MIN_PATTERN_DETECTION_DAYS:  # Need sufficient data
            return

        # Calculate baseline cost excluding first days of month
        non_first_days = df[~df["IsFirstOfMonth"]]["Total costs($)"]
        if len(non_first_days) == 0:
            return

        baseline_mean = non_first_days.mean()
        baseline_std = non_first_days.std()

        # Check first days vs baseline
        first_days = df[df["IsFirstOfMonth"]]

        if len(first_days) == 0:
            return

        # Flag first days that are significantly higher than baseline
        threshold = baseline_mean + (
            self.config.monthly_billing_threshold * baseline_std
        )

        df["HasMonthlyBillingSpike"] = df["IsFirstOfMonth"] & (
            df["Total costs($)"] > threshold
        )

        # Store stats for reporting
        self.monthly_billing_stats = {
            "baseline_mean": baseline_mean,
            "baseline_std": baseline_std,
            "first_day_mean": first_days["Total costs($)"].mean(),
            "first_day_spikes": df["HasMonthlyBillingSpike"].sum(),
            "threshold": threshold,
        }

    def get_service_columns(self, df):
        """Get list of service cost columns from DataFrame"""
        return [
            col for col in df.columns if col.endswith("($)") and col != "Total costs($)"
        ]

    def get_monthly_billing_stats(self):
        """Get monthly billing pattern statistics"""
        return self.monthly_billing_stats
