"""
Main orchestrator for AWS Cost Analysis Suite
"""

from datetime import datetime, timezone
from pathlib import Path

from .analyzers import (
    AnomalyDetector,
    BasicAnalyzer,
    ForecastingAnalyzer,
    RecommendationEngine,
    TrendingAnalyzer,
)
from .aws_client import AWSClient
from .config import Config
from .data_processor import DataProcessor
from .interactive_visualizer import InteractiveVisualizer
from .visualizer import Visualizer

# Constants
MIN_MONTHS_FOR_COMPARISON = 2
NEGATIVE_TREND_THRESHOLD = -2


class AWSCostAnalyzer:
    """Main orchestrator for AWS cost analysis"""

    def __init__(self, data_source=None, aws_profile=None, output_format="both"):
        """
        Initialize the AWS Cost Analyzer

        Args:
            data_source: Path to CSV file, or None to fetch from AWS CLI
            aws_profile: AWS profile to use (defaults to default or
                AWS_PROFILE env var)
            output_format: "png", "html", or "both" (default "both")
        """
        self.data_source = data_source
        self.df = None
        self.timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.session_id = f"aws_analysis_{self.timestamp}"
        self.output_format = output_format

        # Initialize configuration
        self.config = Config()
        if aws_profile:
            self.config.aws_profile = aws_profile

        # Initialize components
        self.aws_client = AWSClient(self.config)
        self.data_processor = DataProcessor(self.config)
        self.visualizer = Visualizer(self.config, self.data_processor)
        self.interactive_visualizer = InteractiveVisualizer(
            self.config, self.data_processor
        )

        # Initialize analyzers
        self.basic_analyzer = BasicAnalyzer(self.config, self.data_processor)
        self.trending_analyzer = TrendingAnalyzer(self.config, self.data_processor)
        self.anomaly_detector = AnomalyDetector(self.config, self.data_processor)
        self.forecasting_analyzer = ForecastingAnalyzer(
            self.config, self.data_processor
        )
        self.recommendation_engine = RecommendationEngine(
            self.config, self.data_processor
        )

    def verify_aws_setup(self):
        """Verify AWS CLI setup and credentials"""
        return self.aws_client.verify_aws_setup()

    def fetch_from_aws_cli(self, start_date=None, end_date=None, exclude_today=True):
        """
        Fetch cost data from AWS CLI using Cost Explorer API
        """
        df, output_file = self.aws_client.fetch_cost_data(
            start_date, end_date, exclude_today, self.timestamp
        )
        if df is not None:
            self.df = df
        return output_file

    def load_from_csv(self, filepath):
        """Load data from existing CSV file"""
        loaded_df = self.aws_client.load_from_csv(filepath)
        if loaded_df is not None:
            self.df = loaded_df
            return True
        return False

    def prepare_data(self):
        """Clean and prepare data for analysis"""
        if self.df is None:
            print("✗ No data loaded")
            return False

        prepared_df = self.data_processor.prepare_data(self.df)
        if prepared_df is not None:
            self.df = prepared_df
            return True
        return False

    def generate_summary_report(self):
        """Generate a comprehensive summary report"""
        if self.df is None:
            return None

        print("\n" + "=" * 60)
        print("EXECUTIVE SUMMARY")
        print("=" * 60)

        # Basic stats
        total_days = len(self.df)
        date_range = f"{self.df['Date'].min().date()} to {self.df['Date'].max().date()}"
        total_cost = self.df["Total costs($)"].sum()
        daily_avg = self.df["Total costs($)"].mean()

        print(f"📊 Analysis Period: {date_range} ({total_days} days)")
        print(f"💰 Total Costs: ${total_cost:,.2f}")
        print(f"📈 Daily Average: ${daily_avg:.2f}")

        # Monthly comparison
        months = sorted(self.df["Month"].unique())
        if len(months) >= MIN_MONTHS_FOR_COMPARISON:
            prev_month_data = self.df[self.df["Month"] == months[-2]]
            curr_month_data = self.df[self.df["Month"] == months[-1]]

            prev_avg = prev_month_data["Total costs($)"].mean()
            curr_avg = curr_month_data["Total costs($)"].mean()
            change_pct = ((curr_avg / prev_avg) - 1) * 100

            trend_emoji = (
                "📈"
                if change_pct > 0
                else "📉" if change_pct < NEGATIVE_TREND_THRESHOLD else "➡️"
            )
            print(
                f"{trend_emoji} Month-over-Month: {change_pct:+.1f}% "
                f"({months[-2]} vs {months[-1]})"
            )

        # Day of week insights
        dow_avg = self.df.groupby("DayOfWeek")["Total costs($)"].mean()
        most_expensive_dow = dow_avg.idxmax()
        least_expensive_dow = dow_avg.idxmin()

        print(
            f"📅 Most expensive day: {most_expensive_dow} "
            f"(${dow_avg[most_expensive_dow]:.2f})"
        )
        print(
            f"📅 Least expensive day: {least_expensive_dow} "
            f"(${dow_avg[least_expensive_dow]:.2f})"
        )

        # Top service
        service_cols = self.data_processor.get_service_columns(self.df)
        if service_cols:
            top_service = self.df[service_cols].sum().idxmax()
            top_service_cost = self.df[service_cols].sum().max()
            top_service_name = top_service.replace("($)", "").strip()
            print(f"🏆 Top service: {top_service_name} (${top_service_cost:,.2f})")

        return {
            "total_days": total_days,
            "date_range": date_range,
            "total_cost": total_cost,
            "daily_avg": daily_avg,
        }

    def create_visualizations(self, forecast_results=None):
        """Create comprehensive visualizations based on output_format"""
        png_path = None
        html_path = None

        if self.output_format in ("png", "both"):
            png_path = self.visualizer.create_visualizations(
                self.df, self.timestamp
            )

        if self.output_format in ("html", "both"):
            html_path = self.interactive_visualizer.create_visualizations(
                self.df, self.timestamp, forecast_results=forecast_results
            )

        return png_path or html_path

    def run_full_analysis(self):
        """Run complete analysis suite with enhanced trending and forecasting"""
        print("🚀 AWS COST ANALYSIS SUITE")
        print("=" * 60)

        if not self.prepare_data():
            return False

        # Run all analyses
        self.generate_summary_report()

        # Basic analyses
        self.basic_analyzer.analyze(self.df)

        # Enhanced analyses
        trending_results = self.trending_analyzer.analyze(self.df)
        anomalies = self.anomaly_detector.analyze(self.df)
        forecast_results = self.forecasting_analyzer.analyze(self.df)
        recommendations = self.recommendation_engine.analyze(self.df)

        # Create visualizations with forecast data
        viz = self.create_visualizations(forecast_results=forecast_results)

        print("\n" + "=" * 60)
        print("✅ ANALYSIS COMPLETE")
        print("=" * 60)
        print(f"🕐 Session: {self.session_id}")
        print(f"📁 Outputs saved to: {self.config.outputs_dir}")
        print("Generated files:")
        if viz:
            print(f"  📊 Dashboard: {Path(viz).name}")
            if self.output_format in ("png", "both"):
                print("  📊 Latest PNG: aws_cost_dashboard_latest.png")
            if self.output_format in ("html", "both"):
                print("  📊 Latest HTML: aws_cost_dashboard_latest.html")
        print(
            "💡 Tip: To save this analysis, run: "
            "./cost-analysis [options] > my_analysis.txt"
        )

        # Summary of key insights
        if trending_results.get("trending") or anomalies or recommendations:
            print("\n🎯 KEY INSIGHTS SUMMARY:")

            trending = trending_results.get("trending", {})
            if trending:
                top_trend = max(trending.items(), key=lambda x: abs(x[1]["abs_change"]))
                print(
                    f"  • Biggest cost trend: {top_trend[0]} "
                    f"({top_trend[1]['abs_change']:+.2f}$/day)"
                )

            if anomalies:
                high_severity = [a for a in anomalies if a["severity"] == "high"]
                if high_severity:
                    print(
                        f"  • {len(high_severity)} high-severity cost "
                        f"anomalies detected"
                    )

            if recommendations:
                print(
                    f"  • {len(recommendations)} optimization recommendations generated"
                )

        return True

    def run_basic_analysis(self):
        """Run basic analysis suite (original functionality)"""
        print("🚀 AWS COST ANALYSIS SUITE - BASIC MODE")
        print("=" * 60)

        if not self.prepare_data():
            return False

        # Run basic analyses only
        self.generate_summary_report()
        self.basic_analyzer.analyze(self.df)

        print("\n" + "=" * 60)
        print("✅ BASIC ANALYSIS COMPLETE")
        print("=" * 60)
        print(f"🕐 Session: {self.session_id}")
        print(f"📁 Outputs saved to: {self.config.outputs_dir}")
        print(
            "💡 Tip: To save this analysis, run: "
            "./cost-analysis --basic [options] > my_analysis.txt"
        )

        return True
