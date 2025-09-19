import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import math

# --- Buying Rule Definitions (A–Q) ---
rule_definitions = {
    "A": "Lot for lot – The order quantity is the shortage quantity. Sub-jobs are created lot for lot. Typically used when first implementing MRP.",
    "B": "Multiples of EBQ – Shortage is rounded up to the next multiple of the Economic Batch Quantity (EBQ).",
    "C": "Fixed time period – Orders consolidate all shortages in a fixed time period into one order.",
    "D": "Order to maximum if shortage – Orders enough to bring stock to the defined maximum when a shortage occurs.",
    "E": "Order to max if less than min – If stock falls below the minimum, order enough to bring it up to maximum.",
    "F": "Multiples of pan – Same as EBQ rule, but uses pan size instead of EBQ.",
    "G": "Multiple EBQ lots – Creates multiple orders of EBQ size to cover a shortage.",
    "H": "Multiple pan lots – Same as rule G but uses pan size.",
    "I": "Min of EBQ – Orders shortage qty unless below EBQ, in which case EBQ is used.",
    "J": "Minimum of pan – Same as rule I but uses pan size.",
    "K": "Multiples of EBQ fixed time – Combination of EBQ and Fixed Time rules.",
    "L": "Multiples of pan fixed time – Same as rule K but with pan size.",
    "M": "Multiple EBQ lots fixed time – Combines multiple EBQs with fixed time consolidation.",
    "N": "Multiple pan lots fixed time – Same as rule M but with pan size.",
    "O": "Min of EBQ thereafter multiples of pan – Orders at least EBQ, then remainder in pan multiples.",
    "P": "Suppress MRP ordering – No replenishment suggested unless overridden. Often used for by-products.",
    "Q": "Apply warehouse order policy – Uses warehouse-defined order policies for calculation."
}

# --- Streamlit UI ---
st.title("SYSPRO Buying Rule Simulator")

# Sidebar inputs
st.sidebar.header("Input Parameters")
weekly_demand = st.sidebar.number_input("Weekly Need (pcs)", value=2)
lead_time_days = st.sidebar.number_input("Lead Time (calendar days)", value=80)
delivery_buffer = st.sidebar.number_input("Delivery Buffer (days)", value=15)
ebq = st.sidebar.number_input("Economic Batch Quantity (EBQ)", value=10)
pan_qty = st.sidebar.number_input("Pan Quantity", value=10)
fixed_time_days = st.sidebar.number_input("Fixed Time Period (business days)", value=20)
start_shortage_date = st.sidebar.date_input("First Shortage Date", value=datetime(2026, 3, 20))

# --- Rule Definitions Section ---
st.header("📘 Buying Rule Definitions")
selected_rule = st.selectbox("Select a Buying Rule to view its definition", list(rule_definitions.keys()))
st.info(f"**{selected_rule}**: {rule_definitions[selected_rule]}")

# --- Helper: Generate 3 PO entries ---
def generate_po_entries(rule_code, qty):
    rows = []
    shortage_date = start_shortage_date
    for _ in range(3):
        po_date = shortage_date - timedelta(days=delivery_buffer)
        rows.append({
            "Buying Rule": rule_code,
            "PO Date": po_date.strftime("%Y-%m-%d"),
            "Order Qty": qty
        })
        shortage_date += timedelta(weeks=4)  # assume monthly cycle
    return rows

