import os
import sys
import subprocess

os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")

from tkinter import Tk, ttk, StringVar, Label, Frame, messagebox
from tkinter import PhotoImage

BASE_DIR = os.path.dirname(__file__)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dataset_generator import generate_dataset
from lp_model import (
    build_and_solve,
    compute_slack,
    sensitivity_analysis,
    profit_sensitivity_by_product,
    SHORT,
    PROFIT,
    DEMAND_MIN,
    DEMAND_MAX,
)
from visualizations import (
    chart_optimal_plan,
    chart_resource_utilisation,
    chart_sensitivity_resources,
    chart_sensitivity_profit_coeff,
    chart_historical,
    chart_product_comparison,
)


class FactoryOptimizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Manufacturing Production Optimizer")
        self.root.geometry("1220x820")
        self.root.minsize(1100, 720)
        self.root.configure(bg="#eef4fb")

        self.solution = None
        self.profit = None
        self.used = None
        self.caps = None
        self.slack = None
        self.df = None
        self.chart_path = os.path.join(BASE_DIR, "charts", "1_optimal_plan.png")

        self.create_widgets()
        self.load_default_chart()
        self.run_analysis()

    def create_widgets(self):
        # Top bar
        top = Frame(self.root, bg="#1f3f66", padx=18, pady=14)
        top.pack(fill="x")

        title = Label(
            top,
            text="Smart Manufacturing Production Optimizer",
            bg="#1f3f66",
            fg="white",
            font=("Arial", 18, "bold"),
        )
        title.pack(anchor="w")

        subtitle = Label(
            top,
            text="Factory planning dashboard • LP model • Resource and profit analysis",
            bg="#1f3f66",
            fg="#dfefff",
            font=("Arial", 10),
        )
        subtitle.pack(anchor="w", pady=(4, 0))

        actions = Frame(self.root, bg="#eef4fb", pady=10)
        actions.pack(fill="x")

        ttk.Button(actions, text="Run Analysis", command=self.run_analysis).pack(side="left", padx=(18, 8))
        ttk.Button(actions, text="Open Charts Folder", command=self.open_charts_folder).pack(side="left", padx=8)
        ttk.Button(actions, text="Refresh Chart", command=self.refresh_chart).pack(side="left", padx=8)
        ttk.Button(actions, text="Exit", command=self.root.destroy).pack(side="left", padx=8)

        status_var = StringVar(value="Ready")
        self.status_var = status_var
        status = Label(actions, textvariable=self.status_var, bg="#eef4fb", fg="#1b5e20", font=("Arial", 10, "bold"))
        status.pack(side="right", padx=(0, 18))

        # Main content
        content = Frame(self.root, bg="#eef4fb")
        content.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        left = Frame(content, bg="#ffffff", bd=1, relief="solid")
        left.pack(side="left", fill="y", padx=(0, 12))

        summary_title = Label(left, text="Optimization Summary", bg="#ffffff", font=("Arial", 12, "bold"), pady=8)
        summary_title.pack(fill="x")

        self.metric_labels = {}
        metrics = [
            ("Profit / day", "₹0"),
            ("Binding resource", "-"),
            ("Average daily profit", "₹0"),
            ("Dataset days", "0"),
        ]
        for label_text, value in metrics:
            row = Frame(left, bg="#ffffff", padx=12, pady=8)
            row.pack(fill="x")
            Label(row, text=label_text, bg="#ffffff", font=("Arial", 10), width=20, anchor="w").pack(side="left")
            val = Label(row, text=value, bg="#ffffff", font=("Arial", 10, "bold"), fg="#0e4a84", anchor="e")
            val.pack(side="right", fill="x", expand=True)
            self.metric_labels[label_text] = val

        divider = ttk.Separator(left, orient="horizontal")
        divider.pack(fill="x", pady=10, padx=10)

        table_title = Label(left, text="Recommended Production Mix", bg="#ffffff", font=("Arial", 11, "bold"), pady=6)
        table_title.pack(fill="x")

        cols = ("Product", "Units/day", "Revenue/day")
        tree = ttk.Treeview(left, columns=cols, show="headings", height=8)
        tree.heading("Product", text="Product")
        tree.heading("Units/day", text="Units/day")
        tree.heading("Revenue/day", text="Revenue/day")
        tree.column("Product", width=90, anchor="center")
        tree.column("Units/day", width=80, anchor="center")
        tree.column("Revenue/day", width=100, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.product_tree = tree

        right = Frame(content, bg="#ffffff", bd=1, relief="solid")
        right.pack(side="right", fill="both", expand=True)

        chart_top = Frame(right, bg="#ffffff")
        chart_top.pack(fill="x", padx=10, pady=(10, 0))
        Label(chart_top, text="Chart View", bg="#ffffff", font=("Arial", 12, "bold")).pack(side="left")

        chart_options = [
            "Optimal Production",
            "Resource Utilisation",
            "Resource Sensitivity",
            "Profit Sensitivity",
            "Historical Analysis",
            "Product Comparison",
        ]
        self.chart_var = StringVar(value=chart_options[0])
        cbo = ttk.Combobox(chart_top, textvariable=self.chart_var, values=chart_options, state="readonly", width=24)
        cbo.pack(side="right")
        cbo.bind("<<ComboboxSelected>>", lambda event: self.refresh_chart())

        self.chart_frame = Frame(right, bg="#f5f7fa", bd=1, relief="solid")
        self.chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.chart_label = Label(self.chart_frame, bg="#f5f7fa")
        self.chart_label.pack(fill="both", expand=True, padx=8, pady=8)

        bottom = Frame(self.root, bg="#eef4fb", pady=8)
        bottom.pack(fill="x")

        resource_title = Label(bottom, text="Resource Utilisation", bg="#eef4fb", font=("Arial", 11, "bold"))
        resource_title.pack(anchor="w", padx=18)

        cols2 = ("Resource", "Used", "Capacity", "Slack", "Utilisation")
        resource_tree = ttk.Treeview(bottom, columns=cols2, show="headings", height=6)
        resource_tree.heading("Resource", text="Resource")
        resource_tree.heading("Used", text="Used")
        resource_tree.heading("Capacity", text="Capacity")
        resource_tree.heading("Slack", text="Slack")
        resource_tree.heading("Utilisation", text="Utilisation")
        resource_tree.column("Resource", width=150, anchor="center")
        resource_tree.column("Used", width=90, anchor="center")
        resource_tree.column("Capacity", width=110, anchor="center")
        resource_tree.column("Slack", width=110, anchor="center")
        resource_tree.column("Utilisation", width=120, anchor="center")
        resource_tree.pack(fill="x", padx=18, pady=(0, 10))
        self.resource_tree = resource_tree

    def set_status(self, message, success=True):
        self.status_var.set(message)
        if success:
            self.status_var.set(message)

    def load_default_chart(self):
        self.show_chart(self.chart_path)

    def show_chart(self, image_path):
        if not os.path.exists(image_path):
            placeholder = Label(self.chart_frame, text="No chart available yet. Run the analysis first.", bg="#f5f7fa", fg="#3b3b3b", font=("Arial", 12))
            placeholder.pack(fill="both", expand=True)
            return

        for child in self.chart_frame.winfo_children():
            if child is not self.chart_label:
                child.destroy()

        self.chart_label.configure(image="")
        self.chart_label.image = None

        try:
            img = PhotoImage(file=image_path)
            target_w = 760
            target_h = 450
            img = self.resize_photo(img, target_w, target_h)
            self.chart_label.configure(image=img)
            self.chart_label.image = img
            self.chart_label.pack(fill="both", expand=True, padx=8, pady=8)
        except Exception:
            placeholder = Label(self.chart_frame, text="Unable to display chart image.", bg="#f5f7fa", fg="#3b3b3b", font=("Arial", 12))
            placeholder.pack(fill="both", expand=True)

    def resize_photo(self, img, width, height):
        return img.subsample(max(1, round(img.width() / width)), max(1, round(img.height() / height)))

    def refresh_chart(self):
        chart_map = {
            "Optimal Production": os.path.join(BASE_DIR, "charts", "1_optimal_plan.png"),
            "Resource Utilisation": os.path.join(BASE_DIR, "charts", "2_resource_utilisation.png"),
            "Resource Sensitivity": os.path.join(BASE_DIR, "charts", "3_sensitivity_resources.png"),
            "Profit Sensitivity": os.path.join(BASE_DIR, "charts", "4_sensitivity_profit.png"),
            "Historical Analysis": os.path.join(BASE_DIR, "charts", "5_historical_analysis.png"),
            "Product Comparison": os.path.join(BASE_DIR, "charts", "6_product_comparison.png"),
        }
        selected = self.chart_var.get()
        path = chart_map.get(selected)
        if path:
            self.show_chart(path)

    def open_charts_folder(self):
        charts_dir = os.path.join(BASE_DIR, "charts")
        if not os.path.exists(charts_dir):
            os.makedirs(charts_dir, exist_ok=True)
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", charts_dir], check=True)
            elif os.name == "nt":
                os.startfile(charts_dir)
            else:
                subprocess.run(["xdg-open", charts_dir], check=True)
            self.set_status("Charts folder opened")
        except Exception as exc:
            self.set_status(f"Could not open folder: {exc}", False)

    def run_analysis(self):
        try:
            self.set_status("Generating dataset and running optimization...")
            df = generate_dataset(60)
            self.df = df
            df.to_csv(os.path.join(BASE_DIR, "factory_data.csv"), index=False)

            solution, profit, _ = build_and_solve()
            used, caps, slack = compute_slack(solution)
            sens_r = sensitivity_analysis(solution, profit)
            sens_p = profit_sensitivity_by_product(solution, profit)

            self.solution = solution
            self.profit = profit
            self.used = used
            self.caps = caps
            self.slack = slack

            chart_optimal_plan(solution, profit)
            chart_resource_utilisation(used, caps)
            chart_sensitivity_resources(sens_r, profit)
            chart_sensitivity_profit_coeff(sens_p, profit)
            chart_historical(df)
            chart_product_comparison(solution)

            self.update_summary()
            self.refresh_chart()
            self.set_status("Analysis complete and charts updated")
        except Exception as exc:
            messagebox.showerror("Project run failed", str(exc))
            self.set_status(f"Error: {exc}", False)

    def update_summary(self):
        if self.profit is None or self.solution is None:
            return

        binding = [k for k in self.slack if abs(self.slack[k]) < 0.5]
        binding_label = ", ".join(binding) if binding else "None"

        self.metric_labels["Profit / day"].configure(text=f"₹{self.profit:,.0f}")
        self.metric_labels["Binding resource"].configure(text=binding_label)
        self.metric_labels["Average daily profit"].configure(text=f"₹{self.df['Total_Daily_Profit_INR'].mean():,.0f}")
        self.metric_labels["Dataset days"].configure(text=str(len(self.df)))

        for row in self.product_tree.get_children():
            self.product_tree.delete(row)

        for product, qty, margin in zip(SHORT, self.solution, self.solution * PROFIT):
            self.product_tree.insert("", "end", values=(product, f"{qty:.2f}", f"₹{margin:,.0f}"))

        for row in self.resource_tree.get_children():
            self.resource_tree.delete(row)

        for resource_name in self.used:
            used_val = self.used[resource_name]
            cap_val = self.caps[resource_name]
            slack_val = self.slack[resource_name]
            util = (used_val / cap_val) * 100
            self.resource_tree.insert(
                "",
                "end",
                values=(resource_name, f"{used_val:.1f}", f"{cap_val:.1f}", f"{slack_val:.1f}", f"{util:.1f}%"),
            )


def main():
    root = Tk()
    app = FactoryOptimizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
