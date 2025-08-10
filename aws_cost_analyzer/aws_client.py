"""
AWS Cost Explorer client for fetching billing data
"""

import json
import os
import subprocess
from datetime import date, datetime, timedelta, timezone

import pandas as pd


class AWSClient:
    """Handles AWS CLI interactions and data fetching"""

    def __init__(self, config):
        self.config = config
        self.aws_profile = config.aws_profile

    def verify_aws_setup(self):
        """Verify AWS CLI setup and credentials"""
        print("🔍 Verifying AWS setup...")

        # Set AWS profile environment variable
        os.environ["AWS_PROFILE"] = self.aws_profile
        print(f"   Using AWS profile: {self.aws_profile}")

        # Check if AWS CLI is available
        try:
            subprocess.run(["aws", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ AWS CLI not found. Please install AWS CLI first.")
            return False

        # Test AWS credentials
        try:
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity"],
                check=True,
                capture_output=True,
                text=True,
            )
            identity_data = json.loads(result.stdout)
            arn = identity_data.get("Arn", "Unknown")
            print(f"✓ AWS credentials verified: {arn}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ AWS credential verification failed: {e}")
            print("   Please check:")
            print("   1. AWS CLI is configured")
            print(f"   2. Profile '{self.aws_profile}' exists")
            print("   3. Credentials are valid")
            return False
        except Exception as e:
            print(f"❌ Unexpected error verifying AWS setup: {e}")
            return False

    def fetch_cost_data(
        self, start_date=None, end_date=None, exclude_today=True, timestamp=None
    ):
        """
        Fetch cost data from AWS CLI using Cost Explorer API

        Args:
            start_date: Start date (YYYY-MM-DD) or None for auto (start of last month)
            end_date: End date (YYYY-MM-DD) or None for auto (today or yesterday)
            exclude_today: If True, exclude today's incomplete data
            timestamp: Timestamp for filename generation

        Returns:
            tuple: (DataFrame, output_file_path) or (None, None) on error
        """
        print("=" * 60)
        print("FETCHING DATA FROM AWS CLI")
        print("=" * 60)

        # Calculate date range if not provided
        today = datetime.now(tz=timezone.utc).date()
        end_date_calc = today - timedelta(days=1) if exclude_today else today

        if start_date is None:
            # Start of last month
            if today.month == 1:
                start_date_calc = date(today.year - 1, 12, 1)
            else:
                start_date_calc = date(today.year, today.month - 1, 1)
        else:
            start_date_calc = (
                datetime.strptime(start_date, "%Y-%m-%d")
                .replace(tzinfo=timezone.utc)
                .date()
            )

        if end_date is None:
            # end_date_calc is already set above
            pass
        else:
            end_date_calc = (
                datetime.strptime(end_date, "%Y-%m-%d")
                .replace(tzinfo=timezone.utc)
                .date()
            )

        print(f"Fetching costs from {start_date_calc} to {end_date_calc}")

        # Prepare AWS CLI command
        cmd = [
            "aws",
            "ce",
            "get-cost-and-usage",
            "--time-period",
            f"Start={start_date_calc},End={end_date_calc + timedelta(days=1)}",
            "--granularity",
            "DAILY",
            "--group-by",
            "Type=DIMENSION,Key=SERVICE",
            "--metrics",
            "BlendedCost",
        ]

        try:
            print("Running AWS CLI command...")
            print(" ".join(cmd))

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            cost_data = json.loads(result.stdout)

            print("✓ Successfully fetched data from AWS")

            # Convert to DataFrame
            cost_data_df = self._convert_aws_data_to_dataframe(cost_data)

            # Save raw data with timestamp
            if timestamp is None:
                timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")

            output_file = (
                self.config.data_dir
                / f"aws_costs_{timestamp}_{start_date_calc}_to_{end_date_calc}.csv"
            )
            cost_data_df.to_csv(output_file, index=False)
            print(f"✓ Data saved to: {output_file}")

            return cost_data_df, output_file

        except subprocess.CalledProcessError as e:
            print(f"✗ AWS CLI error: {e}")
            print(f"Error output: {e.stderr}")
            return None, None
        except json.JSONDecodeError as e:
            print(f"✗ JSON parsing error: {e}")
            return None, None
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            return None, None

    def _convert_aws_data_to_dataframe(self, aws_data):
        """Convert AWS Cost Explorer JSON response to DataFrame similar to CSV format"""
        rows = []

        # Get all unique services across all time periods
        all_services = set()
        for result in aws_data["ResultsByTime"]:
            for group in result.get("Groups", []):
                service_name = group["Keys"][0]
                all_services.add(service_name)

        # Sort services for consistent column order
        all_services = sorted(all_services)

        # Process each day
        for result in aws_data["ResultsByTime"]:
            date_str = result["TimePeriod"]["Start"]
            row = {"Service": date_str}

            # Initialize all services to 0
            for service in all_services:
                row[f"{service}($)"] = 0.0

            # Fill in actual costs
            daily_total = 0.0
            for group in result.get("Groups", []):
                service_name = group["Keys"][0]
                amount = float(group["Metrics"]["BlendedCost"]["Amount"])
                row[f"{service_name}($)"] = amount
                daily_total += amount

            row["Total costs($)"] = daily_total
            rows.append(row)

        cost_data_df = pd.DataFrame(rows)

        # Convert Service column to datetime for consistency
        cost_data_df["Service"] = pd.to_datetime(cost_data_df["Service"]).dt.strftime(
            "%Y-%m-%d"
        )

        return cost_data_df

    def load_from_csv(self, filepath):
        """
        Load data from existing CSV file

        Args:
            filepath: Path to CSV file

        Returns:
            DataFrame or None on error
        """
        print("=" * 60)
        print(f"LOADING DATA FROM CSV: {filepath}")
        print("=" * 60)

        try:
            data_df = pd.read_csv(filepath)
            print(f"✓ Successfully loaded {len(data_df)} rows from CSV")
            return data_df
        except Exception as e:
            print(f"✗ Error loading CSV: {e}")
            return None
