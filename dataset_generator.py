"""
=============================================================
  Smart Manufacturing Production Optimizer
  MODULE 1: Dataset Generator
  Generates 60 days of simulated factory production data
=============================================================
"""

import pandas as pd
import numpy as np
import os

np.random.seed(42)

BASE_DIR = os.path.dirname(__file__)
prod_df = pd.read_csv(os.path.join(BASE_DIR, "product_data.csv"))

PRODUCTS = prod_df["Product_Full_Name"].str.replace(" ", "_").tolist()

# Base production quantities (units/day) per product
BASE_PRODUCTION = prod_df["Base_Production"].tolist()

# Profit per unit (INR)
PROFIT_PER_UNIT = prod_df["Profit"].tolist()

# Resource usage per unit
LABOR_PER_UNIT    = prod_df["Labor_Usage"].tolist()
CNC_PER_UNIT      = prod_df["CNC_Usage"].tolist()
ASSEMBLY_PER_UNIT = prod_df["Assembly_Usage"].tolist()
STEEL_PER_UNIT    = prod_df["Steel_Usage"].tolist()
COPPER_PER_UNIT   = prod_df["Copper_Usage"].tolist()


def generate_dataset(n_days=60):
    records = []

    for day in range(1, n_days + 1):
        # Simulate day-of-week effect (lower production on Mon/Fri)
        dow = (day - 1) % 5  # 0=Mon … 4=Fri
        efficiency = 0.88 if dow in [0, 4] else 1.00

        # Available resources that day (slight daily variation)
        labor_avail    = np.random.normal(480, 15) * efficiency
        cnc_avail      = np.random.normal(300, 10) * efficiency
        assembly_avail = np.random.normal(240,  8) * efficiency
        steel_avail    = np.random.normal(1200, 40)
        copper_avail   = np.random.normal(400,  15)

        # Actual units produced (add noise)
        prod = [max(0, int(np.random.normal(base * efficiency, base * 0.12)))
                for base in BASE_PRODUCTION]

        # Compute resource consumption
        labor_used    = sum(p * r for p, r in zip(prod, LABOR_PER_UNIT))
        cnc_used      = sum(p * r for p, r in zip(prod, CNC_PER_UNIT))
        assembly_used = sum(p * r for p, r in zip(prod, ASSEMBLY_PER_UNIT))
        steel_used    = sum(p * r for p, r in zip(prod, STEEL_PER_UNIT))
        copper_used   = sum(p * r for p, r in zip(prod, COPPER_PER_UNIT))

        total_profit = sum(p * pr for p, pr in zip(prod, PROFIT_PER_UNIT))

        # Demand satisfaction flag
        demand_met = all(p >= int(base * 0.6)
                         for p, base in zip(prod, BASE_PRODUCTION))

        record = {
            "Day": day,
            "Day_of_Week": ["Mon", "Tue", "Wed", "Thu", "Fri"][dow],
            "Shift_Efficiency_%": round(efficiency * 100, 1),
        }
        for i, name in enumerate(PRODUCTS):
            record[f"Units_{name}"] = prod[i]
        record.update({
            "Labor_Available_hrs":    round(labor_avail, 1),
            "Labor_Used_hrs":         round(labor_used, 1),
            "Labor_Utilization_%":    round(labor_used / labor_avail * 100, 1),
            "CNC_Available_hrs":      round(cnc_avail, 1),
            "CNC_Used_hrs":           round(cnc_used, 1),
            "CNC_Utilization_%":      round(cnc_used / cnc_avail * 100, 1),
            "Assembly_Available_hrs": round(assembly_avail, 1),
            "Assembly_Used_hrs":      round(assembly_used, 1),
            "Assembly_Util_%":        round(assembly_used / assembly_avail * 100, 1),
            "Steel_Available_kg":     round(steel_avail, 1),
            "Steel_Used_kg":          round(steel_used, 1),
            "Steel_Utilization_%":    round(steel_used / steel_avail * 100, 1),
            "Copper_Available_kg":    round(copper_avail, 1),
            "Copper_Used_kg":         round(copper_used, 1),
            "Copper_Utilization_%":   round(copper_used / copper_avail * 100, 1),
            "Total_Daily_Profit_INR": total_profit,
            "Demand_Met":             demand_met,
        })
        records.append(record)

    df = pd.DataFrame(records)
    return df


if __name__ == "__main__":
    df = generate_dataset(60)
    print(f"Dataset shape: {df.shape}")
    print(df.head(3).to_string())
    df.to_csv(os.path.join(BASE_DIR, "factory_data.csv"), index=False)
    print("\n✓ Dataset saved to factory_data.csv")
