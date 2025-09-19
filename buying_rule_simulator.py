import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Title
st.title("SYSPRO Buying Rule Simulator")

# Inputs
st.sidebar.header("Input Parameters")
weekly_demand = st.sidebar.number_input("Weekly Need (pcs)", value=2)
lead_time_days = st.sidebar.number_input("Lead Time (calendar days)", value=80)
delivery_buffer = st.sidebar.number_input("Delivery Buffer (days)", value=15)
ebq = st.sidebar.number_input("Economic Batch Quantity (EBQ)", value=10)
pan_qty = st.sidebar.number_input("Pan Quantity", value=10)
fixed_time_days = st.sidebar.number_input("Fixed Time Period (business days)", value=20)
start_shortage_date = st.sidebar.date_input("First Shortage Date", value=datetime(2026, 3, 20))

# Calculate PO release date
def get_po_date(shortage_date):
    return shortage_date - timedelta(days=delivery_buffer)

# Function to generate 3 PO entries
def generate_po_entries(rule_code):
    rows = []
    shortage_date = start_shortage_date
    for _ in range(3):
        if rule_code == "A":
            qty = weekly_demand
        elif rule_code == "B":
            qty = ebq
        elif rule_code == "C":
            qty = (fixed_time_days // 5) * weekly_demand
        elif rule_code == "D":
            qty = 100 + weekly_demand
        elif rule_code == "E":
            qty = 200 - 12  # Simulating Min = 50, Max = 200, Available = 12
        elif rule_code == "F":
            qty = pan_qty
        elif rule_code == "G":
            shortage = weekly_demand * 2 + 1  # Simulate larger shortage
            lots = -(-shortage // ebq)  # Ceiling division
            qty = lots * ebq
        elif rule_code == "H":
            shortage = weekly_demand * 2 + 1
            lots = -(-shortage // pan_qty)
            qty = lots * pan_qty
        elif rule_code == "I":
            qty = ebq
        elif rule_code == "J":
            qty = pan_qty
        elif rule_code == "K":
            qty = ebq
        elif rule_code == "L":
            qty = pan_qty
        elif rule_code == "M":
            shortage = weekly_demand * 2 + 1
            lots = -(-shortage // ebq)
            qty = lots * ebq
        elif rule_code == "N":
            shortage = weekly_demand * 2 + 1
            lots = -(-shortage // pan_qty)
            qty = lots * pan_qty
        elif rule_code == "O":
            base = ebq
            remainder = weekly_demand * 2 + 3 - base
            lots = -(-remainder // pan_qty)
            qty = base + lots * pan_qty
        else:
            qty = 0
        po_date = get_po_date(shortage_date)
        rows.append({
            "Buying Rule": rule_code,
            "PO Date": po_date.strftime("%Y-%m-%d"),
            "Order Qty": qty
        })
        shortage_date += timedelta(weeks=4)
    return rows

# Generate table
rules = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O']
all_entries = []
for rule in rules:
    all_entries.extend(generate_po_entries(rule))

# Display table
df = pd.DataFrame(all_entries)
st.dataframe(df)
