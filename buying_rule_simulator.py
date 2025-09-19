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
st.set_page_config(page_title="SYSPRO Buying Rule Simulator", layout="wide")
st.title("✈️ SYSPRO Buying Rule Simulator")

# Sidebar: Inputs
st.sidebar.header("🔧 Variables")
lead_time_days = st.sidebar.number_input("Lead Time (days)", value=80, min_value=1)
ebq = st.sidebar.number_input("Economic Batch Quantity (EBQ)", value=10, min_value=1)
pan_qty = st.sidebar.number_input("Pan Quantity", value=10, min_value=1)
fixed_time_days = st.sidebar.number_input("Fixed Time Period (business days)", value=20, min_value=5)
start_shortage_date = st.sidebar.date_input("First Shortage Date", value=datetime(2026, 3, 20))
yearly_ac_demand = st.sidebar.number_input("Yearly A/C Demand (pcs)", value=100, min_value=1, key="yearly_demand")
qty_per_ac = st.sidebar.number_input("Quantity per A/C", value=2, min_value=1, key="qty_per_ac")
time_per_po = st.sidebar.number_input("Time per PO (hrs)", value=0.5, min_value=0.1, step=0.1)

st.sidebar.header("📌 Constants")
delivery_buffer = 15
buyer_rate = 35
part_price = 50
st.sidebar.write(f"Delivery Buffer (days): **{delivery_buffer}**")
st.sidebar.write(f"Buyer Rate: **${buyer_rate}/hr**")
st.sidebar.write(f"Part Cost: **${part_price}/unit**")

# Derived weekly demand
weekly_demand = math.ceil(yearly_ac_demand / 52)

# --- Helper: Generate 3 PO Dates with Qty ---
def get_po_schedule(start_date, delivery_buffer, qty):
    rows = []
    shortage_date = start_date
    for _ in range(3):
        po_date = shortage_date - timedelta(days=delivery_buffer)
        rows.append(f"{po_date.strftime('%Y-%m-%d')} → {int(qty)} pcs")
        shortage_date += timedelta(weeks=4)  # assume monthly cycle
    return "\n".join(rows)

# --- Quantities for Rules A–Q ---
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

# --- Cost model constants ---
cost_per_po = buyer_rate * time_per_po

# --- Build Combined Summary ---
combined_data = []
for rule, qty in rules.items():
    if qty <= 0:
        combined_data.append({
            "Rule": rule,
            "Description": rule_definitions.get(rule, ""),
            "Example Order Qty": 0,
            "POs/year": 0,
            "PO Schedule (next 3)": "-",
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
        "PO Schedule (next 3)": get_po_schedule(start_shortage_date, delivery_buffer, qty),
        "Holding Cost/year": f"${int(holding_cost):,}",
        "Buyer Cost/year": f"${int(buyer_cost):,}",
        "Total Annual Cost": f"${int(total_cost):,}",
        "Notes": notes
    })

combined_df = pd.DataFrame(combined_data)

# --- Tabs ---
tab1, tab2 = st.tabs(["📊 Simulator", "📘 Rule Reference"])

