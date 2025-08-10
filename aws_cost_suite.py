#!/usr/bin/env python3
"""
AWS Cost Analysis Suite
Fetches AWS cost data via CLI and runs comprehensive analysis with advanced trending

This is the new modular entry point that uses the refactored package structure.
The original functionality is preserved but now organized into logical modules.

USAGE EXAMPLES:
  ./aws_cost_suite.py --fetch --months 3        # Last 3 months with full analysis
  ./aws_cost_suite.py --csv data/costs.csv      # Analyze existing CSV
  ./aws_cost_suite.py --fetch --basic          # Original functionality only
  ./aws_cost_suite.py --fetch --days 30 --no-viz # Skip visualizations

  # Or use the cost-analysis wrapper:
  ./cost-analysis --fetch --months 3
"""

import sys

from aws_cost_analyzer.cli import main

if __name__ == "__main__":
    sys.exit(main())
