"""
Base analyzer class with common functionality
"""

from abc import ABC, abstractmethod


class BaseAnalyzer(ABC):
    """Base class for all analyzers"""

    def __init__(self, config, data_processor):
        self.config = config
        self.data_processor = data_processor

    @abstractmethod
    def analyze(self, df):
        """
        Perform analysis on the DataFrame

        Args:
            df: Prepared DataFrame with cost data

        Returns:
            dict: Analysis results
        """

    def get_service_columns(self, df):
        """Get service cost columns"""
        return self.data_processor.get_service_columns(df)

    def print_section_header(self, title):
        """Print a formatted section header"""
        print("\n" + "=" * 60)
        print(title)
        print("=" * 60)
