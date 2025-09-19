import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import math
import io

# --- Buying Rule Definitions (A–Q) ---
rule_definitions = {
    "A": "Lot for lot – Order the exact shortage qty. Typically used when first implementing MRP.",
    "B": "Multiples of EBQ – Round shortage up to the next multiple of the Economic Batch Quantity (EBQ).",
    "C": "Fixed time period – Consolidate all shortages in a fixed time period into one order.",
    "D": "Order to maximum if shortage – When shortage occurs, order up to the maximum warehouse qty.",
    "E": "Order to max if < min – If stock falls below minimum, order enough to bring it up to maximum.",
    "F": "Multiples of pan – Same as EBQ rule but uses pan size instead.",
    "G": "Multiple EBQ lots – Creates multiple orders of EBQ size to cover a shortage.",
    "H": "Multiple pan lots – Same as rule G but uses pan size.",
    "I": "Min of EBQ – Orders shortage qty unless it’s below EBQ, then EBQ is used.",
    "J": "Minimum of pan – Same as rule I but uses pan size.",
    "K": "Multiples of EBQ fixed time – Combine shortages over time, round up to EBQ.",
    "L": "Multiples of pan fixed time – Same as rule K but uses pan size.",
    "M": "Multiple EBQ lots fixed time – Combine shortages, split into EBQ-sized lots.",
    "N": "Multiple pan lots fixed time – Same as M but uses pan size.",
    "O": "Min EBQ + multiples of pan – At least EBQ, remainder rounded up in pan multiples.",
    "P": "Suppress MRP ordering – No replenishment unless overridden. Often for by-products.",
    "Q": "Apply warehouse order policy – Uses warehouse-defined policies for calculation."
}

# --- Streamlit UI ---
st.title("SYSPRO Buying Rule Simulator")

# Sidebar inputs for PO simulation
st.sidebar.header("🔧 Simulation Parameters")
lead_time_days = st.sidebar.number_input("Lead Time (days)", value=80, min_value=1)
delivery_buffer = st.sidebar.number_input("Delivery Buffer (days)", value=15, min_value=1)
ebq = st.sidebar.number_input("Economic Batch Quantity (EBQ)", value=10, min_value=1)
pan_qty = st.sidebar.number_input("Pan Quantity", value=10, min_value=1)
fixed_time_days = st.sidebar.number_input("Fixed Time Period (business days)", value=20, min_value=5)
start_shortage_date = st.sidebar.date_input("First Shortage Date", value=datetime(2026, 3, 20))

# --- Demand Parameters ---
st.header("📦 Demand Parameters")
col1, col2 = st.columns(2)
with col1:
    yearly_ac_demand = st.number_input("Yearly A/C Demand (pcs)", value=100, min_value=1, key="yearly_demand")
with col2:
    qty_per_ac = st.number_input("Quantity per A/C", value=2, min_value=1, key="qty_per_ac")

# Derived weekly demand (always integer for PO calcs)
weekly_demand = math.ceil(yearly_ac_demand / 52)
st.markdown(f"➡️ Calculated **Weekly Demand = {weekly_demand} pcs** (from {yearly_ac_demand} yearly / 52 weeks)")

# --- Rule Definitions Section ---
st.header("📘 Buying Rule Definitions")
selected_rule = st.selectbox("Select a Buying Rule to view its definition", list(rule_definitions.keys()))
st.info(f"**{selected_rule}**: {rule_definitions[selected_rule]}")

# --- Helper: Generate 3 PO Dates ---
def get_po_dates(start_date, delivery_buffer):
    dates = []
    shortage_date = start_date
    for _ in range(3):
        po_date = shortage_date - timedelta(days=delivery_buffer)
        dates.append(po_date.strftime("%Y-%m-%d"))
        shortage_date += timedelta(weeks=4)  # assume monthly cycle
    return ", ".join(dates)

# --- Quantities for Rules A–Q (rounded to integers) ---
rules = {
    "A": weekly_demand,
    "B": ebq,
    "C": math.ceil((fixed_time_days // 5) * weekly_demand),
    "D": 100 + weekly_demand,
    "E": 200 - 12,
    "F": pan_qty,
    "G": math.ceil((weekly_demand * 2 + 1) / ebq) * ebq,
    "H": math.ceil((weekly_demand * 2 + 1) / pan_qty) * pan_qty,
    "I": max(ebq, weekly_demand),
    "J": max(pan_qty, weekly_demand),
    "K": ebq,
    "L": pan_qty,
    "M": math.ceil((weekly_demand * 2 + 1) / ebq) * ebq,
    "N": math.ceil((weekly_demand * 2 + 1) / pan_qty) * pan_qty,
    "O": ebq + math.ceil(max(0, (weekly_demand * 2 + 3 - ebq)) / pan_qty) * pan_qty,
    "P": 0,
    "Q": 0
}

# --- Constants for Cost Model ---
st.subheader("Constants (fixed values)")
st.markdown("""
- **Buyer Price:** $35/hour (≈ $17.50 per PO at 0.5 hr/PO)  
- **Part Cost:** $50/unit  
""")

buyer_rate = 35
time_per_po = 0.5
part_price = 50
cost_per_po = buyer_rate * time_per_po

# --- Combined Summary Table ---
combined_data = []

for rule, qty in rules.items():
    if qty <= 0:
        combined_data.append({
            "Rule": rule,
            "Description": rule_definitions.get(rule, ""),
            "Example Order Qty": 0,
            "POs/year": 0,
            "PO Dates (next 3)": "-",
            "Holding Cost/year": "$0",
            "Buyer Cost/year": "$0",
            "Total Annual Cost": "$0",
            "Notes": "No auto ordering (manual)"
        })
        continue

    annual_demand = yearly_ac_demand
    orders_per_year = math.ceil(annual_demand / qty)

    avg_inventory = qty / 2
    holding_cost = avg_inventory * part_price
    buyer_cost = orders_per_year * cost_per_po
    total_cost = holding_cost + buyer_cost

    notes = "Balanced" if rule in ["B","C","F","G","H","I","J","K","L","M","N","O"] else \
            "High PO load" if rule == "A" else \
            "No auto ordering" if rule in ["P","Q"] else \
            "High inventory"

    combined_data.append({
        "Rule": rule,
        "Description": rule_definitions.get(rule, ""),
        "Example Order Qty": f"{int(qty)} pcs",
        "POs/year": int(orders_per_year),
        "PO Dates (next 3)": get_po_dates(start_shortage_date, delivery_buffer),
        "Holding Cost/year": f"${int(holding_cost):,}",
        "Buyer Cost/year": f"${int(buyer_cost):,}",
        "Total Annual Cost": f"**${int(total_cost):,}**",
        "Notes": notes
    })

combined_df = pd.DataFrame(combined_data)

st.header("📊 Combined Buying Rule Summary")
st.dataframe(combined_df)

# --- Download Buttons ---
st.subheader("⬇️ Download Results")
csv = combined_df.to_csv(index=False).encode('utf-8')
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:  # openpyxl avoids install issues
    combined_df.to_excel(writer, index=False, sheet_name="BuyingRules")

st.download_button(
    label="Download as CSV",
    data=csv,
    file_name="BuyingRulesSummary.csv",
    mime="text/csv"
)

st.download_button(
    label="Download as Excel",
    data=excel_buffer.getvalue(),
    file_name="BuyingRulesSummary.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
