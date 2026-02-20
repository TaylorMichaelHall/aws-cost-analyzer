"""
Command Line Interface for AWS Cost Analyzer
"""

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .main import AWSCostAnalyzer


def calculate_date_range(args):  # noqa: PLR0912
    """Calculate start and end dates based on arguments"""
    today = datetime.now(tz=timezone.utc).date()

    # Handle end date
    if args.end_date:
        end_date = (
            datetime.strptime(args.end_date, "%Y-%m-%d")
            .replace(tzinfo=timezone.utc)
            .date()
        )
    elif args.include_today:
        end_date = today
    else:
        end_date = today - timedelta(days=1)

    # Handle start date based on various options
    if args.start_date:
        start_date = (
            datetime.strptime(args.start_date, "%Y-%m-%d")
            .replace(tzinfo=timezone.utc)
            .date()
        )
    elif args.current_month:
        start_date = date(today.year, today.month, 1)
        end_date = today if args.include_today else today - timedelta(days=1)
    elif args.last_month:
        if today.month == 1:
            start_date = date(today.year - 1, 12, 1)
            end_date = date(today.year, 1, 1) - timedelta(days=1)
        else:
            start_date = date(today.year, today.month - 1, 1)
            end_date = date(today.year, today.month, 1) - timedelta(days=1)
    elif args.ytd:
        start_date = date(today.year, 1, 1)
        end_date = today if args.include_today else today - timedelta(days=1)
    elif args.days:
        start_date = end_date - timedelta(days=args.days - 1)
    elif args.weeks:
        start_date = end_date - timedelta(weeks=args.weeks)
    elif args.months:
        # Calculate months back
        year = end_date.year
        month = end_date.month - args.months
        while month <= 0:
            month += 12
            year -= 1
        start_date = date(year, month, 1)
    # Default: start of last month
    elif today.month == 1:
        start_date = date(today.year - 1, 12, 1)
    else:
        start_date = date(today.year, today.month - 1, 1)

    return start_date, end_date


def main():  # noqa: PLR0911,PLR0912,PLR0915
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description=(
            "AWS Cost Analysis Suite - Find cost trends and "
            "anomalies that AWS Cost Explorer misses"
        )
    )
    parser.add_argument("--csv", type=str, help="Path to existing CSV file")
    parser.add_argument("--fetch", action="store_true", help="Fetch data from AWS CLI")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--include-today",
        action="store_true",
        help="Include today (incomplete) in data",
    )
    parser.add_argument(
        "--days", type=int, help="Number of days back from end date (e.g., --days 30)"
    )
    parser.add_argument(
        "--weeks", type=int, help="Number of weeks back from end date (e.g., --weeks 4)"
    )
    parser.add_argument(
        "--months",
        type=int,
        help="Number of months back from end date (e.g., --months 2)",
    )
    parser.add_argument(
        "--current-month", action="store_true", help="Fetch current month only"
    )
    parser.add_argument(
        "--last-month", action="store_true", help="Fetch last month only"
    )
    parser.add_argument("--ytd", action="store_true", help="Fetch year-to-date")
    parser.add_argument(
        "--aws-profile",
        type=str,
        help="AWS profile to use (default: default or AWS_PROFILE env var)",
    )

    # Enhanced analysis options
    parser.add_argument(
        "--basic",
        action="store_true",
        help="Run only basic analysis (skip enhanced trending features)",
    )
    parser.add_argument(
        "--no-viz", action="store_true", help="Skip visualization generation"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["png", "html", "both"],
        default="both",
        help="Output format for dashboards (default: both)",
    )

    args = parser.parse_args()

    # Print banner
    print("🏦 AWS COST ANALYSIS SUITE")
    print("=" * 60)
    if not args.basic:
        print(
            "🚀 Enhanced features: Trending • Anomalies • Forecasting • Recommendations"
        )
        print("=" * 60)

    analyzer = AWSCostAnalyzer(
        aws_profile=args.aws_profile, output_format=args.format
    )

    if args.fetch:
        # Verify AWS setup before proceeding
        if not analyzer.verify_aws_setup():
            print("❌ AWS setup verification failed")
            return 1
        # Calculate date range based on arguments
        start_date, end_date = calculate_date_range(args)

        print(f"📅 Date range: {start_date} to {end_date}")

        # Fetch from AWS CLI
        csv_file = analyzer.fetch_from_aws_cli(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            exclude_today=False,  # We've already handled this in calculate_date_range
        )
        if csv_file is None:
            print("❌ Failed to fetch data from AWS CLI")
            return 1
    elif args.csv:
        # Load from CSV
        if not analyzer.load_from_csv(args.csv):
            print("❌ Failed to load CSV file")
            return 1
    else:
        # Try to load default CSV file from data directory
        data_dir = Path("data")
        if data_dir.exists():
            csv_files = list(data_dir.glob("*.csv"))
            if csv_files:
                # Use the most recent CSV file
                latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
                print(f"Using most recent CSV: {latest_csv}")
                if not analyzer.load_from_csv(str(latest_csv)):
                    print("❌ Failed to load CSV file")
                    return 1
            else:
                print("❌ No CSV files found in data/ directory")
                return 1
        else:
            print("❌ No data source specified. Use --csv or --fetch")
            print("Or put CSV files in data/ directory")
            return 1

    # Run analysis
    if args.basic:
        success = analyzer.run_basic_analysis()
        if not args.no_viz:
            analyzer.create_visualizations()
    else:
        success = analyzer.run_full_analysis()

    if success:
        print("🎉 Analysis completed successfully!")
        return 0
    print("❌ Analysis failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
