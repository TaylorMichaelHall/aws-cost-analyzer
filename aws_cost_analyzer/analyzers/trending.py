"""
Trending and growth analysis for AWS services
"""

import numpy as np
from scipy import stats

from .base import BaseAnalyzer

# Constants for trending analysis
MIN_TRENDING_DATA_POINTS = 3
MIN_REGRESSION_DATA_POINTS = 2
HIGHLY_SIGNIFICANT_P = 0.01
SIGNIFICANT_P = 0.05
MARGINALLY_SIGNIFICANT_P = 0.1
MIN_VELOCITY_DATA_POINTS = 7
MIN_3DAY_VELOCITY_POINTS = 6
MIN_WEEKLY_VELOCITY_POINTS = 14
MIN_OVERALL_VELOCITY_POINTS = 4
SIGNIFICANT_VELOCITY_THRESHOLD = 10
HIGH_VELOCITY_THRESHOLD = 20
STRONG_CORRELATION_THRESHOLD = 0.5
VERY_STRONG_CORRELATION_THRESHOLD = 0.8
HIGH_CORRELATION_THRESHOLD = 0.7
MIN_SERVICE_COST_THRESHOLD = 10
MIN_SERVICE_VARIATION_THRESHOLD = 0.5
MIN_CORRELATION_SERVICES = 2
MIN_GROWTH_DATA_POINTS = 7
MIN_SERVICE_TOTAL_THRESHOLD = 5
ACCELERATION_THRESHOLD = 0.1
NEGATIVE_ACCELERATION_THRESHOLD = -0.1
RAPID_GROWTH_THRESHOLD = 5
GROWTH_THRESHOLD = 1


