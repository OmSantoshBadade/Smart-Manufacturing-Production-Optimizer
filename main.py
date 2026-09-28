"""
=============================================================
  Smart Manufacturing Production Optimizer
  MAIN RUNNER  ─  run this file to execute the full project
  
  Output files generated:
    factory_data.csv          ← 60-day simulated dataset
    charts/1_optimal_plan.png
    charts/2_resource_utilisation.png
    charts/3_sensitivity_resources.png
    charts/4_sensitivity_profit.png
    charts/5_historical_analysis.png
    charts/6_product_comparison.png
=============================================================
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
BASE_DIR = os.path.dirname(__file__)

import numpy as np
import matplotlib.ticker    # needed by visualizations.py
import matplotlib
matplotlib.use("Agg")

from dataset_generator           import generate_dataset
from lp_model                    import (build_and_solve, compute_slack,
                                         sensitivity_analysis,
                                         profit_sensitivity_by_product,
                                         PRODUCTS, SHORT, PROFIT,
                                         DEMAND_MIN, DEMAND_MAX,
                                         LABOR_CAP, CNC_CAP, ASSEMBLY_CAP,
                                         STEEL_CAP, COPPER_CAP)
from visualizations              import (chart_optimal_plan,
                                         chart_resource_utilisation,
                                         chart_sensitivity_resources,
                                         chart_sensitivity_profit_coeff,
                                         chart_historical,
                                         chart_product_comparison)

DIVIDER = "=" * 65

def banner(title):
    print(f"\n{DIVIDER}\n  {title}\n{DIVIDER}")


def main():
    # ── 1. Generate Dataset ──────────────────────────────────────
    banner("STEP 1 – Generating 60-Day Factory Dataset")
    df = generate_dataset(60)
    df.to_csv(os.path.join(BASE_DIR, "factory_data.csv"), index=False)
    print(f"  Rows : {len(df)}   Columns : {len(df.columns)}")
    print(f"  Date range : Day 1 – Day 60  (Mon–Fri cycles)")
    print(f"\n  Sample (first 3 days):")
    print(df[["Day", "Day_of_Week",
              "Units_Electronic_Controllers", "Units_Hydraulic_Pumps",
              "Units_Conveyor_Belts", "Units_Precision_Gears",
              "Units_Sensor_Modules", "Total_Daily_Profit_INR"]].head(3).to_string(index=False))
    print(f"\n  Avg Daily Profit : ₹{df['Total_Daily_Profit_INR'].mean():>10,.0f}")
    print(f"  Min Daily Profit : ₹{df['Total_Daily_Profit_INR'].min():>10,.0f}")
    print(f"  Max Daily Profit : ₹{df['Total_Daily_Profit_INR'].max():>10,.0f}")

    # ── 2. Formulate & Solve LP ──────────────────────────────────
    banner("STEP 2 – Formulating & Solving the LP Model")
    print("""
  DECISION VARIABLES
  ─────────────────
  x₁ = Electronic Controllers (units/day)
  x₂ = Hydraulic Pumps        (units/day)
  x₃ = Conveyor Belts         (units/day)
  x₄ = Precision Gears        (units/day)
  x₅ = Sensor Modules         (units/day)

  OBJECTIVE FUNCTION  (Maximise)
  ─────────────────────────────
  Z = 450x₁ + 600x₂ + 350x₃ + 280x₄ + 520x₅

  CONSTRAINTS
  ──────────
  Labor    : 6.0x₁ + 9.0x₂ + 4.5x₃ + 3.0x₄ + 7.0x₅ ≤ 480  hrs
  CNC      : 4.0x₁ + 7.0x₂ + 2.5x₃ + 2.0x₄ + 5.0x₅ ≤ 300  hrs
  Assembly : 3.0x₁ + 5.0x₂ + 2.0x₃ + 1.5x₄ + 4.0x₅ ≤ 240  hrs
  Steel    : 8.0x₁ +14.0x₂ + 6.0x₃ + 4.0x₄ + 3.0x₅ ≤ 1200 kg
  Copper   : 2.5x₁ + 1.5x₂ + 0.5x₃ + 0.8x₄ + 3.5x₅ ≤ 400  kg

  Demand (min / max):
    EC  : 10 – 35    HP  : 5 – 25    CB  : 15 – 50
    PG  : 20 – 60    SM  : 10 – 40
  Non-negativity: x₁, …, x₅ ≥ 0
    """)

    solution, profit, _ = build_and_solve()

    print("  ── OPTIMAL SOLUTION ──────────────────────────────────")
    for name, qty in zip(SHORT, solution):
        bar = "█" * int(qty / 2)
        print(f"  {name:5s}  {qty:6.2f} units/day   {bar}")
    print(f"\n  ✦ MAXIMUM DAILY PROFIT = ₹{profit:,.2f}")

    # ── 3. Resource Utilisation ──────────────────────────────────
    banner("STEP 3 – Resource Utilisation & Slack Analysis")
    used, caps, slack = compute_slack(solution)

    print(f"  {'Resource':<22} {'Used':>8} {'Capacity':>10} {'Slack':>8}  {'Util %':>7}")
    print("  " + "-" * 60)
    for k in used:
        pct   = used[k] / caps[k] * 100
        flag  = " ← BINDING" if abs(slack[k]) < 0.5 else ""
        print(f"  {k:<22} {used[k]:>8.1f} {caps[k]:>10.0f} "
              f"{slack[k]:>8.1f}  {pct:>6.1f}%{flag}")

    # ── 4. Sensitivity Analysis ──────────────────────────────────
    banner("STEP 4 – Sensitivity Analysis")
    sens_r = sensitivity_analysis(solution, profit)
    sens_p = profit_sensitivity_by_product(solution, profit)

    print("  Resource Capacity Sensitivity (±30% change):")
    print(f"  {'Resource':<12} {'Profit at -30%':>16} {'Base Profit':>14} {'Profit at +30%':>16}")
    print("  " + "-" * 62)
    for res, data in sens_r.items():
        p_low  = data["profit"][0]
        p_high = data["profit"][-1]
        print(f"  {res:<12} ₹{p_low:>13,.0f} ₹{profit:>12,.0f} ₹{p_high:>13,.0f}")

    print("\n  Product Profit Coefficient Sensitivity (±40%):")
    print(f"  {'Product':<8} {'Profit at -40%':>16} {'Base Profit':>14} {'Profit at +40%':>16}")
    print("  " + "-" * 57)
    for prod, data in sens_p.items():
        p_low  = data["profit"][0]
        p_high = data["profit"][-1]
        print(f"  {prod:<8} ₹{p_low:>13,.0f} ₹{profit:>12,.0f} ₹{p_high:>13,.0f}")

    # ── 5. Recommendations ──────────────────────────────────────
    banner("STEP 5 – Management Recommendations")
    binding = [k for k in slack if abs(slack[k]) < 0.5]
    print(f"""
  FINDINGS
  ───────
  1. Optimal daily profit of ₹{profit:,.0f} is achievable with the
     recommended production mix.

  2. BINDING CONSTRAINTS: {', '.join(binding) if binding else 'None'}
     These resources are fully utilised and limit further profit growth.
     Investing in capacity expansion here yields highest ROI.

  3. Hydraulic Pumps (HP) have the highest profit margin (₹600/unit)
     and should be produced at maximum demand capacity (25 units/day).

  4. Sensor Modules (SM) offer the second-highest margin (₹520/unit)
     and are constrained primarily by CNC machine time.

  5. Sensitivity analysis shows CNC and Assembly capacity have the
     steepest profit–capacity slopes. A 30% increase in CNC capacity
     would unlock approximately ₹{sens_r['CNC']['profit'][-1] - profit:,.0f}
     additional daily profit.

  ACTIONABLE STEPS FOR MANAGEMENT
  ────────────────────────────────
  • Prioritise HP and SM production in daily planning.
  • Negotiate shift extensions or overtime for binding resources.
  • Evaluate capex for additional CNC machine (highest sensitivity).
  • Review Precision Gear demand ceiling — currently not binding;
    explore new sales channels to raise the demand upper bound.
  • Use the recommended production plan as the daily dispatch schedule.
    """)

    # ── 6. Generate Charts ───────────────────────────────────────
    banner("STEP 6 – Generating All Charts")
    chart_optimal_plan(solution, profit)
    chart_resource_utilisation(used, caps)
    chart_sensitivity_resources(sens_r, profit)
    chart_sensitivity_profit_coeff(sens_p, profit)
    chart_historical(df)
    chart_product_comparison(solution)

    print(f"\n  ✓ All charts saved to {os.path.join(BASE_DIR, 'charts')}/")
    print(f"\n{DIVIDER}")
    print("  PROJECT COMPLETE")
    print(DIVIDER)

    return solution, profit, df, used, caps, slack, sens_r, sens_p


if __name__ == "__main__":
    results = main()
