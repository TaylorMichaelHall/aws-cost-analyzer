"""
AWS Cost Analysis Suite

A comprehensive AWS cost analysis tool that provides:
- Enhanced trending analysis
- Anomaly detection
- Cost forecasting
- Growth rate analysis
- Service correlations
- Efficiency recommendations
"""

from .config import Config
from .main import AWSCostAnalyzer

__version__ = "2.0.0"
__all__ = ["AWSCostAnalyzer", "Config"]
