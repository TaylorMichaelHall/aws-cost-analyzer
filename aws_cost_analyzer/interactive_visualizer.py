"""
Interactive Plotly dashboard for AWS cost analysis
"""

import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import zscore

from .utils import clean_service_name

warnings.filterwarnings("ignore")

# Constants
MIN_SERVICE_COST = 0.5
WEEKEND_COLOR_THRESHOLD = 5
OUTLIER_Z_SCORE_THRESHOLD = 2.5
MIN_DATA_POINTS_FOR_COMPARISON = 4
TOP_SERVICES_PIE = 6
TOP_SERVICES_SPARKLINES = 6


class InteractiveVisualizer:
    """Handles interactive Plotly dashboard creation"""

    def __init__(self, config, data_processor):
        self.config = config
        self.data_processor = data_processor

    def create_visualizations(self, df, timestamp, forecast_results=None):
        """Create interactive Plotly dashboard.

        Args:
            df: Prepared DataFrame with cost data
            timestamp: Timestamp string for file naming
            forecast_results: Optional dict from ForecastingAnalyzer.analyze()

        Returns:
            str path to HTML file, or None on failure
        """
        if df is None:
            return None

        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except ImportError:
            print("Warning: plotly not installed, skipping interactive dashboard")
            return None

        print("\nCreating interactive dashboard...")

        try:
            fig = make_subplots(
                rows=4,
                cols=2,
                subplot_titles=(
                    "Daily Cost Timeline",
                    "Day-of-Week Patterns",
                    "Cost Trend + Anomalies",
                    "Cost Forecast",
                    "Service Cost Changes",
                    "Service Breakdown",
                    "Cost Distribution",
                    "Per-Service Sparklines",
                ),
                vertical_spacing=0.07,
                horizontal_spacing=0.08,
                specs=[
                    [{}, {}],
                    [{}, {}],
                    [{}, {"type": "domain"}],
                    [{}, {}],
                ],
            )

            # Panel 1: Daily Cost Timeline (R1C1)
            self._add_daily_timeline(fig, df, row=1, col=1)

            # Panel 2: Day-of-Week Patterns (R1C2)
            self._add_dow_patterns(fig, df, row=1, col=2)

            # Panel 3: Cost Trend + Anomalies (R2C1)
            self._add_trend_anomalies(fig, df, row=2, col=1)

            # Panel 4: Cost Forecast (R2C2)
            self._add_forecast(fig, df, forecast_results, row=2, col=2)

            # Panel 5: Service Cost Changes (R3C1)
            self._add_service_changes(fig, df, row=3, col=1)

            # Panel 6: Service Breakdown Pie (R3C2)
            self._add_service_pie(fig, df, row=3, col=2)

            # Panel 7: Cost Distribution (R4C1)
            self._add_distribution(fig, df, row=4, col=1)

            # Panel 8: Per-Service Sparklines (R4C2)
            self._add_service_sparklines(fig, df, forecast_results, row=4, col=2)

            # Layout
            analysis_date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            fig.update_layout(
                title=dict(
                    text=f"AWS Cost Analysis Dashboard - {analysis_date}",
                    font=dict(size=20),
                ),
                template="plotly_white",
                height=1600,
                width=1400,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.02),
            )

            # Save
            output_file = (
                self.config.outputs_dir / f"aws_cost_dashboard_{timestamp}.html"
            )
            fig.write_html(
                str(output_file), include_plotlyjs="cdn", full_html=True
            )
            print(f"  Interactive dashboard saved to: {output_file}")

            latest_file = self.config.outputs_dir / "aws_cost_dashboard_latest.html"
            fig.write_html(
                str(latest_file), include_plotlyjs="cdn", full_html=True
            )
            print(f"  Latest interactive dashboard: {latest_file}")

            return str(output_file)

        except Exception as e:
            print(f"  Interactive visualization error: {e}")
            return None

    def _add_daily_timeline(self, fig, df, row, col):
        import plotly.graph_objects as go

        months = sorted(df["Month"].unique())
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

        for i, month in enumerate(months):
            month_data = df[df["Month"] == month]
            fig.add_trace(
                go.Scatter(
                    x=month_data["Day"],
                    y=month_data["Total costs($)"],
                    mode="lines+markers",
                    name=month,
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=5),
                    hovertemplate="Day %{x}<br>Cost: $%{y:.2f}<extra>%{fullData.name}</extra>",
                    legendgroup="timeline",
                ),
                row=row,
                col=col,
            )

        fig.update_xaxes(title_text="Day of Month", row=row, col=col)
        fig.update_yaxes(title_text="Daily Cost ($)", row=row, col=col)

    def _add_dow_patterns(self, fig, df, row, col):
        import plotly.graph_objects as go

        dow_data = (
            df.groupby(["DayOfWeek", "DayNum"])["Total costs($)"]
            .mean()
            .reset_index()
            .sort_values("DayNum")
        )

        colors = [
            "lightblue" if d < WEEKEND_COLOR_THRESHOLD else "#FF6B6B"
            for d in dow_data["DayNum"]
        ]

        fig.add_trace(
            go.Bar(
                x=dow_data["DayOfWeek"],
                y=dow_data["Total costs($)"],
                marker_color=colors,
                hovertemplate="%{x}<br>Avg Cost: $%{y:.2f}<extra></extra>",
                showlegend=False,
            ),
            row=row,
            col=col,
        )

        fig.update_xaxes(title_text="Day of Week", row=row, col=col)
        fig.update_yaxes(title_text="Average Daily Cost ($)", row=row, col=col)

    def _add_trend_anomalies(self, fig, df, row, col):
        import plotly.graph_objects as go

        # Cost line
        fig.add_trace(
            go.Scatter(
                x=df["Date"],
                y=df["Total costs($)"],
                mode="lines",
                name="Daily Cost",
                line=dict(color="#1f77b4", width=2),
                hovertemplate="%{x|%Y-%m-%d}<br>Cost: $%{y:.2f}<extra></extra>",
                legendgroup="trend",
                showlegend=False,
            ),
            row=row,
            col=col,
        )

        # Trend line
        x_numeric = np.arange(len(df))
        trend_coeffs = np.polyfit(x_numeric, df["Total costs($)"], 1)
        trend_line = np.polyval(trend_coeffs, x_numeric)

        fig.add_trace(
            go.Scatter(
                x=df["Date"],
                y=trend_line,
                mode="lines",
                name=f"Trend: ${trend_coeffs[0]:+.2f}/day",
                line=dict(color="red", width=2, dash="dash"),
                hovertemplate="%{x|%Y-%m-%d}<br>Trend: $%{y:.2f}<extra></extra>",
                legendgroup="trend",
            ),
            row=row,
            col=col,
        )

        # Anomalies
        total_costs = df["Total costs($)"]
        z_scores = np.abs(zscore(total_costs))
        outliers = z_scores > OUTLIER_Z_SCORE_THRESHOLD

        if outliers.any():
            outlier_df = df[outliers]
            outlier_z = z_scores[outliers]

            fig.add_trace(
                go.Scatter(
                    x=outlier_df["Date"],
                    y=outlier_df["Total costs($)"],
                    mode="markers",
                    name="Anomalies",
                    marker=dict(color="red", size=10, symbol="diamond"),
                    customdata=outlier_z,
                    hovertemplate=(
                        "%{x|%Y-%m-%d}<br>Cost: $%{y:.2f}"
                        "<br>Z-score: %{customdata:.1f}<extra></extra>"
                    ),
                    legendgroup="trend",
                ),
                row=row,
                col=col,
            )

        fig.update_xaxes(title_text="Date", row=row, col=col)
        fig.update_yaxes(title_text="Daily Cost ($)", row=row, col=col)

    def _add_forecast(self, fig, df, forecast_results, row, col):
        import plotly.graph_objects as go

        # Historical data (last 30 days for context)
        recent = df.tail(30)
        fig.add_trace(
            go.Scatter(
                x=recent["Date"],
                y=recent["Total costs($)"],
                mode="lines",
                name="Historical",
                line=dict(color="#1f77b4", width=2),
                hovertemplate="%{x|%Y-%m-%d}<br>Cost: $%{y:.2f}<extra></extra>",
                legendgroup="forecast",
                showlegend=False,
            ),
            row=row,
            col=col,
        )

        if forecast_results and "forecast_series" in forecast_results:
            fs = forecast_results["forecast_series"]
            dates = pd.to_datetime(fs["dates"])
            values = np.array(fs["values"])
            lower = np.array(fs["lower_ci"])
            upper = np.array(fs["upper_ci"])

            # Forecast line
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=values,
                    mode="lines",
                    name=f"Forecast ({forecast_results.get('best_model', 'Model')})",
                    line=dict(color="#ff7f0e", width=2, dash="dash"),
                    hovertemplate="%{x|%Y-%m-%d}<br>Predicted: $%{y:.2f}<extra></extra>",
                    legendgroup="forecast",
                ),
                row=row,
                col=col,
            )

            # Confidence interval band
            fig.add_trace(
                go.Scatter(
                    x=pd.concat([pd.Series(dates), pd.Series(dates[::-1])]),
                    y=np.concatenate([upper, lower[::-1]]),
                    fill="toself",
                    fillcolor="rgba(255,127,14,0.15)",
                    line=dict(color="rgba(255,127,14,0)"),
                    name="95% CI",
                    hovertemplate=(
                        "%{x|%Y-%m-%d}<br>CI: $%{y:.2f}<extra></extra>"
                    ),
                    legendgroup="forecast",
                    showlegend=False,
                ),
                row=row,
                col=col,
            )
        else:
            # No forecast data - show placeholder text via annotation
            fig.add_annotation(
                text="Insufficient data for forecasting",
                xref=f"x{self._axis_num(row, col)}",
                yref=f"y{self._axis_num(row, col)}",
                x=0.5,
                y=0.5,
                xanchor="center",
                yanchor="middle",
                showarrow=False,
                font=dict(size=14, color="gray"),
            )

        fig.update_xaxes(title_text="Date", row=row, col=col)
        fig.update_yaxes(title_text="Cost ($)", row=row, col=col)

    def _add_service_changes(self, fig, df, row, col):
        import plotly.graph_objects as go

        service_cols = self.data_processor.get_service_columns(df)

        if not service_cols or len(df) < MIN_DATA_POINTS_FOR_COMPARISON:
            return

        mid_point = len(df) // 2
        earlier = df.iloc[:mid_point]
        recent = df.iloc[mid_point:]

        changes = []
        for sc in service_cols:
            service_name = sc.replace("($)", "").strip()
            earlier_avg = earlier[sc].mean()
            recent_avg = recent[sc].mean()

            if earlier_avg > MIN_SERVICE_COST or recent_avg > MIN_SERVICE_COST:
                dollar_change = recent_avg - earlier_avg
                pct_change = (
                    (recent_avg - earlier_avg) / max(earlier_avg, 0.01)
                ) * 100
                changes.append(
                    {
                        "service": service_name,
                        "dollar_change": dollar_change,
                        "pct_change": pct_change,
                    }
                )

        changes.sort(key=lambda x: abs(x["dollar_change"]), reverse=True)
        top = changes[:8]

        if not top:
            return

        services = [clean_service_name(c["service"]) for c in top]
        dollar_vals = [c["dollar_change"] for c in top]
        pct_vals = [c["pct_change"] for c in top]
        colors = ["#FF4444" if v > 0 else "#44AA44" for v in dollar_vals]

        fig.add_trace(
            go.Bar(
                y=services,
                x=dollar_vals,
                orientation="h",
                marker_color=colors,
                customdata=pct_vals,
                hovertemplate=(
                    "%{y}<br>Change: $%{x:.2f}/day"
                    "<br>%{customdata:+.1f}%<extra></extra>"
                ),
                showlegend=False,
            ),
            row=row,
            col=col,
        )

        fig.update_xaxes(title_text="Daily Cost Change ($)", row=row, col=col)

    def _add_service_pie(self, fig, df, row, col):
        import plotly.graph_objects as go

        service_cols = self.data_processor.get_service_columns(df)
        if not service_cols:
            return

        service_totals = df[service_cols].sum().sort_values(ascending=False)
        top = service_totals.head(TOP_SERVICES_PIE)
        others = service_totals.iloc[TOP_SERVICES_PIE:].sum()

        labels = [
            clean_service_name(s.replace("($)", "").strip(), max_length=12)
            for s in top.index
        ]
        values = top.values.tolist()

        if others > 0:
            labels.append("Others")
            values.append(others)

        pie_colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1",
            "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8",
        ]

        fig.add_trace(
            go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=pie_colors[: len(labels)]),
                hovertemplate="%{label}<br>$%{value:,.2f}<br>%{percent}<extra></extra>",
                textinfo="label+percent",
                textfont_size=10,
            ),
            row=row,
            col=col,
        )

    def _add_distribution(self, fig, df, row, col):
        import plotly.graph_objects as go

        costs = df["Total costs($)"]

        fig.add_trace(
            go.Histogram(
                x=costs,
                nbinsx=20,
                marker_color="skyblue",
                marker_line_color="black",
                marker_line_width=1,
                hovertemplate="Range: $%{x:.0f}<br>Count: %{y}<extra></extra>",
                showlegend=False,
            ),
            row=row,
            col=col,
        )

        # Mean and median as vertical line traces (avoids add_vline bug with domain subplots)
        y_max = costs.max() * 0.9
        fig.add_trace(
            go.Scatter(
                x=[costs.mean(), costs.mean()],
                y=[0, y_max],
                mode="lines",
                line=dict(color="red", width=2, dash="dash"),
                name=f"Mean: ${costs.mean():.0f}",
                legendgroup="dist",
                showlegend=True,
            ),
            row=row,
            col=col,
        )
        fig.add_trace(
            go.Scatter(
                x=[costs.median(), costs.median()],
                y=[0, y_max],
                mode="lines",
                line=dict(color="green", width=2, dash="dash"),
                name=f"Median: ${costs.median():.0f}",
                legendgroup="dist",
                showlegend=True,
            ),
            row=row,
            col=col,
        )

        fig.update_xaxes(title_text="Daily Cost ($)", row=row, col=col)
        fig.update_yaxes(title_text="Frequency", row=row, col=col)

    def _add_service_sparklines(self, fig, df, forecast_results, row, col):
        import plotly.graph_objects as go

        service_cols = self.data_processor.get_service_columns(df)
        if not service_cols:
            return

        service_totals = df[service_cols].sum().sort_values(ascending=False)
        top = service_totals.head(TOP_SERVICES_SPARKLINES)

        sparkline_colors = [
            "#1f77b4", "#ff7f0e", "#2ca02c",
            "#d62728", "#9467bd", "#8c564b",
        ]

        for i, sc in enumerate(top.index):
            service_name = clean_service_name(
                sc.replace("($)", "").strip(), max_length=20
            )
            color = sparkline_colors[i % len(sparkline_colors)]

            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df[sc],
                    mode="lines",
                    name=service_name,
                    line=dict(color=color, width=1.5),
                    hovertemplate=(
                        f"{service_name}<br>"
                        "%{x|%Y-%m-%d}<br>$%{y:.2f}<extra></extra>"
                    ),
                    legendgroup="sparklines",
                    showlegend=True,
                ),
                row=row,
                col=col,
            )

            # Add forecast overlay if available
            if (
                forecast_results
                and "service_forecasts" in forecast_results
            ):
                svc_name_raw = sc.replace("($)", "").strip()
                svc_fc = forecast_results["service_forecasts"].get(svc_name_raw)
                if svc_fc:
                    fc_dates = pd.to_datetime(svc_fc["forecast_dates"])
                    fc_values = svc_fc["forecast_values"]
                    fig.add_trace(
                        go.Scatter(
                            x=fc_dates,
                            y=fc_values,
                            mode="lines",
                            line=dict(color=color, width=1.5, dash="dot"),
                            hovertemplate=(
                                f"{service_name} (forecast)<br>"
                                "%{x|%Y-%m-%d}<br>$%{y:.2f}<extra></extra>"
                            ),
                            legendgroup="sparklines",
                            showlegend=False,
                        ),
                        row=row,
                        col=col,
                    )

        fig.update_xaxes(title_text="Date", row=row, col=col)
        fig.update_yaxes(title_text="Cost ($)", row=row, col=col)

    @staticmethod
    def _axis_num(row, col):
        """Convert row/col to plotly axis number (1-indexed, left-to-right, top-to-bottom)"""
        idx = (row - 1) * 2 + col
        return "" if idx == 1 else str(idx)
