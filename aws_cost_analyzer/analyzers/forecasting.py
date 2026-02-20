"""
Cost forecasting and prediction analysis with model competition
"""

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from .base import BaseAnalyzer
from .forecast_accuracy import ForecastAccuracyTracker
from .forecast_models import (
    HoltWintersModel,
    PolynomialTrendModel,
    SeasonalDecompositionModel,
    WeightedMovingAverageModel,
)

# Constants
MIN_DAYS_FOR_FORECASTING = 7
DECEMBER_MONTH = 12
TOP_SERVICES_COUNT = 6
DEFAULT_HORIZON = 14


class ForecastingAnalyzer(BaseAnalyzer):
    """Handles cost forecasting and prediction with model competition"""

    def analyze(self, df):
        """Run cost forecasting"""
        return self.run_cost_forecasting(df)

    def _prepare_series(self, df, column="Total costs($)"):
        """Convert DataFrame column to a daily-frequency Series with DatetimeIndex"""
        series = df.set_index("Date")[column].sort_index()
        series = series.asfreq("D")
        series = series.ffill()
        return series

    def _get_all_models(self):
        """Return all available forecast models"""
        return [
            HoltWintersModel(),
            SeasonalDecompositionModel(),
            WeightedMovingAverageModel(),
            PolynomialTrendModel(),
        ]

    def _print_accuracy_table(self, all_metrics, best_name):
        """Print model accuracy comparison table"""
        if not all_metrics:
            return

        print("\nModel Accuracy Comparison (7-day backtest):")
        print(
            f"  {'Model':<28} {'MAPE':>8} {'RMSE':>10} {'MAE':>10} "
            f"{'Dir.Acc':>8} {'CI Cov':>8}"
        )
        print("  " + "-" * 74)

        for m in all_metrics:
            marker = " *" if m.model_name == best_name else "  "
            print(
                f"{marker}{m.model_name:<28} {m.mape:>7.1f}% "
                f"${m.rmse:>8.2f} ${m.mae:>8.2f} "
                f"{m.directional_accuracy:>6.0f}% {m.ci_coverage:>6.0f}%"
            )

        print(f"\n  * = selected model: {best_name}")

    def _forecast_service(self, df, service_col, horizon):
        """Forecast a single service, returns ForecastResult or None"""
        try:
            series = self._prepare_series(df, column=service_col)
            if series.sum() < self.config.min_service_cost_for_analysis:
                return None

            models = self._get_all_models()
            for model in models:
                result = model.fit_and_forecast(
                    series,
                    horizon=horizon,
                    confidence_level=self.config.forecast_confidence_level,
                )
                if result is not None:
                    return result
        except Exception:
            pass
        return None

    def run_cost_forecasting(self, df):
        """Implement cost forecasting using model competition"""
        if df is None or len(df) < MIN_DAYS_FOR_FORECASTING:
            return None

        self.print_section_header("COST FORECASTING ANALYSIS")

        horizon = getattr(self.config, "forecast_horizon", DEFAULT_HORIZON)

        # Prepare time series
        series = self._prepare_series(df)

        # Run model competition
        models = self._get_all_models()
        tracker = ForecastAccuracyTracker()
        best_model, all_metrics = tracker.select_best_model(models, series)

        print(f"Best forecasting model: {best_model.name}")
        self._print_accuracy_table(all_metrics, best_model.name)

        # Generate forecast with winning model
        forecast_result = best_model.fit_and_forecast(
            series,
            horizon=horizon,
            confidence_level=self.config.forecast_confidence_level,
        )

        # Fallback if best model fails on full data
        if forecast_result is None:
            for model in models:
                forecast_result = model.fit_and_forecast(
                    series,
                    horizon=horizon,
                    confidence_level=self.config.forecast_confidence_level,
                )
                if forecast_result is not None:
                    break

        if forecast_result is None:
            print("Warning: No model could produce a forecast")
            return {"best_model": best_model.name, "forecasts": {}}

        # Print forecasts at key horizons
        forecast_days = [1, 7, 14, 30]
        print("\nCost forecasts:")
        print("-" * 40)

        forecasts = {}
        for days in forecast_days:
            if days <= horizon:
                idx = days - 1
                value = forecast_result.forecast_values[idx]
                lower = forecast_result.lower_ci[idx]
                upper = forecast_result.upper_ci[idx]
                ci_range = (upper - lower) / 2
            else:
                # Extrapolate for 30-day using last forecast value
                value = float(forecast_result.forecast_values[-1])
                ci_range = forecast_result.residual_std * 1.96

            future_date = series.index[-1] + timedelta(days=days)
            print(
                f"{days:2d} days ({future_date.strftime('%Y-%m-%d')}): "
                f"${value:6.2f} +/- ${ci_range:.2f}"
            )
            forecasts[days] = value

        # Per-service forecasts
        service_cols = self.data_processor.get_service_columns(df)
        service_forecasts = {}

        if service_cols:
            service_totals = df[service_cols].sum().sort_values(ascending=False)
            top_services = service_totals.head(TOP_SERVICES_COUNT)

            print(f"\nPer-service forecasts ({horizon}-day):")
            print("-" * 50)

            for service_col in top_services.index:
                svc_result = self._forecast_service(df, service_col, horizon)
                service_name = service_col.replace("($)", "").strip()

                if svc_result is not None:
                    avg_forecast = float(np.mean(svc_result.forecast_values))
                    current_avg = float(df[service_col].iloc[-7:].mean())
                    change_pct = (
                        ((avg_forecast - current_avg) / max(current_avg, 0.01)) * 100
                    )
                    trend = "+" if change_pct > 0 else ""
                    print(
                        f"  {service_name:<30} "
                        f"${avg_forecast:>8.2f}/day ({trend}{change_pct:.1f}%)"
                    )
                    service_forecasts[service_name] = {
                        "forecast_values": svc_result.forecast_values.tolist(),
                        "forecast_dates": [
                            d.strftime("%Y-%m-%d") for d in svc_result.forecast_dates
                        ],
                        "lower_ci": svc_result.lower_ci.tolist(),
                        "upper_ci": svc_result.upper_ci.tolist(),
                        "model": svc_result.model_name,
                    }
                else:
                    print(f"  {service_name:<30} (insufficient data)")

        # Monthly projection
        current_month = df["Date"].max().strftime("%Y-%m")
        today = datetime.now(tz=timezone.utc).date()

        if (
            df["Date"].max().date().month == today.month
            and df["Date"].max().date().year == today.year
        ):
            try:
                if today.month < DECEMBER_MONTH:
                    days_in_month = (
                        today.replace(month=today.month + 1, day=1) - timedelta(days=1)
                    ).day
                else:
                    days_in_month = (
                        today.replace(year=today.year + 1, month=1, day=1)
                        - timedelta(days=1)
                    ).day

                days_remaining = days_in_month - df["Date"].max().date().day

                if days_remaining > 0:
                    # Use forecast series for projection
                    forecast_days_to_use = min(days_remaining, horizon)
                    daily_forecast = float(
                        np.mean(forecast_result.forecast_values[:forecast_days_to_use])
                    )

                    current_month_total = df[df["Month"] == current_month][
                        "Total costs($)"
                    ].sum()
                    projected_month_total = current_month_total + (
                        daily_forecast * days_remaining
                    )

                    print(f"\n{current_month} month projection:")
                    print(f"Current total: ${current_month_total:,.2f}")
                    print(f"Projected total: ${projected_month_total:,.2f}")
            except Exception:
                pass

        return {
            "best_model": best_model.name,
            "forecasts": forecasts,
            "forecast_series": {
                "dates": [
                    d.strftime("%Y-%m-%d") for d in forecast_result.forecast_dates
                ],
                "values": forecast_result.forecast_values.tolist(),
                "lower_ci": forecast_result.lower_ci.tolist(),
                "upper_ci": forecast_result.upper_ci.tolist(),
            },
            "service_forecasts": service_forecasts,
            "historical_dates": [
                d.strftime("%Y-%m-%d") for d in series.index
            ],
            "historical_values": series.values.tolist(),
            "accuracy_metrics": [
                {
                    "model": m.model_name,
                    "mape": m.mape,
                    "rmse": m.rmse,
                    "mae": m.mae,
                    "directional_accuracy": m.directional_accuracy,
                    "ci_coverage": m.ci_coverage,
                }
                for m in all_metrics
            ],
        }