class TrendingAnalyzer(BaseAnalyzer):
    """Analyzes cost trends and growth patterns"""

    def analyze(self, df):
        """Run all trending analyses"""
        results = {}
        results["trending"] = self.run_trending_analysis(df)
        results["velocity"] = self.run_cost_velocity_analysis(df)
        results["correlations"] = self.run_service_correlation_analysis(df)
        results["growth"] = self.run_service_growth_analysis(df)
        return results

    def run_trending_analysis(self, df):
        """Analyze biggest trending changes in service costs over time"""
        if df is None:
            return None

        self.print_section_header("TRENDING SERVICE ANALYSIS")

        # Get service columns
        service_cols = self.get_service_columns(df)

        if len(service_cols) == 0:
            print("⚠ No service data available for trending analysis")
            return None

        # Calculate rolling averages and trends for each service
        window_size = min(
            7, len(df) // 2
        )  # 7-day window or half the data, whichever is smaller

        if window_size < MIN_TRENDING_DATA_POINTS:
            print("⚠ Need at least 3 days of data for trending analysis")
            return None

        trends = {}

        for service_col in service_cols:
            service_name = service_col.replace("($)", "").strip()
            service_data = df[service_col].copy()

            # Skip services with very low total costs
            if service_data.sum() < self.config.min_service_cost_for_analysis:
                continue

            # Calculate rolling average
            rolling_avg = service_data.rolling(window=window_size, min_periods=2).mean()

            # Calculate trend slope using linear regression on the rolling averages
            valid_data = rolling_avg.dropna()
            if len(valid_data) < MIN_REGRESSION_DATA_POINTS:
                continue

            x = np.arange(len(valid_data))
            slope, _intercept, r_value, p_value, _std_err = stats.linregress(
                x, valid_data.values
            )

            # Calculate percentage change from first to last period
            first_avg = valid_data.iloc[:window_size].mean()
            last_avg = valid_data.iloc[-window_size:].mean()

            if first_avg > 0:
                pct_change = ((last_avg - first_avg) / first_avg) * 100
            else:
                pct_change = 0

            # Calculate absolute change in dollars
            abs_change = last_avg - first_avg

            trends[service_name] = {
                "slope": slope,
                "pct_change": pct_change,
                "abs_change": abs_change,
                "r_squared": r_value**2,
                "p_value": p_value,
                "total_cost": service_data.sum(),
                "avg_cost": service_data.mean(),
                "recent_avg": last_avg,
                "early_avg": first_avg,
            }

        # Sort by absolute change (biggest dollar impact)
        trending_services = sorted(
            trends.items(), key=lambda x: abs(x[1]["abs_change"]), reverse=True
        )

        print("Top 10 services by absolute cost trend (daily average change):")
        print("=" * 75)
        for i, (service, data) in enumerate(trending_services[:10], 1):
            trend_symbol = (
                "📈"
                if data["abs_change"] > 0
                else "📉" if data["abs_change"] < 0 else "➡️"
            )
            significance = (
                "***"
                if data["p_value"] < HIGHLY_SIGNIFICANT_P
                else (
                    "**"
                    if data["p_value"] < SIGNIFICANT_P
                    else "*" if data["p_value"] < MARGINALLY_SIGNIFICANT_P else ""
                )
            )

            print(
                f"{i:2d}. {trend_symbol} {service:<25} "
                f"${data['abs_change']:+8.2f}/day ({data['pct_change']:+6.1f}%) "
                f"${data['total_cost']:8,.0f} total {significance}"
            )

        # Also show percentage-based trends for smaller services
        pct_trending = sorted(
            [
                (k, v)
                for k, v in trends.items()
                if v["total_cost"] > self.config.min_service_cost_for_trending
            ],
            key=lambda x: abs(x[1]["pct_change"]),
            reverse=True,
        )

        print(
            f"\nTop services by percentage change (for services >"
            f"${self.config.min_service_cost_for_trending:.0f} total):"
        )
        print("=" * 75)
        for i, (service, data) in enumerate(pct_trending[:10], 1):
            trend_symbol = (
                "📈"
                if data["pct_change"] > 0
                else "📉" if data["pct_change"] < 0 else "➡️"
            )
            significance = (
                "***"
                if data["p_value"] < HIGHLY_SIGNIFICANT_P
                else (
                    "**"
                    if data["p_value"] < SIGNIFICANT_P
                    else "*" if data["p_value"] < MARGINALLY_SIGNIFICANT_P else ""
                )
            )

            print(
                f"{i:2d}. {trend_symbol} {service:<25} "
                f"{data['pct_change']:+8.1f}% (${data['abs_change']:+6.2f}/day) "
                f"${data['total_cost']:8,.0f} total {significance}"
            )

        return trends

    def run_cost_velocity_analysis(self, df):
        """Analyze rate of cost change over different time windows"""
        if df is None or len(df) < MIN_VELOCITY_DATA_POINTS:
            return None

        self.print_section_header("COST VELOCITY ANALYSIS")

        total_costs = df["Total costs($)"]

        # Calculate different velocity metrics
        velocities = {}

        # 3-day velocity (recent vs previous 3 days)
        if len(df) >= MIN_3DAY_VELOCITY_POINTS:
            recent_3d = total_costs.iloc[-3:].mean()
            prev_3d = total_costs.iloc[-6:-3].mean()
            if prev_3d > 0:
                velocities["3_day"] = ((recent_3d - prev_3d) / prev_3d) * 100

        # Weekly velocity (recent week vs previous week)
        if len(df) >= MIN_WEEKLY_VELOCITY_POINTS:
            recent_7d = total_costs.iloc[-7:].mean()
            prev_7d = total_costs.iloc[-14:-7].mean()
            if prev_7d > 0:
                velocities["7_day"] = ((recent_7d - prev_7d) / prev_7d) * 100

        # Overall trend velocity (first half vs second half)
        if len(df) >= MIN_OVERALL_VELOCITY_POINTS:
            mid_point = len(df) // 2
            first_half = total_costs.iloc[:mid_point].mean()
            second_half = total_costs.iloc[mid_point:].mean()
            if first_half > 0:
                velocities["overall"] = ((second_half - first_half) / first_half) * 100

        print("Cost change velocity (percentage change per period):")
        print("-" * 50)

        for period, velocity in velocities.items():
            if abs(velocity) > SIGNIFICANT_VELOCITY_THRESHOLD:
                trend_emoji = (
                    "🚀"
                    if velocity > SIGNIFICANT_VELOCITY_THRESHOLD
                    else ("📉" if velocity < -SIGNIFICANT_VELOCITY_THRESHOLD else "➡️")
                )
                severity = (
                    " ⚠️ SIGNIFICANT" if abs(velocity) > HIGH_VELOCITY_THRESHOLD else ""
                )
            else:
                trend_emoji = "📈" if velocity > 0 else "📉" if velocity < 0 else "➡️"
                severity = ""

            print(
                f"{trend_emoji} {period.replace('_', '-'):<12}: "
                f"{velocity:+6.1f}%{severity}"
            )

        return velocities

    def run_service_correlation_analysis(self, df):
        """Analyze correlations between different services to find related cost
        patterns"""
        if df is None:
            return None

        self.print_section_header("SERVICE CORRELATION ANALYSIS")

        # Get service columns with meaningful data
        service_cols = self.get_service_columns(df)

        if len(service_cols) < MIN_CORRELATION_SERVICES:
            print("⚠ Need at least 2 services for correlation analysis")
            return None

        # Filter to services with total cost and some variation
        meaningful_services = [
            col
            for col in service_cols
            if df[col].sum() > MIN_SERVICE_COST_THRESHOLD
            and df[col].std() > MIN_SERVICE_VARIATION_THRESHOLD
        ]

        if len(meaningful_services) < MIN_CORRELATION_SERVICES:
            print("⚠ Need at least 2 services with meaningful cost variations")
            return None

        # Calculate correlation matrix
        correlation_data = df[meaningful_services]
        corr_matrix = correlation_data.corr()

        # Find high correlations (excluding self-correlations)
        high_correlations = []

        for i in range(len(meaningful_services)):
            for j in range(i + 1, len(meaningful_services)):
                service1 = meaningful_services[i].replace("($)", "").strip()
                service2 = meaningful_services[j].replace("($)", "").strip()
                correlation = corr_matrix.iloc[i, j]

                if abs(correlation) > STRONG_CORRELATION_THRESHOLD:
                    high_correlations.append(
                        {
                            "service1": service1,
                            "service2": service2,
                            "correlation": correlation,
                            "strength": (
                                "Very Strong"
                                if abs(correlation) > VERY_STRONG_CORRELATION_THRESHOLD
                                else "Strong"
                            ),
                        }
                    )

        if high_correlations:
            print("Strong service cost correlations (|r| > 0.5):")
            print("-" * 60)
            # Sort by absolute correlation strength
            high_correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)

            for corr in high_correlations[:10]:  # Show top 10
                corr_type = "📈 Positive" if corr["correlation"] > 0 else "📉 Negative"
                print(
                    f"{corr_type} {corr['strength']:<12}: "
                    f"{corr['service1']:<20} ↔ {corr['service2']:<20} "
                    f"(r={corr['correlation']:+.3f})"
                )

            # Provide insights
            print("\n💡 Insights:")
            positive_corrs = [
                c
                for c in high_correlations
                if c["correlation"] > HIGH_CORRELATION_THRESHOLD
            ]
            negative_corrs = [
                c
                for c in high_correlations
                if c["correlation"] < -HIGH_CORRELATION_THRESHOLD
            ]

            if positive_corrs:
                print(
                    f"   • {len(positive_corrs)} service pairs move together "
                    f"(may indicate shared workloads)"
                )
            if negative_corrs:
                print(
                    f"   • {len(negative_corrs)} service pairs move in opposite "
                    f"directions (may indicate substitution)"
                )

        else:
            print(
                "✅ No strong correlations found between services "
                "(costs are independent)"
            )

        return high_correlations

    def run_service_growth_analysis(self, df):  # noqa: PLR0912
        """Analyze growth rates and acceleration/deceleration patterns for services"""
        if df is None or len(df) < MIN_GROWTH_DATA_POINTS:
            return None

        self.print_section_header("SERVICE GROWTH RATE ANALYSIS")

        service_cols = self.get_service_columns(df)

        growth_analysis = {}

        for service_col in service_cols:
            service_name = service_col.replace("($)", "").strip()
            service_data = df[service_col]

            # Skip services with very low costs
            if service_data.sum() < MIN_SERVICE_TOTAL_THRESHOLD:
                continue

            # Calculate different growth metrics
            total_days = len(service_data)

            # Early vs Late period comparison (first 1/3 vs last 1/3)
            first_third = int(total_days * 0.33)
            last_third = int(total_days * 0.67)

            early_avg = service_data.iloc[:first_third].mean()
            late_avg = service_data.iloc[last_third:].mean()

            # Calculate compound daily growth rate
            if early_avg > 0 and total_days > first_third:
                days_between = total_days - first_third
                if late_avg > 0 and days_between > 0:
                    compound_growth = (
                        (late_avg / early_avg) ** (1 / days_between) - 1
                    ) * 100
                else:
                    compound_growth = 0
            else:
                compound_growth = 0

            # Calculate acceleration (is growth increasing or decreasing?)
            # Compare first half vs second half growth rates
            mid_point = total_days // 2

            # First half trend
            first_half = service_data.iloc[:mid_point]
            if len(first_half) > MIN_REGRESSION_DATA_POINTS:
                first_slope = np.polyfit(range(len(first_half)), first_half.values, 1)[
                    0
                ]
            else:
                first_slope = 0

            # Second half trend
            second_half = service_data.iloc[mid_point:]
            if len(second_half) > MIN_REGRESSION_DATA_POINTS:
                second_slope = np.polyfit(
                    range(len(second_half)), second_half.values, 1
                )[0]
            else:
                second_slope = 0

            acceleration = second_slope - first_slope

            growth_analysis[service_name] = {
                "early_avg": early_avg,
                "late_avg": late_avg,
                "compound_daily_growth": compound_growth,
                "acceleration": acceleration,
                "total_cost": service_data.sum(),
                "trend_direction": (
                    "Accelerating"
                    if acceleration > ACCELERATION_THRESHOLD
                    else (
                        "Decelerating"
                        if acceleration < NEGATIVE_ACCELERATION_THRESHOLD
                        else "Stable"
                    )
                ),
            }

        # Sort by compound growth rate
        growing_services = sorted(
            [
                (k, v)
                for k, v in growth_analysis.items()
                if v["total_cost"] > MIN_SERVICE_COST_THRESHOLD
            ],
            key=lambda x: x[1]["compound_daily_growth"],
            reverse=True,
        )

        print("Service growth rates (services >$10 total):")
        print("=" * 80)

        for i, (service, data) in enumerate(growing_services[:15], 1):
            growth_rate = data["compound_daily_growth"]
            trend_emoji = (
                "🚀"
                if growth_rate > RAPID_GROWTH_THRESHOLD
                else (
                    "📈"
                    if growth_rate > GROWTH_THRESHOLD
                    else "📉" if growth_rate < -GROWTH_THRESHOLD else "➡️"
                )
            )

            accel_emoji = (
                "⚡"
                if data["trend_direction"] == "Accelerating"
                else "🔻" if data["trend_direction"] == "Decelerating" else "🟰"
            )

            print(
                f"{i:2d}. {trend_emoji} {service:<25} "
                f"{growth_rate:+6.2f}%/day {accel_emoji} {data['trend_direction']:<12} "
                f"${data['total_cost']:8,.0f} total"
            )

        # Show top accelerating and decelerating services
        accelerating = sorted(
            [
                (k, v)
                for k, v in growth_analysis.items()
                if v["total_cost"] > MIN_SERVICE_COST_THRESHOLD
            ],
            key=lambda x: x[1]["acceleration"],
            reverse=True,
        )

        print("\nTop accelerating services (increasing growth rate):")
        print("-" * 55)
        for i, (service, data) in enumerate(accelerating[:5], 1):
            print(
                f"{i}. ⚡ {service:<30} acceleration: {data['acceleration']:+.2f}/day²"
            )

        print("\nTop decelerating services (decreasing growth rate):")
        print("-" * 55)
        for i, (service, data) in enumerate(reversed(accelerating[-5:]), 1):
            print(
                f"{i}. 🔻 {service:<30} deceleration: {data['acceleration']:+.2f}/day²"
            )

        return growth_analysis
