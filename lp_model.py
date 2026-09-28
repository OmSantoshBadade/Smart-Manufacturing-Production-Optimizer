"""
=============================================================
  Smart Manufacturing Production Optimizer
  MODULE 2: Linear Programming Model
  
  Objective : Maximize daily profit
  Products  : 5 (EC, HP, CB, PG, SM)
  Constraints: Labor, CNC Machine, Assembly, Steel, Copper,
               Demand upper/lower bounds
  
  Solved via scipy.optimize.linprog (HiGHS interior-point method).
  PuLP equivalent code is shown in comments for reference.
=============================================================
"""

import os
import pandas as pd
import numpy as np
from scipy.optimize import linprog


# ─── Problem Data ────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(__file__)

# 1. Load Product Data
prod_df = pd.read_csv(os.path.join(BASE_DIR, "product_data.csv"))
PRODUCTS = prod_df["Product_Full_Name"].str.replace(" ", "\n").tolist()
SHORT = prod_df["Product_Short_Name"].tolist()

# Objective coefficients and resource usage arrays
PROFIT = prod_df["Profit"].to_numpy(dtype=float)
LABOR    = prod_df["Labor_Usage"].to_numpy(dtype=float)
CNC      = prod_df["CNC_Usage"].to_numpy(dtype=float)
ASSEMBLY = prod_df["Assembly_Usage"].to_numpy(dtype=float)
STEEL    = prod_df["Steel_Usage"].to_numpy(dtype=float)
COPPER   = prod_df["Copper_Usage"].to_numpy(dtype=float)

# Demand bounds
DEMAND_MIN = prod_df["Demand_Min"].to_numpy(dtype=float)
DEMAND_MAX = prod_df["Demand_Max"].to_numpy(dtype=float)

# 2. Load Capacity Data
cap_df = pd.read_csv(os.path.join(BASE_DIR, "resource_capacities.csv")).set_index("Resource")
LABOR_CAP    = cap_df.loc["Labor", "Capacity"]
CNC_CAP      = cap_df.loc["CNC", "Capacity"]
ASSEMBLY_CAP = cap_df.loc["Assembly", "Capacity"]
STEEL_CAP    = cap_df.loc["Steel", "Capacity"]
COPPER_CAP   = cap_df.loc["Copper", "Capacity"]


def build_and_solve():
    """
    Formulate and solve the LP.

    ─── PuLP equivalent (for reference) ────────────────────────────
    from pulp import *

    prob = LpProblem("Production_Optimizer", LpMaximize)

    x = [LpVariable(f"x_{s}", lowBound=DEMAND_MIN[i], upBound=DEMAND_MAX[i])
         for i, s in enumerate(SHORT)]

    # Objective
    prob += lpSum(PROFIT[i] * x[i] for i in range(5)), "Total_Profit"

    # Resource constraints
    prob += lpSum(LABOR[i]    * x[i] for i in range(5)) <= LABOR_CAP,    "Labor"
    prob += lpSum(CNC[i]      * x[i] for i in range(5)) <= CNC_CAP,      "CNC"
    prob += lpSum(ASSEMBLY[i] * x[i] for i in range(5)) <= ASSEMBLY_CAP, "Assembly"
    prob += lpSum(STEEL[i]    * x[i] for i in range(5)) <= STEEL_CAP,    "Steel"
    prob += lpSum(COPPER[i]   * x[i] for i in range(5)) <= COPPER_CAP,   "Copper"

    prob.solve(PULP_CBC_CMD(msg=0))

    solution = [value(xi) for xi in x]
    profit   = value(prob.objective)
    ─────────────────────────────────────────────────────────────────
    """

    n = len(SHORT)  # number of products

    # scipy.linprog minimises, so negate profit to maximise
    c = -PROFIT

    # Inequality constraints:  A_ub @ x <= b_ub
    A_ub = np.vstack([LABOR, CNC, ASSEMBLY, STEEL, COPPER])
    b_ub = np.array([LABOR_CAP, CNC_CAP, ASSEMBLY_CAP, STEEL_CAP, COPPER_CAP],
                    dtype=float)

    # Bounds: demand_min <= x_i <= demand_max
    bounds = [(DEMAND_MIN[i], DEMAND_MAX[i]) for i in range(n)]

    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")

    if result.status != 0:
        raise RuntimeError(f"Solver failed: {result.message}")

    solution = result.x
    profit   = -result.fun   # negate back
    return solution, profit, result


