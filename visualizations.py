"""
=============================================================
  Smart Manufacturing Production Optimizer
  MODULE 3: Visualizations
  Generates all charts for the project report
=============================================================
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import pandas as pd
import os

# Save charts inside this project directory for portability.
OUT = os.path.join(os.path.dirname(__file__), "charts")
os.makedirs(OUT, exist_ok=True)

# ─── Colour palette ──────────────────────────────────────────────────────────
COLORS = ["#2E4057", "#048A81", "#54C6EB", "#EF7B45", "#D64045"]
BG     = "#F7F9FC"
GRID_C = "#E2E8F0"

from lp_model import SHORT, PRODUCTS as FULL, PROFIT, DEMAND_MIN, DEMAND_MAX


def _style_ax(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor(BG)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.tick_params(labelsize=8)
    ax.yaxis.grid(True, color=GRID_C, linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)


# ═══════════════════════════════════════════════════════════════════
# Chart 1 – Optimal Production Plan (bar chart)
# ═══════════════════════════════════════════════════════════════════
def chart_optimal_plan(solution, profit):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), facecolor=BG)
    fig.suptitle("Optimal Production Plan", fontsize=14, fontweight="bold", y=1.01)

    # Left – units produced
    ax = axes[0]
    bars = ax.bar(SHORT, solution, color=COLORS, edgecolor="white", linewidth=0.8)
    for bar, v in zip(bars, solution):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f"{v:.1f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
    # overlay demand range
    for i, (lo, hi) in enumerate(zip(DEMAND_MIN, DEMAND_MAX)):
        ax.plot([i - 0.4, i + 0.4], [lo, lo], color="gray", linewidth=1, linestyle="--")
        ax.plot([i - 0.4, i + 0.4], [hi, hi], color="gray", linewidth=1, linestyle=":")
    _style_ax(ax, "Units Produced per Day", "Product", "Units / Day")
    lo_line = mpatches.Patch(color="gray", label="Demand bounds (-- min / ·· max)")
    ax.legend(handles=[lo_line], fontsize=7)

    # Right – revenue contribution
    ax2 = axes[1]
    rev = solution * PROFIT
    wedges, texts, autotexts = ax2.pie(
        rev, labels=SHORT, autopct="%1.1f%%",
        colors=COLORS, startangle=140,
        wedgeprops=dict(edgecolor="white", linewidth=1.5))
    for t in autotexts:
        t.set_fontsize(8)
    ax2.set_title(f"Revenue Contribution\n(Total ₹{profit:,.0f}/day)",
                  fontsize=12, fontweight="bold")

    plt.tight_layout()
    path = f"{OUT}/1_optimal_plan.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {path}")
    return path


# ═══════════════════════════════════════════════════════════════════
# Chart 2 – Resource Utilisation Dashboard
# ═══════════════════════════════════════════════════════════════════
def chart_resource_utilisation(used, caps):
    fig, ax = plt.subplots(figsize=(10, 5), facecolor=BG)
    resources = list(used.keys())
    used_v = [used[r] for r in resources]
    slack_v = [caps[r] - used[r] for r in resources]
    util_pct = [used[r] / caps[r] * 100 for r in resources]

    x = np.arange(len(resources))
    w = 0.5

    b1 = ax.bar(x, used_v,  width=w, color=COLORS[:len(resources)],
                label="Used", edgecolor="white")
    b2 = ax.bar(x, slack_v, width=w, bottom=used_v,
                color="lightgray", label="Slack", edgecolor="white")

    for i, (bar, pct) in enumerate(zip(b1, util_pct)):
        col = "#D64045" if pct > 90 else "#048A81"
        ax.text(bar.get_x() + bar.get_width() / 2,
                used_v[i] / 2,
                f"{pct:.1f}%", ha="center", va="center",
                fontsize=9, fontweight="bold", color="white")

    ax.set_xticks(x)
    ax.set_xticklabels(resources, fontsize=9)
    _style_ax(ax, "Resource Utilisation vs Capacity", "Resource", "Units")
    ax.legend(fontsize=9)

    plt.tight_layout()
    path = f"{OUT}/2_resource_utilisation.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {path}")
    return path


# ═══════════════════════════════════════════════════════════════════
# Chart 3 – Sensitivity Analysis: Resource Capacity
# ═══════════════════════════════════════════════════════════════════
def chart_sensitivity_resources(sens_data, base_profit):
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), facecolor=BG)
    axes = axes.flatten()

    for idx, (res, data) in enumerate(sens_data.items()):
        ax = axes[idx]
        pct = data["pct"]
        prof = data["profit"]
        ax.plot(pct, prof, color=COLORS[idx], linewidth=2, marker="o",
                markersize=4)
        ax.axvline(0, color="gray", linestyle="--", linewidth=0.8)
        ax.axhline(base_profit, color="red", linestyle=":", linewidth=0.8,
                   label=f"Base: ₹{base_profit:,.0f}")
        ax.fill_between(pct, prof, base_profit,
                        where=[p > base_profit for p in prof],
                        alpha=0.15, color="green")
        ax.fill_between(pct, prof, base_profit,
                        where=[p < base_profit for p in prof],
                        alpha=0.15, color="red")
        _style_ax(ax, f"{res} Capacity (±30%)",
                  "Change (%)", "Optimal Profit (₹)")
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"₹{v/1000:.0f}K"))
        ax.legend(fontsize=7)

    axes[-1].set_visible(False)
    fig.suptitle("Sensitivity Analysis: Effect of Resource Capacity on Profit",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = f"{OUT}/3_sensitivity_resources.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {path}")
    return path


# ═══════════════════════════════════════════════════════════════════
# Chart 4 – Sensitivity Analysis: Profit Coefficients
# ═══════════════════════════════════════════════════════════════════
def chart_sensitivity_profit_coeff(sens_data, base_profit):
    fig, ax = plt.subplots(figsize=(11, 5), facecolor=BG)

    for idx, (prod, data) in enumerate(sens_data.items()):
        pct  = data["pct"]
        prof = data["profit"]
        ax.plot(pct, prof, color=COLORS[idx % len(COLORS)], linewidth=2,
                label=prod, marker="o", markersize=3)

    ax.axvline(0,           color="gray", linestyle="--", linewidth=0.8)
    ax.axhline(base_profit, color="black", linestyle=":", linewidth=1,
               label=f"Base profit ₹{base_profit:,.0f}")
    _style_ax(ax, "Sensitivity Analysis: Profit Coefficients (±40%)",
              "Change in Unit Profit (%)", "Optimal Total Profit (₹)")
    ax.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, _: f"₹{v/1000:.0f}K"))
    ax.legend(fontsize=9, loc="upper left")

    plt.tight_layout()
    path = f"{OUT}/4_sensitivity_profit.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {path}")
    return path


# ═══════════════════════════════════════════════════════════════════
# Chart 5 – Historical Dataset Analysis
# ═══════════════════════════════════════════════════════════════════
def chart_historical(df):
    fig = plt.figure(figsize=(14, 9), facecolor=BG)
    gs  = GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.35)

    # 5a – Daily profit trend
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.plot(df["Day"], df["Total_Daily_Profit_INR"] / 1000,
             color=COLORS[0], linewidth=1.5, alpha=0.8)
    ax1.fill_between(df["Day"], df["Total_Daily_Profit_INR"] / 1000,
                     alpha=0.15, color=COLORS[0])
    ax1.axhline(df["Total_Daily_Profit_INR"].mean() / 1000,
                color="red", linestyle="--", linewidth=1,
                label=f"Avg ₹{df['Total_Daily_Profit_INR'].mean():,.0f}")
    _style_ax(ax1, "60-Day Daily Profit Trend", "Day", "Profit (₹ thousands)")
    ax1.legend(fontsize=8)

    # 5b – Demand met pie
    ax2 = fig.add_subplot(gs[0, 2])
    met  = df["Demand_Met"].sum()
    nmet = len(df) - met
    ax2.pie([met, nmet], labels=[f"Met ({met}d)", f"Unmet ({nmet}d)"],
            colors=["#048A81", "#D64045"], autopct="%1.0f%%",
            startangle=90, wedgeprops=dict(edgecolor="white"))
    ax2.set_title("Demand Fulfillment\n(60 days)", fontsize=11, fontweight="bold")

    # 5c – Avg utilisation by resource
    ax3 = fig.add_subplot(gs[1, :2])
    resources_cols = {
        "Labor":    "Labor_Utilization_%",
        "CNC":      "CNC_Utilization_%",
        "Assembly": "Assembly_Util_%",
        "Steel":    "Steel_Utilization_%",
        "Copper":   "Copper_Utilization_%",
    }
    avg_util = {r: df[c].mean() for r, c in resources_cols.items()}
    bars = ax3.barh(list(avg_util.keys()), list(avg_util.values()),
                    color=COLORS, edgecolor="white")
    for bar, val in zip(bars, avg_util.values()):
        ax3.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                 f"{val:.1f}%", va="center", fontsize=8)
    ax3.axvline(85, color="red", linestyle="--", linewidth=1, label="85% threshold")
    _style_ax(ax3, "Avg Resource Utilisation Over 60 Days", "Utilisation (%)", "")
    ax3.set_xlim(0, 115)
    ax3.legend(fontsize=8)

    # 5d – Day-of-week profit boxplot
    ax4 = fig.add_subplot(gs[1, 2])
    dows  = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    data_bp = [df[df["Day_of_Week"] == d]["Total_Daily_Profit_INR"].values / 1000
               for d in dows]
    bp = ax4.boxplot(data_bp, labels=dows, patch_artist=True, medianprops={"color": "white"})
    for patch, col in zip(bp["boxes"], COLORS):
        patch.set_facecolor(col)
    _style_ax(ax4, "Profit by Day of Week", "Day", "Profit (₹K)")

    fig.suptitle("Historical Factory Data Analysis (60-Day Simulation)",
                 fontsize=13, fontweight="bold")

    path = f"{OUT}/5_historical_analysis.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {path}")
    return path


# ═══════════════════════════════════════════════════════════════════
# Chart 6 – Profit Margin & Demand Comparison
# ═══════════════════════════════════════════════════════════════════
def chart_product_comparison(solution):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), facecolor=BG)

    # Margin per unit
    ax = axes[0]
    ax.bar(SHORT, PROFIT, color=COLORS, edgecolor="white")
    for i, v in enumerate(PROFIT):
        ax.text(i, v + 5, f"₹{v}", ha="center", va="bottom",
                fontsize=9, fontweight="bold")
    _style_ax(ax, "Profit Margin per Unit (₹)", "Product", "₹ / Unit")

    # Optimal vs max demand
    ax2 = axes[1]
    x = np.arange(len(SHORT))
    w = 0.3
    ax2.bar(x - w/2, DEMAND_MAX, width=w, color="lightsteelblue",
            label="Max Demand", edgecolor="white")
    ax2.bar(x + w/2, solution, width=w, color=COLORS,
            label="Optimal Qty", edgecolor="white")
    ax2.set_xticks(x)
    ax2.set_xticklabels(SHORT)
    _style_ax(ax2, "Optimal Production vs Max Demand",
              "Product", "Units / Day")
    ax2.legend(fontsize=9)

    plt.tight_layout()
    path = f"{OUT}/6_product_comparison.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ {path}")
    return path


if __name__ == "__main__":
    # Quick standalone test
    from lp_model import build_and_solve, compute_slack, \
        sensitivity_analysis, profit_sensitivity_by_product
    from dataset_generator import generate_dataset
    import matplotlib.ticker

    sol, profit, _ = build_and_solve()
    used, caps, slack = compute_slack(sol)
    df = generate_dataset(60)

    print("Generating charts...")
    chart_optimal_plan(sol, profit)
    chart_resource_utilisation(used, caps)
    sens_r  = sensitivity_analysis(sol, profit)
    sens_p  = profit_sensitivity_by_product(sol, profit)
    chart_sensitivity_resources(sens_r, profit)
    chart_sensitivity_profit_coeff(sens_p, profit)
    chart_historical(df)
    chart_product_comparison(sol)
    print("Done.")
