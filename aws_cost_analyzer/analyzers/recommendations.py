"""
Efficiency recommendations based on cost patterns
"""

from .base import BaseAnalyzer

# Constants for analysis thresholds
MIN_DATA_POINTS = 5
HIGH_VOLATILITY_THRESHOLD = 0.3
MIN_BIWEEKLY_DATA_POINTS = 14
GROWTH_THRESHOLD = 1.1  # 10% growth
SIGNIFICANT_PEAK_THRESHOLD = 1.4  # 40% difference
MODERATE_PEAK_THRESHOLD = 1.15  # 15% difference
WEEKDAY_WEEKEND_THRESHOLD = 1.3  # 30% difference
TOP_SERVICES_CONCENTRATION_THRESHOLD = 0.8  # 80% concentration in top 5 services


class RecommendationEngine(BaseAnalyzer):
    """Generates efficiency and optimization recommendations"""

    def analyze(self, df):
        """Generate recommendations"""
        return self.generate_efficiency_recommendations(df)

    def generate_efficiency_recommendations(self, df):  # noqa: PLR0912,PLR0915
        """Generate recommendations based on cost patterns and usage analysis"""
        if df is None:
            return None

        self.print_section_header("EFFICIENCY RECOMMENDATIONS")

        recommendations = []

        # Weekend vs Weekday analysis
        weekday_avg = df[~df["IsWeekend"]]["Total costs($)"].mean()
        weekend_avg = df[df["IsWeekend"]]["Total costs($)"].mean()

        if weekend_avg > weekday_avg:  # Weekend costs are actually higher than weekdays
            recommendations.append(
                {
                    "category": "⏰ Scheduling Opportunity",
                    "recommendation": (
                        f"Weekend costs are higher (${weekend_avg:.2f} vs "
                        f"${weekday_avg:.2f} weekday avg). High weekend usage may "
                        "indicate always-on resources that could be scaled down during "
                        "low-demand periods."
                    ),
                    "potential_savings": (
                        f"~${(weekend_avg - weekday_avg) * 104:.0f}/year"
                    ),  # 52 weekends * 2 days
                }
            )
        elif (
            weekday_avg > weekend_avg * WEEKDAY_WEEKEND_THRESHOLD
        ):  # Weekdays significantly higher - good pattern
            recommendations.append(
                {
                    "category": "✅ Scheduling Efficiency",
                    "recommendation": (
                        f"Good cost pattern detected: weekends are "
                        f"{((1 - weekend_avg/weekday_avg) * 100):.1f}% cheaper "
                        f"(${weekend_avg:.2f} vs ${weekday_avg:.2f}). This suggests "
                        f"effective resource scaling during low-demand periods."
                    ),
                    "potential_savings": (
                        "Pattern already optimized - maintain current scheduling"
                    ),
                }
            )

        # Service concentration analysis
        service_cols = self.get_service_columns(df)
        if service_cols:
            service_totals = df[service_cols].sum().sort_values(ascending=False)
            top_5_share = service_totals.head(5).sum() / service_totals.sum()

            if top_5_share > TOP_SERVICES_CONCENTRATION_THRESHOLD:
                recommendations.append(
                    {
                        "category": "🎯 Cost Concentration",
                        "recommendation": (
                            f"Top 5 services account for {top_5_share:.1%} of costs. "
                            f"Focus optimization efforts on: "
                            f"{', '.join([
                                s.replace('($)', '')
                                for s in service_totals.head(3).index
                            ])}"
                        ),
                        "potential_savings": "High - concentrated optimization impact",
                    }
                )

        # Cost volatility analysis (excluding monthly billing spikes)
        monthly_billing_stats = self.data_processor.get_monthly_billing_stats()
        if monthly_billing_stats is not None and "HasMonthlyBillingSpike" in df.columns:
            # Calculate volatility excluding first-of-month spikes for more
            # accurate assessment
            clean_costs = df[~df["HasMonthlyBillingSpike"]]["Total costs($)"]
            if len(clean_costs) > MIN_DATA_POINTS:  # Need sufficient data
                cv = clean_costs.std() / clean_costs.mean()
                total_costs_for_calc = clean_costs
            else:
                total_costs_for_calc = df["Total costs($)"]
                cv = total_costs_for_calc.std() / total_costs_for_calc.mean()
        else:
            total_costs_for_calc = df["Total costs($)"]
            cv = total_costs_for_calc.std() / total_costs_for_calc.mean()

        if cv > HIGH_VOLATILITY_THRESHOLD:  # High volatility
            recommendations.append(
                {
                    "category": "📊 Cost Stability",
                    "recommendation": (
                        f"High cost volatility detected (CV={cv:.2f}). Review "
                        f"workload scheduling and resource provisioning to reduce "
                        f"cost swings."
                    ),
                    "potential_savings": (
                        f"~${total_costs_for_calc.std() * 0.5 * 365:.0f}/year "
                        f"from reduced volatility"
                    ),
                }
            )

        # Growth trend recommendations
        total_costs = df[
            "Total costs($)"
        ]  # Use original total costs for growth analysis
        if len(df) >= MIN_BIWEEKLY_DATA_POINTS:
            recent_avg = total_costs.iloc[-7:].mean()
            earlier_avg = total_costs.iloc[-14:-7].mean()

            if recent_avg > earlier_avg * GROWTH_THRESHOLD:  # Growing >10%/week
                growth_rate = ((recent_avg / earlier_avg) - 1) * 100
                recommendations.append(
                    {
                        "category": "📈 Growth Management",
                        "recommendation": (
                            f"Costs growing rapidly ({growth_rate:.1f}% "
                            f"week-over-week). Review new deployments and "
                            f"scaling policies."
                        ),
                        "potential_savings": (
                            "Prevent runaway costs - review immediately"
                        ),
                    }
                )

        # Day-of-week peak load analysis
        dow_costs = df.groupby("DayOfWeek")["Total costs($)"].mean()
        min_dow = dow_costs.idxmin()
        max_dow = dow_costs.idxmax()

        if (
            dow_costs.max() > dow_costs.min() * SIGNIFICANT_PEAK_THRESHOLD
        ):  # >40% difference indicates significant peaks
            peak_premium = dow_costs.max() - dow_costs.min()
            peak_pct = ((dow_costs.max() / dow_costs.min()) - 1) * 100

            recommendations.append(
                {
                    "category": "📊 Peak Load Distribution",
                    "recommendation": (
                        f"High peak load variation: {max_dow} (${dow_costs.max():.2f}) "
                        f"is {peak_pct:.1f}% higher than {min_dow} "
                        f"(${dow_costs.min():.2f}). Peak loads may be causing "
                        f"auto-scaling costs (e.g., RDS readers). Consider: "
                        f"1) Distributing batch jobs away from {max_dow}, "
                        f"2) Pre-scaling resources before peak periods, "
                        f"3) Using scheduled scaling instead of reactive scaling."
                    ),
                    "potential_savings": (
                        f"~${peak_premium * 0.3 * 52:.0f}/year from peak smoothing"
                    ),  # Assume 30% of peak premium can be optimized
                }
            )
        elif (
            dow_costs.max() > dow_costs.min() * MODERATE_PEAK_THRESHOLD
        ):  # 15-40% variation is normal but worth noting
            recommendations.append(
                {
                    "category": "📈 Load Pattern Analysis",
                    "recommendation": (
                        f"Moderate load variation detected: {max_dow} "
                        f"(${dow_costs.max():.2f}) vs {min_dow} "
                        f"(${dow_costs.min():.2f}). This variation appears "
                        f"normal for most workloads. Monitor for any "
                        f"unexpected changes."
                    ),
                    "potential_savings": "No immediate optimization needed",
                }
            )

        # Display recommendations
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec['category']}")
                print(f"   {rec['recommendation']}")
                print(f"   💰 Potential impact: {rec['potential_savings']}")
                print()
        else:
            print(
                "✅ No major optimization opportunities identified "
                "based on current patterns"
            )

        return recommendations
