#!/usr/bin/env python3
"""
AWS Cost Analysis Suite - Status Overview
Shows current state and recent analyses
"""

from datetime import datetime, timezone
from pathlib import Path


def show_banner():
    print("🏦 AWS COST ANALYSIS SUITE - STATUS")
    print("=" * 50)


def check_directory_structure():
    """Check and display directory structure"""
    print("\n📁 DIRECTORY STRUCTURE:")

    directories = {
        "data/": "CSV files and raw data",
        "outputs/": "Reports, charts, and analysis results",
        "scripts/": "Individual analysis scripts",
    }

    for dir_name, description in directories.items():
        dir_path = Path(dir_name)
        status = "✓" if dir_path.exists() else "✗"

        if dir_path.exists():
            file_count = len(list(dir_path.glob("*")))
            print(f"  {status} {dir_name:<12} {description} ({file_count} files)")
        else:
            print(f"  {status} {dir_name:<12} {description} (missing)")


def show_recent_outputs():
    """Show recent analysis outputs"""
    outputs_dir = Path("outputs")

    if not outputs_dir.exists():
        print("\n📊 RECENT OUTPUTS: None (outputs directory not found)")
        return

    # Get all output files
    png_files = list(outputs_dir.glob("aws_cost_dashboard_*.png"))
    txt_files = list(outputs_dir.glob("aws_cost_report_*.txt"))

    if not png_files and not txt_files:
        print("\n📊 RECENT OUTPUTS: None")
        return

    print(f"\n📊 RECENT OUTPUTS ({len(png_files + txt_files)} files):")

    # Combine and sort by modification time
    all_files = png_files + txt_files
    all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    for i, file in enumerate(all_files[:10], 1):  # Show latest 10
        mtime = datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc)
        size_kb = file.stat().st_size / 1024

        if file.suffix == ".png":
            icon = "📊"
        elif file.suffix == ".txt":
            icon = "📄"
        else:
            icon = "📄"

        print(f"  {i:2d}. {icon} {file.name}")
        print(f"      📅 {mtime.strftime('%Y-%m-%d %H:%M:%S')} ({size_kb:.1f} KB)")


def show_available_data():
    """Show available data files"""
    data_dir = Path("data")

    if not data_dir.exists():
        print("\n📋 AVAILABLE DATA: None (data directory not found)")
        return

    csv_files = list(data_dir.glob("*.csv"))

    if not csv_files:
        print("\n📋 AVAILABLE DATA: None")
        print("  💡 Add CSV files to data/ directory for analysis")
        return

    print(f"\n📋 AVAILABLE DATA ({len(csv_files)} files):")

    csv_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    for i, file in enumerate(csv_files, 1):
        mtime = datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc)
        size_kb = file.stat().st_size / 1024

        print(f"  {i}. 📄 {file.name}")
        print(f"     📅 {mtime.strftime('%Y-%m-%d %H:%M:%S')} ({size_kb:.1f} KB)")


def show_quick_actions():
    """Show quick action commands"""
    print("\n🚀 QUICK ACTIONS:")
    print("  🎯 RECOMMENDED USAGE:        ./cost-analysis --fetch --months 3")
    print("     (fetches data and runs complete enhanced analysis)")
    print()
    print("  1. Full analysis:            ./cost-analysis --fetch --months 3")
    print("  2. Analyze existing data:    ./cost-analysis --csv data/your_file.csv")
    print("  3. Basic analysis only:      ./cost-analysis --fetch --basic --months 2")
    print("  4. Recent data (30 days):    ./cost-analysis --fetch --days 30")
    print("  5. View this status:         python3 status.py")


def check_requirements():
    """Check if required packages are available"""
    print("\n🔧 DEPENDENCIES:")

    required_packages = ["pandas", "matplotlib", "numpy", "scipy", "boto3", "dotenv"]

    import importlib

    missing_packages = []
    available_packages = []
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:  # noqa: PERF203
            missing_packages.append(package)
        else:
            available_packages.append(package)

    for package in available_packages:
        print(f"  ✓ {package}")
    for package in missing_packages:
        print(f"  ✗ {package} (pip install {package})")


def show_latest_session_info():
    """Show information about the latest analysis session"""
    outputs_dir = Path("outputs")

    if not outputs_dir.exists():
        return

    # Find latest report file
    txt_files = list(outputs_dir.glob("aws_cost_report_*.txt"))

    if not txt_files:
        return

    latest_report = max(txt_files, key=lambda x: x.stat().st_mtime)

    print("\n📈 LATEST ANALYSIS:")
    print(f"  📄 Report: {latest_report.name}")

    # Extract timestamp from filename
    timestamp_str = latest_report.stem.replace("aws_cost_report_", "")
    try:
        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").replace(
            tzinfo=timezone.utc
        )
        print(f"  🕐 Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    except ValueError:
        mtime = datetime.fromtimestamp(latest_report.stat().st_mtime, tz=timezone.utc)
        print(f"  🕐 Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

    # Try to extract key info from report
    try:
        with open(latest_report) as f:
            content = f.read()

        lines = content.split("\n")
        for line in lines:
            if "Analysis Period:" in line:
                print(f"  📅 {line.strip()}")
            elif "Total Costs:" in line:
                print(f"  💰 {line.strip()}")
            elif "Daily Average:" in line:
                print(f"  📊 {line.strip()}")
                break
    except Exception:
        pass


def main():
    """Main status display"""
    show_banner()
    check_directory_structure()
    show_available_data()
    show_recent_outputs()
    show_latest_session_info()
    check_requirements()
    show_quick_actions()

    print(
        f"\n🕐 Status checked at: "
        f"{datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
    )


if __name__ == "__main__":
    main()
