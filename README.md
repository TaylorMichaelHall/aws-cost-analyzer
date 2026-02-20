# AWS Cost Analyzer

A Python tool that analyzes AWS costs with features AWS Cost Explorer doesn't have: trend detection, anomaly alerts, production-grade forecasting, and optimization recommendations.

## What it does

- **Trending Analysis**: Find which services are growing/shrinking fastest, with acceleration tracking and service correlations
- **Anomaly Detection**: Flag unusual cost spikes automatically, with monthly billing pattern awareness
- **Cost Forecasting**: Compete four models (Holt-Winters, seasonal decomposition, weighted moving average, polynomial trend) and pick the best via walk-forward backtesting. Per-service forecasts for your top services
- **Smart Recommendations**: Get specific optimization suggestions based on detected patterns
- **Interactive Dashboard**: 8-panel Plotly HTML dashboard with hover tooltips, legend toggles, and forecast confidence bands
- **Static Dashboard**: 6-panel matplotlib PNG for embedding in reports or Slack

## Quick Start

1. **Install uv** (if needed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Configure AWS CLI** with your profile:
   ```bash
   aws configure --profile your-profile-name
   ```

3. **Run analysis**:
   ```bash
   ./cost-analysis --fetch --months 3
   ```

That's it. The tool auto-installs dependencies and generates a complete cost analysis with visualizations.

## Usage Examples

```bash
# Last 30 days
./cost-analysis --fetch --days 30

# Custom date range
./cost-analysis --fetch --start-date 2025-01-01 --end-date 2025-01-31

# Use specific AWS profile
./cost-analysis --fetch --aws-profile myprofile --months 2

# Analyze existing CSV (from AWS Cost Explorer export)
./cost-analysis --csv data/my_costs.csv

# Interactive HTML dashboard only
./cost-analysis --csv data/my_costs.csv --format html

# Static PNG only
./cost-analysis --csv data/my_costs.csv --format png

# Both formats (default)
./cost-analysis --csv data/my_costs.csv --format both

# Basic mode (skip enhanced analysis)
./cost-analysis --csv data/my_costs.csv --basic
```

## Output

- **Console**: Full analysis with model accuracy table, per-service forecasts, anomalies, and recommendations
- **Interactive dashboard**: `outputs/aws_cost_dashboard_latest.html` — 8 panels with hover, zoom, and toggle
- **Static dashboard**: `outputs/aws_cost_dashboard_latest.png` — 6 panels for reports
- **Data**: Raw CSV files saved to `data/`

### Dashboard Panels (Interactive)

| Panel | Description |
|-------|-------------|
| Daily Cost Timeline | Per-month line chart with range slider |
| Day-of-Week Patterns | Weekday vs weekend bar chart |
| Cost Trend + Anomalies | Trend line with anomaly markers and z-scores |
| Cost Forecast | Historical + forecast with 95% confidence band |
| Service Cost Changes | Horizontal bar chart showing recent vs earlier period |
| Service Breakdown | Pie chart with drill-down hover |
| Cost Distribution | Histogram with mean/median lines |
| Per-Service Sparklines | Top 6 services with forecast overlay |

### Forecasting Models

The analyzer runs four models and selects the best via 7-day walk-forward backtesting:

| Model | Min Data | Best For |
|-------|----------|----------|
| Holt-Winters | 14 days | Data with weekly seasonality |
| Seasonal Decomposition | 21 days | Strong repeating patterns |
| Weighted Moving Average | 7 days | Stable, low-variance costs |
| Polynomial Trend | 7 days | Clear linear/quadratic trends |

The console output shows a comparison table with MAPE, RMSE, MAE, directional accuracy, and CI coverage for each model.

## Configuration

Copy `.env.example` to `.env` to customize:

```bash
cp .env.example .env
```

Available settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_PROFILE` | `default` | AWS CLI profile to use |
| `ANOMALY_THRESHOLD` | `2.5` | Z-score threshold for anomaly detection (lower = more sensitive) |
| `MIN_SERVICE_COST_FOR_ANALYSIS` | `1.0` | Ignore services below this daily cost |
| `MIN_SERVICE_COST_FOR_TRENDING` | `10.0` | Minimum total cost for trending analysis |
| `FORECAST_CONFIDENCE_LEVEL` | `0.95` | Confidence level for forecast intervals |
| `FORECAST_HORIZON` | `14` | Number of days to forecast ahead |
| `FORECAST_SEASONAL_PERIOD` | `7` | Seasonal period in days (7 = weekly) |
| `VISUALIZATION_DPI` | `300` | DPI for static PNG dashboard |

## Project Structure

```
aws-cost-analyzer/
├── aws_cost_analyzer/
│   ├── cli.py                  # Command-line interface
│   ├── main.py                 # Orchestrator
│   ├── config.py               # Configuration management
│   ├── aws_client.py           # AWS API integration
│   ├── data_processor.py       # Data cleaning and preparation
│   ├── visualizer.py           # Static matplotlib dashboard
│   ├── interactive_visualizer.py  # Interactive Plotly dashboard
│   ├── utils.py                # Shared utilities
│   └── analyzers/
│       ├── base.py             # Base analyzer class
│       ├── basic.py            # Basic cost analysis
│       ├── trending.py         # Service trend detection
│       ├── anomaly.py          # Anomaly detection
│       ├── forecasting.py      # Forecast orchestration
│       ├── forecast_models.py  # Model implementations
│       ├── forecast_accuracy.py # Walk-forward backtesting
│       └── recommendations.py  # Optimization suggestions
├── cost-analysis               # Wrapper script
├── aws_cost_suite.py           # Entry point
├── pyproject.toml              # Dependencies and project config
├── data/                       # CSV data files (gitignored)
└── outputs/                    # Generated dashboards (gitignored)
```

## Requirements

- Python 3.9+
- AWS CLI configured with Cost Explorer permissions (`ce:GetCostAndUsage`)
- [uv](https://docs.astral.sh/uv/) package manager

## License

MIT - see LICENSE file
