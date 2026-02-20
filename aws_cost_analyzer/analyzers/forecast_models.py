"""
Forecast model implementations for cost prediction
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class ForecastResult:
    """Standardized output for all forecast models"""

    model_name: str
    forecast_values: np.ndarray
    forecast_dates: pd.DatetimeIndex
    lower_ci: np.ndarray
    upper_ci: np.ndarray
    fitted_values: np.ndarray
    residuals: np.ndarray
    residual_std: float
    confidence_level: float = 0.95
    metadata: dict = field(default_factory=dict)


class HoltWintersModel:
    """Holt-Winters exponential smoothing with optional weekly seasonality"""

    name = "Holt-Winters"
    min_data_points = 14

    def fit_and_forecast(self, series, horizon, confidence_level=0.95):
        """Fit Holt-Winters and forecast.

        Args:
            series: pd.Series with DatetimeIndex
            horizon: number of periods to forecast
            confidence_level: confidence level for intervals

        Returns:
            ForecastResult or None on failure
        """
        if len(series) < self.min_data_points:
            return None

        try:
            from scipy.stats import norm
            from statsmodels.tsa.holtwinters import ExponentialSmoothing

            seasonal_period = 7 if len(series) >= 14 else None
            seasonal = "add" if seasonal_period else None

            model = ExponentialSmoothing(
                series,
                trend="add",
                seasonal=seasonal,
                seasonal_periods=seasonal_period,
                initialization_method="estimated",
            )
            fit = model.fit(optimized=True)

            forecast_values = fit.forecast(horizon)
            fitted_values = fit.fittedvalues
            residuals = series - fitted_values
            residual_std = float(residuals.std())

            # Widening confidence intervals
            z = norm.ppf(1 - (1 - confidence_level) / 2)
            steps = np.arange(1, horizon + 1)
            ci_width = residual_std * z * np.sqrt(steps)

            forecast_dates = pd.date_range(
                start=series.index[-1] + pd.Timedelta(days=1),
                periods=horizon,
                freq="D",
            )

            return ForecastResult(
                model_name=self.name,
                forecast_values=forecast_values.values,
                forecast_dates=forecast_dates,
                lower_ci=forecast_values.values - ci_width,
                upper_ci=forecast_values.values + ci_width,
                fitted_values=fitted_values.values,
                residuals=residuals.values,
                residual_std=residual_std,
                confidence_level=confidence_level,
                metadata={"seasonal_period": seasonal_period},
            )
        except Exception:
            return None


class SeasonalDecompositionModel:
    """Classical seasonal decomposition with trend extrapolation"""

    name = "Seasonal Decomposition"
    min_data_points = 21

    def fit_and_forecast(self, series, horizon, confidence_level=0.95):
        if len(series) < self.min_data_points:
            return None

        try:
            from scipy.stats import norm
            from statsmodels.tsa.seasonal import seasonal_decompose

            period = 7
            result = seasonal_decompose(series, model="additive", period=period)

            trend = result.trend.dropna()
            seasonal = result.seasonal

            # Extrapolate trend with linear regression
            x = np.arange(len(trend))
            coeffs = np.polyfit(x, trend.values, 1)

            # Forecast trend
            future_x = np.arange(len(trend), len(trend) + horizon)
            trend_forecast = np.polyval(coeffs, future_x)

            # Repeat seasonal pattern
            seasonal_cycle = seasonal.values[-period:]
            seasonal_forecast = np.array(
                [seasonal_cycle[i % period] for i in range(horizon)]
            )

            forecast_values = trend_forecast + seasonal_forecast

            # Fitted values: trend + seasonal (aligned to original)
            fitted_values = np.full(len(series), np.nan)
            trend_vals = result.trend.values
            seasonal_vals = result.seasonal.values
            for i in range(len(series)):
                if not np.isnan(trend_vals[i]):
                    fitted_values[i] = trend_vals[i] + seasonal_vals[i]

            fitted_series = pd.Series(fitted_values, index=series.index)
            residuals = series - fitted_series
            residual_std = float(residuals.dropna().std())

            z = norm.ppf(1 - (1 - confidence_level) / 2)
            steps = np.arange(1, horizon + 1)
            ci_width = residual_std * z * np.sqrt(steps)

            forecast_dates = pd.date_range(
                start=series.index[-1] + pd.Timedelta(days=1),
                periods=horizon,
                freq="D",
            )

            return ForecastResult(
                model_name=self.name,
                forecast_values=forecast_values,
                forecast_dates=forecast_dates,
                lower_ci=forecast_values - ci_width,
                upper_ci=forecast_values + ci_width,
                fitted_values=fitted_values,
                residuals=residuals.values,
                residual_std=residual_std,
                confidence_level=confidence_level,
                metadata={"period": period, "trend_slope": coeffs[0]},
            )
        except Exception:
            return None


class WeightedMovingAverageModel:
    """Exponentially weighted moving average forecast"""

    name = "Weighted Moving Average"
    min_data_points = 7

    def fit_and_forecast(self, series, horizon, confidence_level=0.95):
        if len(series) < self.min_data_points:
            return None

        try:
            from scipy.stats import norm

            window = min(14, len(series))
            recent = series.iloc[-window:]

            # Exponentially decaying weights
            weights = np.exp(np.linspace(-1, 0, window))
            weights /= weights.sum()

            weighted_avg = float(np.average(recent.values, weights=weights))
            forecast_values = np.full(horizon, weighted_avg)

            # Fitted values: rolling weighted average
            fitted_values = np.full(len(series), np.nan)
            for i in range(window, len(series) + 1):
                segment = series.iloc[i - window : i]
                w = np.exp(np.linspace(-1, 0, len(segment)))
                w /= w.sum()
                fitted_values[i - 1] = np.average(segment.values, weights=w)

            fitted_series = pd.Series(fitted_values, index=series.index)
            residuals = series - fitted_series
            residual_std = float(residuals.dropna().std())

            z = norm.ppf(1 - (1 - confidence_level) / 2)
            steps = np.arange(1, horizon + 1)
            ci_width = residual_std * z * np.sqrt(steps)

            forecast_dates = pd.date_range(
                start=series.index[-1] + pd.Timedelta(days=1),
                periods=horizon,
                freq="D",
            )

            return ForecastResult(
                model_name=self.name,
                forecast_values=forecast_values,
                forecast_dates=forecast_dates,
                lower_ci=forecast_values - ci_width,
                upper_ci=forecast_values + ci_width,
                fitted_values=fitted_values,
                residuals=residuals.values,
                residual_std=residual_std,
                confidence_level=confidence_level,
                metadata={"window": window, "weighted_avg": weighted_avg},
            )
        except Exception:
            return None


class PolynomialTrendModel:
    """Linear/quadratic polynomial trend (wraps existing approach)"""

    name = "Polynomial Trend"
    min_data_points = 7

    def fit_and_forecast(self, series, horizon, confidence_level=0.95):
        if len(series) < self.min_data_points:
            return None

        try:
            from scipy.stats import norm

            x = np.arange(len(series))
            degree = 2 if len(series) >= 10 else 1

            coeffs = np.polyfit(x, series.values, degree)
            fitted_values = np.polyval(coeffs, x)

            future_x = np.arange(len(series), len(series) + horizon)
            forecast_values = np.polyval(coeffs, future_x)

            residuals = series.values - fitted_values
            residual_std = float(np.std(residuals))

            z = norm.ppf(1 - (1 - confidence_level) / 2)
            steps = np.arange(1, horizon + 1)
            ci_width = residual_std * z * np.sqrt(steps)

            forecast_dates = pd.date_range(
                start=series.index[-1] + pd.Timedelta(days=1),
                periods=horizon,
                freq="D",
            )

            return ForecastResult(
                model_name=self.name,
                forecast_values=forecast_values,
                forecast_dates=forecast_dates,
                lower_ci=forecast_values - ci_width,
                upper_ci=forecast_values + ci_width,
                fitted_values=fitted_values,
                residuals=residuals,
                residual_std=residual_std,
                confidence_level=confidence_level,
                metadata={"degree": degree, "coefficients": coeffs.tolist()},
            )
        except Exception:
            return None
