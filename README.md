# AWS Cost Analyzer

A Python tool that analyzes AWS costs with features AWS Cost Explorer doesn't have: trend detection, anomaly alerts, forecasting, and optimization recommendations.

## What it does

- **Trending Analysis**: Find which services are growing/shrinking fastest
- **Anomaly Detection**: Flag unusual cost spikes automatically  
- **Cost Forecasting**: Predict future costs with confidence intervals
- **Smart Recommendations**: Get specific optimization suggestions
- **Enhanced Visualizations**: 6-panel dashboard with trend highlighting

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

That's it! The tool auto-installs dependencies and generates a complete cost analysis with visualizations.

## Usage Examples

```bash
# Last 30 days
./cost-analysis --fetch --days 30

# Custom date range
./cost-analysis --fetch --start-date 2024-01-01 --end-date 2024-01-31

# Use specific AWS profile
./cost-analysis --fetch --aws-profile production --months 2

# Analyze existing CSV
./cost-analysis --csv data/my_costs.csv
```

## Configuration

Copy `.env.example` to `.env` to customize:

```bash
AWS_PROFILE=default
ANOMALY_THRESHOLD=2.5    # Lower = more sensitive
MIN_SERVICE_COST=1.0     # Ignore tiny services
```

## Output

- **Console**: Complete analysis with insights and recommendations
- **Dashboard**: `aws_cost_dashboard_latest.png` with 6 visualization panels
- **Data**: Raw CSV files saved to `data/` directory

## Requirements

- Python 3.8+
- AWS CLI configured with Cost Explorer permissions
- UV package manager (auto-installed by wrapper script)

## License

MIT - see LICENSE file