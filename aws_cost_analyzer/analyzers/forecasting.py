"""
Cost forecasting and prediction analysis
"""

from datetime import datetime, timedelta, timezone

import numpy as np

from .base import BaseAnalyzer

# Constants
MIN_DAYS_FOR_FORECASTING = 7  # Minimum days of data needed for forecasting
MIN_DAYS_FOR_QUADRATIC = 10  # Minimum days needed for quadratic trend
DECEMBER_MONTH = 12


class ForecastingAnalyzer(BaseAnalyzer):
    """Handles cost forecasting and prediction"""

    def analyze(self, df):
        """Run cost forecasting"""
        return self.run_cost_forecasting(df)

    def run_cost_forecasting(self, df):
        """Implement cost forecasting using trend analysis"""
        if df is None or len(df) < MIN_DAYS_FOR_FORECASTING:
            return None

        self.print_section_header("COST FORECASTING ANALYSIS")

        total_costs = df["Total costs($)"]
        dates = df["Date"]

        # Convert dates to numeric for regression
        date_numeric = np.arange(len(dates))

        # Fit different models
        models = {}

        # Linear trend
        linear_coeffs = np.polyfit(date_numeric, total_costs, 1)
        models["linear"] = {
            "coeffs": linear_coeffs,
            "name": "Linear Trend",
            "r_squared": np.corrcoef(
                total_costs, np.polyval(linear_coeffs, date_numeric)
            )[0, 1]
            ** 2,
        }

        # Quadratic trend (for acceleration/deceleration)
        if len(df) >= MIN_DAYS_FOR_QUADRATIC:
            quad_coeffs = np.polyfit(date_numeric, total_costs, 2)
            models["quadratic"] = {
                "coeffs": quad_coeffs,
                "name": "Quadratic Trend",
                "r_squared": np.corrcoef(
                    total_costs, np.polyval(quad_coeffs, date_numeric)
                )[0, 1]
                ** 2,
            }

        # Moving average trend
        window = min(7, len(total_costs) // 3)
        ma_trend = total_costs.rolling(window=window).mean()
        recent_ma = ma_trend.dropna().iloc[-3:].mean()  # Last 3 days of MA

        # Choose best model based on R²
        best_model = max(models.items(), key=lambda x: x[1]["r_squared"])

        print(
            f"Best forecasting model: {best_model[1]['name']} "
            f"(R² = {best_model[1]['r_squared']:.3f})"
        )

        # Generate forecasts
        forecast_days = [1, 7, 14, 30]  # 1 day, 1 week, 2 weeks, 1 month

        print("\nCost forecasts:")
        print("-" * 40)

        forecasts = {}
        for days in forecast_days:
            future_date_numeric = len(dates) + days - 1

            if best_model[0] == "linear" or best_model[0] == "quadratic":
                forecast = np.polyval(best_model[1]["coeffs"], future_date_numeric)
            else:
                # Fallback to moving average
                forecast = recent_ma

            # Also show confidence range based on recent volatility
            recent_std = total_costs.iloc[-min(14, len(total_costs)) :].std()
            confidence_range = recent_std * 1.96  # 95% confidence interval

            future_date = dates.iloc[-1] + timedelta(days=days)

            print(
                f"{days:2d} days ({future_date.strftime('%Y-%m-%d')}): "
                f"${forecast:6.2f} ± ${confidence_range:.2f}"
            )

            forecasts[days] = forecast

        # Monthly projection if we're in an incomplete month
        current_month = dates.max().strftime("%Y-%m")
        today = datetime.now(tz=timezone.utc).date()

        if (
            dates.max().date().month == today.month
            and dates.max().date().year == today.year
        ):
            days_in_month = (
                today.replace(month=today.month + 1, day=1)
                if today.month < DECEMBER_MONTH
                else today.replace(year=today.year + 1, month=1, day=1)
                - timedelta(days=1)
            ).day
            days_remaining = days_in_month - dates.max().date().day

            if days_remaining > 0:
                month_end_forecast = np.polyval(
                    best_model[1]["coeffs"], len(dates) + days_remaining - 1
                )
                current_month_total = total_costs[df["Month"] == current_month].sum()
                projected_month_total = current_month_total + (
                    month_end_forecast * days_remaining
                )

                print(f"\n{current_month} month projection:")
                print(f"Current total: ${current_month_total:,.2f}")
                print(f"Projected total: ${projected_month_total:,.2f}")

        return {
            "best_model": best_model[1]["name"],
            "r_squared": best_model[1]["r_squared"],
            "forecasts": forecasts,
        }
