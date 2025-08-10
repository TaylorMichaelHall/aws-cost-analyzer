"""
Basic analysis methods - monthly comparison, service analysis, day-of-week patterns
"""

from datetime import date, datetime, timezone

from .base import BaseAnalyzer

# Constants
# Minimum number of months needed for month-to-month comparison
MIN_MONTHS_FOR_COMPARISON = 2
MIN_DAYS_FOR_PERIOD_COMPARISON = 4  # Minimum days needed for period comparison
MIN_MONTH_END_DAY = 28  # Consider month complete if last data is after this day
DECEMBER_MONTH = 12


class BasicAnalyzer(BaseAnalyzer):
    """Handles basic cost analysis operations"""

    def analyze(self, df):
        """Run all basic analyses"""
        results = {}
        results["monthly"] = self.run_monthly_comparison(df)
        results["projection"] = self.run_projection_analysis(df)
        results["services"] = self.run_service_analysis(df)
        results["dow"] = self.run_day_of_week_analysis(df)
        results["monthly_billing"] = self.run_monthly_billing_analysis(df)
        return results

    def run_monthly_comparison(self, df):
        """Run monthly comparison analysis"""
        if df is None:
            return None

        self.print_section_header("PERIOD COST COMPARISON")

        # Get unique months
        months = df["Month"].unique()

        if len(months) < MIN_MONTHS_FOR_COMPARISON:
            # If we don't have multiple months, try period comparison
            return self._run_period_comparison(df)

        # Get latest two months
        months = sorted(months)
        prev_month, curr_month = months[-2], months[-1]

        prev_data = df[df["Month"] == prev_month]
        curr_data = df[df["Month"] == curr_month]

        prev_total = prev_data["Total costs($)"].sum()
        curr_total = curr_data["Total costs($)"].sum()

        prev_avg = prev_data["Total costs($)"].mean()
        curr_avg = curr_data["Total costs($)"].mean()

        print(
            f"{prev_month}: ${prev_total:,.2f} total, ${prev_avg:.2f} daily avg "
            f"({len(prev_data)} days)"
        )
        print(
            f"{curr_month}: ${curr_total:,.2f} total, ${curr_avg:.2f} daily avg "
            f"({len(curr_data)} days)"
        )
        change_pct = (curr_avg / prev_avg - 1) * 100
        print(f"Change: ${curr_avg - prev_avg:+.2f}/day ({change_pct:+.1f}%)")

        return {
            "prev_month": prev_month,
            "curr_month": curr_month,
            "prev_total": prev_total,
            "curr_total": curr_total,
            "prev_avg": prev_avg,
            "curr_avg": curr_avg,
        }

    def _run_period_comparison(self, df):
        """Run comparison for periods shorter than a month"""
        total_days = len(df)

        if total_days < MIN_DAYS_FOR_PERIOD_COMPARISON:
            print("⚠ Need at least 4 days of data for period comparison")
            return None

        # Split data roughly in half
        split_point = total_days // 2

        first_half = df.iloc[:split_point]
        second_half = df.iloc[split_point:]

        first_total = first_half["Total costs($)"].sum()
        second_total = second_half["Total costs($)"].sum()

        first_avg = first_half["Total costs($)"].mean()
        second_avg = second_half["Total costs($)"].mean()

        first_period = (
            f"{first_half['Date'].min().date()} to {first_half['Date'].max().date()}"
        )
        second_period = (
            f"{second_half['Date'].min().date()} to {second_half['Date'].max().date()}"
        )

        print(
            f"First period ({first_period}): ${first_total:,.2f} total, "
            f"${first_avg:.2f} daily avg ({len(first_half)} days)"
        )
        print(
            f"Second period ({second_period}): ${second_total:,.2f} total, "
            f"${second_avg:.2f} daily avg ({len(second_half)} days)"
        )
        if first_avg > 0:
            change_pct = (second_avg / first_avg - 1) * 100
            print(f"Change: ${second_avg - first_avg:+.2f}/day ({change_pct:+.1f}%)")

        return {
            "first_period": first_period,
            "second_period": second_period,
            "first_total": first_total,
            "second_total": second_total,
            "first_avg": first_avg,
            "second_avg": second_avg,
        }

    def run_projection_analysis(self, df):
        """Run cost projection analysis"""
        if df is None:
            return None

        self.print_section_header("COST PROJECTION ANALYSIS")

        # Get current month data
        current_month = df["Month"].max()
        curr_data = df[df["Month"] == current_month]

        if len(curr_data) == 0:
            print("⚠ No current month data")
            return None

        # Check if current month is complete
        today = datetime.now(tz=timezone.utc).date()
        last_data_date = curr_data["Date"].max().date()
        is_complete_month = (
            last_data_date.day >= MIN_MONTH_END_DAY
            and last_data_date.month != today.month
        )

        if is_complete_month:
            print(f"✓ {current_month} appears to be a complete month")
            return None

        # Projection for incomplete month
        curr_total = curr_data["Total costs($)"].sum()
        last_day_cost = curr_data["Total costs($)"].iloc[-1]

        # Check if last day appears incomplete (very low cost)
        avg_cost = curr_data["Total costs($)"].mean()
        is_last_day_incomplete = last_day_cost < (avg_cost * 0.5)

        if is_last_day_incomplete:
            # Exclude last day for projection
            complete_data = curr_data.iloc[:-1]
            complete_avg = complete_data["Total costs($)"].mean()
            print(
                f"⚠ Last day appears incomplete (${last_day_cost:.2f}), "
                f"excluding from projection"
            )
        else:
            complete_avg = curr_data["Total costs($)"].mean()

        # Get days in current month
        year, month = int(current_month[:4]), int(current_month[5:])
        next_month = (
            date(year + 1, 1, 1)
            if month == DECEMBER_MONTH
            else date(year, month + 1, 1)
        )
        days_in_month = (next_month - date(year, month, 1)).days

        # Project full month
        projected_total = complete_avg * days_in_month

        print(f"Current month ({current_month}):")
        print(f"  Total so far: ${curr_total:,.2f} ({len(curr_data)} days)")
        print(f"  Daily average: ${complete_avg:.2f}")
        print(f"  Days in month: {days_in_month}")
        print(f"  Projected total: ${projected_total:,.2f}")

        return {
            "current_month": current_month,
            "current_total": curr_total,
            "daily_avg": complete_avg,
            "projected_total": projected_total,
            "days_in_month": days_in_month,
        }

    def run_service_analysis(self, df):
        """Analyze top services and their trends"""
        if df is None:
            return None

        self.print_section_header("TOP SERVICES ANALYSIS")

        # Get service columns
        service_cols = self.get_service_columns(df)

        # Calculate total costs by service
        service_totals = df[service_cols].sum().sort_values(ascending=False)

        print("Top 10 services by total cost:")
        for i, (service, cost) in enumerate(service_totals.head(10).items(), 1):
            service_clean = service.replace("($)", "").strip()
            print(f"{i:2d}. {service_clean:<35} ${cost:>10,.2f}")

        return service_totals.head(10).to_dict()

    def run_day_of_week_analysis(self, df):
        """Analyze cost patterns by day of week"""
        if df is None:
            return None

        self.print_section_header("DAY OF WEEK ANALYSIS")

        # Group by day of week
        dow_stats = df.groupby("DayOfWeek")["Total costs($)"].agg(
            ["mean", "std", "count"]
        )

        # Order by day of week
        day_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        print("Average daily costs by day of week:")
        for day in day_order:
            if day in dow_stats.index:
                stats = dow_stats.loc[day]
                weekend_flag = "📅" if day in ["Saturday", "Sunday"] else "  "
                print(
                    f"  {weekend_flag} {day:<10}: ${stats['mean']:>7.2f} ± "
                    f"${stats['std']:>6.2f} ({stats['count']} days)"
                )

        return dow_stats.to_dict()

    def run_monthly_billing_analysis(self, df):
        """Analyze first-of-month billing patterns (savings plans, free tier, etc.)"""
        monthly_billing_stats = self.data_processor.get_monthly_billing_stats()

        if df is None or monthly_billing_stats is None:
            return None

        self.print_section_header("MONTHLY BILLING PATTERN ANALYSIS")

        stats = monthly_billing_stats

        # Check if we have any first days in our data
        first_days = df[df["IsFirstOfMonth"]]
        if len(first_days) == 0:
            print("📅 No first-of-month data in this period")
            return None

        print("First-of-month cost patterns (savings plans, free tier, etc.):")
        print("-" * 65)

        print(
            f"📊 Baseline daily cost (days 2-31): ${stats['baseline_mean']:.2f} ± "
            f"${stats['baseline_std']:.2f}"
        )
        print(f"📅 First-of-month average: ${stats['first_day_mean']:.2f}")

        # Calculate the first-day premium
        first_day_premium = 0
        if stats["baseline_mean"] > 0:
            first_day_premium = (
                (stats["first_day_mean"] - stats["baseline_mean"])
                / stats["baseline_mean"]
            ) * 100
            print(f"💰 First-day cost premium: {first_day_premium:+.1f}% vs baseline")

        if stats["first_day_spikes"] > 0:
            print(f"🚨 {stats['first_day_spikes']} first-day billing spikes detected")
            spike_days = df[df["HasMonthlyBillingSpike"]]
            for _, row in spike_days.iterrows():
                spike_amount = row["Total costs($)"] - stats["baseline_mean"]
                print(
                    f"   📈 {row['Date'].strftime('%Y-%m-%d')}: "
                    f"${row['Total costs($)']:,.2f} (+${spike_amount:.2f})"
                )
        else:
            print("✅ No unusual first-day billing spikes detected")

        # Provide guidance
        print("\n💡 Monthly billing insights:")
        if stats["first_day_mean"] > stats["baseline_mean"] * 1.2:  # 20% higher
            print("   • First-of-month costs are significantly higher than baseline")
            print(
                "   • Likely due to: Savings Plans, Reserved Instances, "
                "or free tier resets"
            )
            print("   • Consider this pattern when analyzing trends and anomalies")
        elif stats["first_day_mean"] > stats["baseline_mean"] * 1.05:  # 5% higher
            print("   • First-of-month costs are moderately higher than baseline")
            print("   • Minor monthly billing cycle effects detected")
        else:
            print("   • First-of-month costs are consistent with other days")

        return {
            "baseline_mean": stats["baseline_mean"],
            "first_day_mean": stats["first_day_mean"],
            "first_day_premium_pct": first_day_premium,
            "spike_count": stats["first_day_spikes"],
        }
