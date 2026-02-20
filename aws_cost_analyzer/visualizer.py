"""
Visualization and dashboard generation for AWS cost analysis
"""

import warnings
from datetime import datetime, timezone

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import zscore

from .utils import clean_service_name

warnings.filterwarnings("ignore")

# Constants
MIN_SERVICE_COST = 0.5
WEEKEND_COLOR_THRESHOLD = 5  # Saturday starts at day 5
OUTLIER_Z_SCORE_THRESHOLD = 2.5
MIN_DATA_POINTS_FOR_COMPARISON = 4


class Visualizer:
    """Handles visualization and dashboard creation"""

    def __init__(self, config, data_processor):
        self.config = config
        self.data_processor = data_processor

    def create_visualizations(self, df, timestamp):  # noqa: PLR0912,PLR0915
        """Create comprehensive visualizations"""
        if df is None:
            return None

        print("\n" + "=" * 60)
        print("CREATING VISUALIZATIONS")
        print("=" * 60)

        try:
            plt.style.use("default")
            # Set strict figure size to prevent auto-expansion
            fig, axes = plt.subplots(2, 3, figsize=(20, 12), constrained_layout=False)
            # Prevent matplotlib from auto-adjusting figure size
            fig.set_size_inches(20, 12, forward=False)

            # Add timestamp to title
            analysis_date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            fig.suptitle(
                f"AWS Cost Analysis Dashboard - {analysis_date}",
                fontsize=16,
                fontweight="bold",
            )

            # 1. Daily timeline
            ax1 = axes[0, 0]
            months = df["Month"].unique()
            colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

            for i, month in enumerate(sorted(months)):
                month_data = df[df["Month"] == month]
                ax1.plot(
                    month_data["Day"],
                    month_data["Total costs($)"],
                    "o-",
                    label=month,
                    linewidth=2,
                    markersize=4,
                    color=colors[i % len(colors)],
                )

            ax1.set_xlabel("Day of Month")
            ax1.set_ylabel("Daily Cost ($)")
            ax1.set_title("Daily Costs by Month")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 2. Day of week patterns
            ax2 = axes[0, 1]
            dow_data = (
                df.groupby(["DayOfWeek", "DayNum"])["Total costs($)"]
                .mean()
                .reset_index()
            )
            dow_data = dow_data.sort_values("DayNum")

            bars = ax2.bar(
                dow_data["DayOfWeek"],
                dow_data["Total costs($)"],
                color=[
                    "lightblue" if i < WEEKEND_COLOR_THRESHOLD else "lightcoral"
                    for i in dow_data["DayNum"]
                ],
            )
            ax2.set_xlabel("Day of Week")
            ax2.set_ylabel("Average Daily Cost ($)")
            ax2.set_title("Average Cost by Day of Week")
            ax2.tick_params(axis="x", rotation=45)

            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + 5,
                    f"${height:.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

            # 3. Cost trend with anomalies
            ax3 = axes[0, 2]
            ax3.plot(df["Date"], df["Total costs($)"], "b-", alpha=0.7, linewidth=2)

            # Add trend line
            x_numeric = np.arange(len(df))
            trend_coeffs = np.polyfit(x_numeric, df["Total costs($)"], 1)
            trend_line = np.polyval(trend_coeffs, x_numeric)
            ax3.plot(
                df["Date"],
                trend_line,
                "r--",
                alpha=0.8,
                linewidth=2,
                label=f"Trend: ${trend_coeffs[0]:+.2f}/day",
            )

            # Mark anomalies if any
            total_costs = df["Total costs($)"]
            z_scores = np.abs(zscore(total_costs))
            outliers = z_scores > OUTLIER_Z_SCORE_THRESHOLD

            if outliers.any():
                outlier_dates = df[outliers]["Date"]
                outlier_costs = df[outliers]["Total costs($)"]
                ax3.scatter(
                    outlier_dates,
                    outlier_costs,
                    color="red",
                    s=50,
                    zorder=5,
                    label="Anomalies",
                )

            ax3.set_xlabel("Date")
            ax3.set_ylabel("Daily Cost ($)")
            ax3.set_title("Cost Timeline with Trend & Anomalies")
            ax3.legend()
            ax3.tick_params(axis="x", rotation=45)

            # 4. Service cost change trending
            ax4 = axes[1, 0]
            service_cols = self.data_processor.get_service_columns(df)

            if service_cols and len(df) >= MIN_DATA_POINTS_FOR_COMPARISON:
                # Split data into two periods for comparison
                mid_point = len(df) // 2
                earlier_period = df.iloc[:mid_point]
                recent_period = df.iloc[mid_point:]

                service_changes = []

                for service_col in service_cols:
                    service_name = service_col.replace("($)", "").strip()

                    earlier_avg = earlier_period[service_col].mean()
                    recent_avg = recent_period[service_col].mean()

                    # Only include services with meaningful costs
                    if earlier_avg > MIN_SERVICE_COST or recent_avg > MIN_SERVICE_COST:
                        dollar_change = recent_avg - earlier_avg
                        pct_change = (
                            (recent_avg - earlier_avg) / max(earlier_avg, 0.01)
                        ) * 100
                        total_cost = df[service_col].sum()

                        service_changes.append(
                            {
                                "service": service_name,  # Keep full name for now
                                "dollar_change": dollar_change,
                                "pct_change": pct_change,
                                "total_cost": total_cost,
                                "recent_avg": recent_avg,
                            }
                        )

                # Sort by absolute dollar change and take top 8
                service_changes.sort(
                    key=lambda x: abs(x["dollar_change"]), reverse=True
                )
                top_changes = service_changes[:8]

                if top_changes:
                    # Create more readable service names using helper function
                    services = [clean_service_name(s["service"]) for s in top_changes]

                    changes = [s["dollar_change"] for s in top_changes]

                    # Color bars: red for increases, green for decreases
                    colors = [
                        "#FF4444" if change > 0 else "#44AA44" for change in changes
                    ]

                    bars = ax4.barh(services, changes, color=colors, alpha=0.8)
                    ax4.set_xlabel("Daily Cost Change ($)")
                    ax4.set_title("Service Cost Changes\n(Recent vs Earlier Period)")
                    ax4.axvline(0, color="black", linestyle="-", alpha=0.3)

                    # Set font size for y-axis labels (service names)
                    ax4.tick_params(axis="y", labelsize=8)

                    # Add percentage labels
                    for bar, service_data in zip(bars, top_changes):
                        width = bar.get_width()
                        pct = service_data["pct_change"]

                        # Position label at end of bar
                        label_x = width + (0.02 if width >= 0 else -0.02)
                        ax4.text(
                            label_x,
                            bar.get_y() + bar.get_height() / 2,
                            f"{pct:+.0f}%",
                            ha="left" if width >= 0 else "right",
                            va="center",
                            fontsize=8,
                            fontweight="bold",
                        )
                else:
                    ax4.text(
                        0.5,
                        0.5,
                        "Insufficient service\ndata for trending",
                        ha="center",
                        va="center",
                        transform=ax4.transAxes,
                        fontsize=10,
                    )
                    ax4.set_title("Service Cost Changes")
            else:
                ax4.text(
                    0.5,
                    0.5,
                    "Insufficient data\nfor trending analysis",
                    ha="center",
                    va="center",
                    transform=ax4.transAxes,
                    fontsize=10,
                )
                ax4.set_title("Service Cost Changes")

            # 5. Cost distribution
            ax5 = axes[1, 1]
            costs = df["Total costs($)"]
            ax5.hist(costs, bins=20, alpha=0.7, color="skyblue", edgecolor="black")
            ax5.axvline(
                costs.mean(),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Mean: ${costs.mean():.0f}",
            )
            ax5.axvline(
                costs.median(),
                color="green",
                linestyle="--",
                linewidth=2,
                label=f"Median: ${costs.median():.0f}",
            )
            ax5.set_xlabel("Daily Cost ($)")
            ax5.set_ylabel("Frequency")
            ax5.set_title("Daily Cost Distribution")
            ax5.legend()

            # 6. Service cost breakdown pie chart
            ax6 = axes[1, 2]

            if service_cols:
                # Get top services for pie chart
                service_totals = df[service_cols].sum().sort_values(ascending=False)

                # Show top 6 services individually, group the rest as "Others"
                top_services = service_totals.head(6)
                others_total = service_totals.iloc[6:].sum()

                # Prepare data for pie chart with clean service names
                pie_data = top_services.copy()
                pie_labels = [
                    clean_service_name(s.replace("($)", "").strip(), max_length=12)
                    for s in pie_data.index
                ]

                if others_total > 0:
                    pie_data = pd.concat(
                        [pie_data, pd.Series([others_total], index=["Others($)"])]
                    )
                    pie_labels.append("Others")

                # Create pie chart with a clean color palette
                colors = [
                    "#FF6B6B",
                    "#4ECDC4",
                    "#45B7D1",
                    "#96CEB4",
                    "#FFEAA7",
                    "#DDA0DD",
                    "#98D8C8",
                ]

                _wedges, _texts, autotexts = ax6.pie(
                    pie_data.values,
                    labels=pie_labels,
                    autopct=lambda pct: f"${pie_data.sum() * pct / 100:.0f}\n"
                    f"({pct:.1f}%)",
                    startangle=90,
                    colors=colors[: len(pie_data)],
                    textprops={"fontsize": 8},
                )

                # Improve text formatting
                for autotext in autotexts:
                    autotext.set_color("white")
                    autotext.set_fontweight("bold")

                ax6.set_title("Service Cost Breakdown", fontsize=10, pad=20)
            else:
                ax6.text(
                    0.5,
                    0.5,
                    "No service data\navailable",
                    ha="center",
                    va="center",
                    transform=ax6.transAxes,
                    fontsize=12,
                )
                ax6.set_title("Service Cost Breakdown")

            plt.tight_layout()

            # Save visualization with timestamp
            output_file = (
                self.config.outputs_dir / f"aws_cost_dashboard_{timestamp}.png"
            )
            # Use pad_inches instead of bbox_inches='tight' to avoid extreme expansion
            plt.savefig(
                output_file,
                dpi=self.config.visualization_dpi,
                bbox_inches="tight",
                pad_inches=0.2,
                facecolor="white",
                edgecolor="none",
            )
            print(f"✓ Dashboard saved to: {output_file}")

            # Also save a "latest" version for easy access
            latest_file = self.config.outputs_dir / "aws_cost_dashboard_latest.png"
            plt.savefig(
                latest_file,
                dpi=self.config.visualization_dpi,
                bbox_inches="tight",
                pad_inches=0.2,
                facecolor="white",
                edgecolor="none",
            )
            print(f"✓ Latest dashboard: {latest_file}")

            plt.close()
            return str(output_file)

        except Exception as e:
            print(f"✗ Visualization error: {e}")
            return None