# --- Tab 1: Simulator ---
with tab1:
    st.header("📊 Combined Buying Rule Summary")

    # Force text wrapping
    st.markdown("""
        <style>
        .dataframe td {
            white-space: normal !important;
            word-wrap: break-word !important;
            max-width: 300px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.dataframe(combined_df, use_container_width=True)

    # --- Downloads ---
    st.subheader("⬇️ Download Results")
    csv = combined_df.to_csv(index=False).encode("utf-8")
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        combined_df.to_excel(writer, index=False, sheet_name="BuyingRules")
        params = {
            "Lead Time (days)": lead_time_days,
            "Delivery Buffer (days)": delivery_buffer,
            "Economic Batch Quantity (EBQ)": ebq,
            "Pan Quantity": pan_qty,
            "Fixed Time Period (business days)": fixed_time_days,
            "First Shortage Date": start_shortage_date.strftime("%Y-%m-%d"),
            "Yearly A/C Demand": yearly_ac_demand,
            "Quantity per A/C": qty_per_ac,
            "Buyer Rate ($/hr)": buyer_rate,
            "Time per PO (hrs)": time_per_po,
            "Part Cost ($/unit)": part_price,
        }
        params_df = pd.DataFrame(list(params.items()), columns=["Parameter", "Value"])
        params_df.to_excel(writer, index=False, sheet_name="Variables_Constants")

    st.download_button("Download as CSV", csv, "BuyingRulesSummary.csv", "text/csv")
    st.download_button(
        "Download as Excel",
        excel_buffer.getvalue(),
        "BuyingRulesSummary.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# --- Tab 2: Rule Reference ---
with tab2:
    st.header("📘 SYSPRO Buying Rules – Summary Table")

    summary_data = [
        ["A", "Lot for Lot", "Orders exactly the shortage qty (or MOQ).", "Low inventory holding.", "Very high PO frequency, heavy admin."],
        ["B", "Multiples of EBQ", "Shortage rounded up to next EBQ multiple.", "Efficient batching, fewer POs.", "May over-order slightly."],
        ["C", "Fixed Time Period", "Combine shortages in a time window into one order.", "Matches time buckets, reduces noise.", "May mismatch if demand shifts."],
        ["D", "Order to Max if Shortage", "Fills shortage + tops up to max level.", "Very few POs.", "High holding cost."],
        ["E", "Order to Max if < Min", "If stock < min, top up to max.", "Safety buffer guaranteed.", "Can create excess inventory."],
        ["F", "Multiples of Pan", "Same as EBQ but pan size.", "Aligns to pan sizes.", "Over-order risk if demand < pan."],
        ["G", "Multiple EBQ Lots", "Creates multiple EBQ orders.", "Respects EBQ constraints.", "Many PO lines."],
        ["H", "Multiple Pan Lots", "Same as G but pan size.", "Pan alignment.", "High admin overhead."],
        ["I", "Min of EBQ", "Shortage or EBQ (whichever is larger).", "Prevents tiny orders.", "Still frequent if lumpy demand."],
        ["J", "Min of Pan", "Same as I but pan size.", "Matches pan rules.", "Same as I."],
        ["K", "Mult EBQ + Fixed Time", "Combine shortages, round up to EBQ.", "Balanced time + batching.", "Possible over-ordering."],
        ["L", "Mult Pan + Fixed Time", "Same as K but pan size.", "Smooth production cycles.", "Same limitation as K."],
        ["M", "Mult EBQ Lots + Fixed Time", "Combine shortages, split into EBQ lots.", "Predictable cycle.", "Many PO lines per bucket."],
        ["N", "Mult Pan Lots + Fixed Time", "Same as M but pan.", "Pan + time aligned.", "High admin overhead."],
        ["O", "Min EBQ + Mult of Pan", "At least EBQ, remainder in pan multiples.", "Handles mixed demand well.", "Logic complexity."],
        ["P", "Suppress MRP Ordering", "No auto replenishment.", "Manual control only.", "Stockout risk."],
        ["Q", "Apply Warehouse Policy", "Warehouse-defined order rules.", "Flexibility per site.", "Setup complexity."]
    ]
    st.markdown("""
        <style>
        .dataframe td {
            white-space: normal !important;
            word-wrap: break-word !important;
            max-width: 250px;
        }
        </style>
    """, unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(summary_data, columns=["Rule", "Name / Description", "How it Works", "Pros", "Cons"]), use_container_width=True)

    st.markdown("### 🛠️ How to Use This")
    st.markdown("""
    - **A (Lot for Lot):** Best when first implementing MRP.  
    - **B, C, K, L:** Good balance between batch efficiency and fewer POs.  
    - **D, E:** Use if you want fewer POs but can tolerate high inventory.  
    - **G, H, M, N:** Careful – can generate too many PO lines.  
    - **O:** Flexible for mixed demand patterns.  
    - **P:** Manual control – use for by-products/non-critical.  
    - **Q:** Best if warehouses need flexibility with local policies.  
    """)

    with st.expander("📖 Full Rule Explanations (click to expand)"):
        for r, desc in rule_definitions.items():
            st.markdown(f"**{r}** – {desc}")

