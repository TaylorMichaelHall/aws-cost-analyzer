"""
Forecast accuracy tracking and model selection via walk-forward backtesting
"""

from dataclasses import dataclass

import numpy as np


BACKTEST_HOLDOUT_DAYS = 7


@dataclass
class AccuracyMetrics:
    """Forecast accuracy metrics for a single model"""

    model_name: str
    mape: float  # Mean Absolute Percentage Error
    rmse: float  # Root Mean Squared Error
    mae: float  # Mean Absolute Error
    directional_accuracy: float  # % of correct direction predictions
    ci_coverage: float  # % of actuals within confidence interval


class ForecastAccuracyTracker:
    """Walk-forward backtesting for forecast model evaluation"""

    def evaluate_model(self, model, series):
        """Evaluate a model using walk-forward backtesting.

        Holds out the last BACKTEST_HOLDOUT_DAYS days, trains on the rest,
        forecasts the holdout period, and compares to actuals.

        Returns:
            AccuracyMetrics or None if evaluation fails
        """
        holdout = BACKTEST_HOLDOUT_DAYS
        if len(series) < holdout + model.min_data_points:
            return None

        train = series.iloc[:-holdout]
        actual = series.iloc[-holdout:].values

        result = model.fit_and_forecast(
            train, horizon=holdout, confidence_level=0.95
        )
        if result is None:
            return None

        predicted = result.forecast_values[:holdout]
        lower = result.lower_ci[:holdout]
        upper = result.upper_ci[:holdout]

        # MAPE (avoid division by zero)
        nonzero = actual != 0
        if nonzero.any():
            mape = float(
                np.mean(np.abs((actual[nonzero] - predicted[nonzero]) / actual[nonzero])) * 100
            )
        else:
            mape = float("inf")

        # RMSE
        rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))

        # MAE
        mae = float(np.mean(np.abs(actual - predicted)))

        # Directional accuracy
        if len(actual) > 1:
            actual_dir = np.diff(actual) >= 0
            predicted_dir = np.diff(predicted) >= 0
            directional_accuracy = float(np.mean(actual_dir == predicted_dir) * 100)
        else:
            directional_accuracy = 0.0

        # CI coverage
        within_ci = (actual >= lower) & (actual <= upper)
        ci_coverage = float(np.mean(within_ci) * 100)

        return AccuracyMetrics(
            model_name=model.name,
            mape=mape,
            rmse=rmse,
            mae=mae,
            directional_accuracy=directional_accuracy,
            ci_coverage=ci_coverage,
        )

    def select_best_model(self, models, series):
        """Run all models through backtesting and select the best one.

        Args:
            models: list of model instances
            series: pd.Series with DatetimeIndex

        Returns:
            (best_model, all_metrics) sorted by MAPE
        """
        results = []
        for model in models:
            metrics = self.evaluate_model(model, series)
            if metrics is not None:
                results.append((model, metrics))

        if not results:
            # Fallback: return first model that can fit
            for model in models:
                if len(series) >= model.min_data_points:
                    return model, []
            return models[-1], []

        # Sort by MAPE (lower is better)
        results.sort(key=lambda x: x[1].mape)

        best_model = results[0][0]
        all_metrics = [r[1] for r in results]

        return best_model, all_metrics