def compute_slack(solution):
    """Return resource slack (unused capacity) for each constraint."""
    used = {
        "Labor (hrs)":    float(LABOR    @ solution),
        "CNC (hrs)":      float(CNC      @ solution),
        "Assembly (hrs)": float(ASSEMBLY @ solution),
        "Steel (kg)":     float(STEEL    @ solution),
        "Copper (kg)":    float(COPPER   @ solution),
    }
    caps = {
        "Labor (hrs)":    LABOR_CAP,
        "CNC (hrs)":      CNC_CAP,
        "Assembly (hrs)": ASSEMBLY_CAP,
        "Steel (kg)":     STEEL_CAP,
        "Copper (kg)":    COPPER_CAP,
    }
    slack = {k: caps[k] - used[k] for k in used}
    return used, caps, slack


def sensitivity_analysis(solution, base_profit):
    """
    Parametric sensitivity on resource capacities.
    Vary each capacity ±30 % in 7 steps and record optimal profit.
    """
    resources = ["Labor", "CNC", "Assembly", "Steel", "Copper"]
    caps_base = [LABOR_CAP, CNC_CAP, ASSEMBLY_CAP, STEEL_CAP, COPPER_CAP]
    A_rows    = [LABOR, CNC, ASSEMBLY, STEEL, COPPER]

    results = {}
    pct_range = np.linspace(-30, 30, 13)   # -30 … +30 %

    for idx, (res, base_cap, row) in enumerate(zip(resources, caps_base, A_rows)):
        profits = []
        for pct in pct_range:
            new_cap = base_cap * (1 + pct / 100)
            new_b   = [LABOR_CAP, CNC_CAP, ASSEMBLY_CAP, STEEL_CAP, COPPER_CAP]
            new_b[idx] = new_cap

            r = linprog(-PROFIT,
                        A_ub=np.vstack([LABOR, CNC, ASSEMBLY, STEEL, COPPER]),
                        b_ub=new_b,
                        bounds=[(DEMAND_MIN[i], DEMAND_MAX[i]) for i in range(len(SHORT))],
                        method="highs")
            profits.append(-r.fun if r.status == 0 else np.nan)
        results[res] = {"pct": pct_range.tolist(), "profit": profits,
                        "base_cap": base_cap}
    return results


def profit_sensitivity_by_product(solution, base_profit):
    """
    Vary each product's profit coefficient ±40 % and record optimal profit.
    """
    pct_range = np.linspace(-40, 40, 13)
    results = {}

    for idx, name in enumerate(SHORT):
        profits = []
        for pct in pct_range:
            new_profit = PROFIT.copy()
            new_profit[idx] = PROFIT[idx] * (1 + pct / 100)
            r = linprog(-new_profit,
                        A_ub=np.vstack([LABOR, CNC, ASSEMBLY, STEEL, COPPER]),
                        b_ub=[LABOR_CAP, CNC_CAP, ASSEMBLY_CAP, STEEL_CAP, COPPER_CAP],
                        bounds=[(DEMAND_MIN[i], DEMAND_MAX[i]) for i in range(len(SHORT))],
                        method="highs")
            profits.append(-r.fun if r.status == 0 else np.nan)
        results[name] = {"pct": pct_range.tolist(), "profit": profits}
    return results


if __name__ == "__main__":
    sol, profit, res = build_and_solve()
    used, caps, slack = compute_slack(sol)

    print("\n" + "=" * 55)
    print("  OPTIMAL PRODUCTION PLAN")
    print("=" * 55)
    for name, qty in zip(SHORT, sol):
        print(f"  {name:5s}  →  {qty:6.2f}  units/day")
    print(f"\n  Maximum Daily Profit : ₹{profit:,.0f}")
    print("=" * 55)

    print("\n  RESOURCE UTILISATION")
    print("-" * 40)
    for k in used:
        pct = used[k] / caps[k] * 100
        print(f"  {k:<20s}  {used[k]:6.1f} / {caps[k]}  ({pct:.1f}%)")
