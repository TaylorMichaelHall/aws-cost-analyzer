"""
Configuration management for AWS Cost Analyzer
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration settings for AWS Cost Analyzer"""

    def __init__(self):
        # AWS Configuration
        self.aws_profile = os.getenv("AWS_PROFILE", "default")

        # Directory Structure
        self.base_dir = Path.cwd()
        self.data_dir = self.base_dir / os.getenv("DATA_DIR", "data")
        self.outputs_dir = self.base_dir / os.getenv("OUTPUT_DIR", "outputs")
        self.scripts_dir = self.base_dir / "scripts"

        # Analysis Parameters
        self.anomaly_threshold = float(os.getenv("ANOMALY_THRESHOLD", "2.5"))
        self.monthly_billing_threshold = float(
            os.getenv("MONTHLY_BILLING_THRESHOLD", "2.0")
        )
        self.min_service_cost_for_analysis = float(
            os.getenv("MIN_SERVICE_COST_FOR_ANALYSIS", "1.0")
        )
        self.min_service_cost_for_trending = float(
            os.getenv("MIN_SERVICE_COST_FOR_TRENDING", "10.0")
        )

        # Visualization Settings
        self.visualization_dpi = int(os.getenv("VISUALIZATION_DPI", "300"))

        # Forecasting Settings
        self.forecast_confidence_level = float(
            os.getenv("FORECAST_CONFIDENCE_LEVEL", "0.95")
        )
        self.forecast_horizon = int(os.getenv("FORECAST_HORIZON", "14"))
        self.forecast_seasonal_period = int(os.getenv("FORECAST_SEASONAL_PERIOD", "7"))

        # Create directories if they don't exist
        self._create_directories()

    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        for dir_path in [self.data_dir, self.outputs_dir, self.scripts_dir]:
            dir_path.mkdir(exist_ok=True)

    def to_dict(self):
        """Convert configuration to dictionary"""
        return {
            "anomaly_threshold": self.anomaly_threshold,
            "monthly_billing_threshold": self.monthly_billing_threshold,
            "min_service_cost_for_analysis": self.min_service_cost_for_analysis,
            "min_service_cost_for_trending": self.min_service_cost_for_trending,
            "visualization_dpi": self.visualization_dpi,
            "forecast_confidence_level": self.forecast_confidence_level,
        }