# --- Quantities for Rules A–Q ---
rules = {
    "A": weekly_demand,
    "B": ebq,
    "C": (fixed_time_days // 5) * weekly_demand,
    "D": 100 + weekly_demand,
    "E": 200 - 12,  # Example Min/Max logic
    "F": pan_qty,
    "G": math.ceil((weekly_demand * 2 + 1) / ebq) * ebq,
    "H": math.ceil((weekly_demand * 2 + 1) / pan_qty) * pan_qty,
    "I": max(ebq, weekly_demand),
    "J": max(pan_qty, weekly_demand),
    "K": ebq,
    "L": pan_qty,
    "M": math.ceil((weekly_demand * 2 + 1) / ebq) * ebq,
    "N": math.ceil((weekly_demand * 2 + 1) / pan_qty) * pan_qty,
    "O": ebq + math.ceil((weekly_demand * 2 + 3 - ebq) / pan_qty) * pan_qty,
    "P": 0,  # No replenishment
    "Q": 0   # Depends on warehouse config
}

# --- Simulation Results ---
st.header("📊 PO Simulation Results")
all_entries = []
for r, q in rules.items():
    if q > 0:
        all_entries.extend(generate_po_entries(r, q))

df = pd.DataFrame(all_entries)
st.dataframe(df)

# --- Summary Cost/Efficiency Table ---

# Cost assumptions
part_price = 50        # $/unit
buyer_rate = 35        # $/hour
time_per_po = 0.5      # hours
cost_per_po = buyer_rate * time_per_po

# Calculate summary table
summary_data = []

for rule, qty in rules.items():
    if qty <= 0:
        summary_data.append({
            "Rule": rule,
            "Description": rule_definitions.get(rule, ""),
            "Order Qty (per shortage)": 0,
            "POs/year": 0,
            "Holding Cost/year": 0,
            "Buyer Cost/year": 0,
            "Total Annual Cost": 0,
            "Notes": "No auto ordering (manual)"
        })
        continue

    # Assume weekly demand = 2 pcs, 52 weeks
    annual_demand = weekly_demand * 52
    orders_per_year = math.ceil(annual_demand / qty)

    # Avg inventory = half order qty
    avg_inventory = qty / 2
    holding_cost = avg_inventory * part_price
    buyer_cost = orders_per_year * cost_per_po
    total_cost = holding_cost + buyer_cost

    # Notes based on rule type
    notes = "Balanced" if rule in ["B","C","F","G","H","I","J","K","L","M","N","O"] else \
            "High PO load" if rule == "A" else \
            "No auto ordering" if rule in ["P","Q"] else \
            "High inventory"

    # --- Cost Model Inputs ---
    st.header("⚙️ Cost Model Parameters")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        part_price = st.number_input("Part Price ($/unit)", value=50, min_value=1)
    with col2:
        buyer_rate = st.number_input("Buyer Rate ($/hour)", value=35, min_value=1)
    with col3:
        time_per_po = st.number_input("Time per PO (hours)", value=0.5, step=0.1)
    
    cost_per_po = buyer_rate * time_per_po

# --- Summary Cost/Efficiency Table ---
summary_data = []

for rule, qty in rules.items():
    if qty <= 0:
        summary_data.append({
            "Rule": rule,
            "Description": rule_definitions.get(rule, ""),
            "Order Qty (per shortage)": 0,
            "POs/year": 0,
            "Holding Cost/year": "$0",
            "Buyer Cost/year": "$0",
            "Total Annual Cost": "$0",
            "Notes": "No auto ordering (manual)"
        })
        continue

    # Annual demand
    annual_demand = weekly_demand * 52
    orders_per_year = math.ceil(annual_demand / qty)

    # Costs
    avg_inventory = qty / 2
    holding_cost = avg_inventory * part_price
    buyer_cost = orders_per_year * cost_per_po
    total_cost = holding_cost + buyer_cost

    # Notes
    notes = "Balanced" if rule in ["B","C","F","G","H","I","J","K","L","M","N","O"] else \
            "High PO load" if rule == "A" else \
            "No auto ordering" if rule in ["P","Q"] else \
            "High inventory"

    summary_data.append({
        "Rule": rule,
        "Description": rule_definitions.get(rule, ""),
        "Order Qty (per shortage)": f"{qty} pcs",
        "POs/year": orders_per_year,
        "Holding Cost/year": f"${holding_cost:,.0f}",
        "Buyer Cost/year": f"${buyer_cost:,.0f}",
        "Total Annual Cost": f"**${total_cost:,.0f}**",
        "Notes": notes
    })

summary_df = pd.DataFrame(summary_data)

st.header("📊 Summary of Costs & Efficiency")
st.dataframe(summary_df)

