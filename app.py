import streamlit as st
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh

# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="ZWARK | Textile Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# DASHBOARD STYLING (dark metrics)
# =========================================================
st.markdown("""
<style>
.block-container {
    max-width: 100%;
    padding: 1rem 2rem;
}
h1 { font-size: 1.6rem !important; }
h2, h3 { margin-top: 0.4rem !important; }
div[data-testid="stMetric"] {
    background-color: #111c30;
    border: 1px solid #25334b;
    border-radius: 10px;
    padding: 12px;
}
div[data-testid="stMetric"] [data-testid="stMetricLabel"],
div[data-testid="stMetric"] [data-testid="stMetricLabel"] * {
    color: #cbd5e1 !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"],
div[data-testid="stMetric"] [data-testid="stMetricValue"] * {
    color: #ffffff !important;
}
div[data-testid="stTabs"] button { font-size: 1rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# LIVE SIMULATION CONTROL
# =========================================================

if "sim_step" not in st.session_state:
    st.session_state.sim_step = 0
if "sim_running" not in st.session_state:
    st.session_state.sim_running = True
if "production_history" not in st.session_state:
    st.session_state.production_history = []
if "loom_history" not in st.session_state:
    st.session_state.loom_history = []
if "status_history" not in st.session_state:
    st.session_state.status_history = []

SHIFT_HOURS = 8
SHIFT_MINUTES = SHIFT_HOURS * 60
SIM_DATE = "2026-11-12"

if st.session_state.sim_running:
    st_autorefresh(interval=3000, key="live_refresh")
    if st.session_state.sim_step < SHIFT_MINUTES:
        st.session_state.sim_step += 1

sim_min = min(st.session_state.sim_step, SHIFT_MINUTES)
sim_hr = 8 + sim_min // 60
sim_minute = sim_min % 60

# =========================================================
# HEADER AND CONTROLS
# =========================================================

header_col, clock_col = st.columns([4, 1])
with header_col:
    st.title("ZWARK | Textile Intelligence")
    st.caption("Live Loom Data • Inventory • Quality • Traceability")
with clock_col:
    st.metric("Simulation Time", f"{sim_hr:02d}:{sim_minute:02d}")

ctrl1, ctrl2, ctrl3 = st.columns([1,1,5])
with ctrl1:
    if st.button("Pause" if st.session_state.sim_running else "Resume", use_container_width=True):
        st.session_state.sim_running = not st.session_state.sim_running
        st.rerun()
with ctrl2:
    if st.button("Restart", use_container_width=True):
        st.session_state.sim_step = 0
        st.session_state.sim_running = True
        st.session_state.production_history = []
        st.session_state.loom_history = []
        st.session_state.status_history = []
        st.rerun()
with ctrl3:
    progress = st.progress(sim_min / SHIFT_MINUTES if SHIFT_MINUTES else 0)
    st.caption(f"{sim_min} of {SHIFT_MINUTES} simulated minutes")

# =========================================================
# 1. YARN BATCHES (Inventory Setup)
# =========================================================

yarn_batches = pd.DataFrame({
    "Yarn Batch": ["YB-001", "YB-002", "YB-003", "YB-004"],
    "Supplier": ["ABC Yarn Mills", "Prime Spinners", "National Yarn Co.", "ABC Yarn Mills"],
    "Yarn Type": ["Cotton 30s", "Cotton 40s", "Cotton 30s", "Cotton 40s"],
    "Opening Stock (kg)": [500.0, 350.0, 400.0, 300.0]
})

# =========================================================
# 2. WARPING AND SIZING DATA
# =========================================================

warp_beams = pd.DataFrame({
    "Beam ID": [f"B-{i:03d}" for i in range(101, 111)],
    "Warp Yarn Batch": ["YB-001", "YB-002", "YB-003", "YB-001", "YB-004",
                        "YB-002", "YB-003", "YB-004", "YB-001", "YB-002"],
    "Sizing Add-on (%)": [10.5, 9.2, 11.0, 10.1, 8.8, 9.5, 10.8, 9.1, 10.3, 9.7],
    "Warp Tension (N)":    [25, 28, 24, 26, 30, 27, 25, 29, 26, 28],
    "Warping End Breaks":  [ 3, 12,  4,  5, 15, 10,  3, 14,  4, 11]
})

# =========================================================
# 3. LOOM ASSIGNMENTS
# =========================================================

loom_ids = [f"L-{i:02d}" for i in range(1, 11)]
rng = np.random.default_rng(42)

assigned_beams = rng.permutation(warp_beams["Beam ID"].to_numpy())
weft_batches = rng.choice(yarn_batches["Yarn Batch"].to_numpy(), size=len(loom_ids))

loom_assign = pd.DataFrame({
    "Loom ID": loom_ids,
    "Beam ID": assigned_beams,
    "Weft Yarn Batch": weft_batches,
    "Shift": ["Day"] * len(loom_ids)
})

# Merge to get warp yarn batch and warping break count per loom
loom_assign = loom_assign.merge(
    warp_beams,
    on="Beam ID",
    how="left",
    validate="many_to_one"
)

# =========================================================
# 4. STOPPAGE SIMULATION (pre-compute all stops)
# =========================================================

stoppages = []
for _, loom in loom_assign.iterrows():
    lid = loom["Loom ID"]
    beam = loom["Beam ID"]
    pre_breaks = int(loom["Warping End Breaks"])

    warp_stops = int(rng.integers(2, 6) + pre_breaks // 4)
    weft_stops = int(rng.integers(1, 6))
    mech_stops = int(rng.integers(0, 3))

    for reason, count in zip(["Warp Break", "Weft Break", "Mechanical"], [warp_stops, weft_stops, mech_stops]):
        for _ in range(count):
            duration = int(rng.integers(1, 7)) if reason == "Warp Break" else (int(rng.integers(1, 4)) if reason == "Weft Break" else int(rng.integers(8, 31)))
            start_min = int(rng.integers(0, SHIFT_MINUTES))
            stoppages.append({
                "Loom ID": lid,
                "Beam ID": beam,
                "Stop Reason": reason,
                "Minute of Shift": start_min,
                "Downtime (min)": min(duration, SHIFT_MINUTES - start_min)
            })

stoppages = pd.DataFrame(stoppages)
stoppages = stoppages[stoppages["Minute of Shift"] < SHIFT_MINUTES]
stoppages = stoppages.sort_values(["Minute of Shift", "Loom ID"]).reset_index(drop=True)
stoppages["Time"] = pd.to_datetime(SIM_DATE + " 08:00") + pd.to_timedelta(stoppages["Minute of Shift"], unit='m')

# =========================================================
# 5. LIVE PRODUCTION CALCULATIONS
# =========================================================

production = loom_assign.copy()
production["Speed (PPM)"] = rng.integers(450, 650, size=len(production))
production["Picks per Inch"] = rng.choice([60, 70, 80], size=len(production))

# Count unique stopped minutes; overlapping events cannot double-count downtime.
elapsed = sim_min
downtime_by_loom = {}
for lid in production["Loom ID"]:
    stopped_minutes = set()
    breaks = stoppages[stoppages["Loom ID"] == lid]
    for _, stop in breaks.iterrows():
        start = int(stop["Minute of Shift"])
        end = min(elapsed, start + int(stop["Downtime (min)"]))
        stopped_minutes.update(range(start, max(start, end)))
    downtime_by_loom[lid] = len(stopped_minutes)

production["Live Downtime (min)"] = production["Loom ID"].map(downtime_by_loom)
production["Running Minutes"] = (elapsed - production["Live Downtime (min)"]).clip(lower=0)
production["Live Actual Picks"] = (production["Speed (PPM)"] * production["Running Minutes"]).astype(int)
production["Fabric Produced (m)"] = (production["Live Actual Picks"] / production["Picks per Inch"] / 39.37).round(2)
if elapsed > 0:
    production["Live Efficiency (%)"] = (
        production["Running Minutes"] / elapsed * 100
    ).round(1)
else:
    production["Live Efficiency (%)"] = 0.0

def loom_status(lid):
    if elapsed >= SHIFT_MINUTES:
        return "Shift Complete"
    stops = stoppages[stoppages["Loom ID"] == lid]
    for _, s in stops.iterrows():
        start = int(s["Minute of Shift"])
        end = start + int(s["Downtime (min)"])
        if start <= elapsed < end:
            return f"Stopped - {s['Stop Reason']}"
    return "Running"

production["Live Status"] = production["Loom ID"].apply(loom_status)

# =========================================================
# 6. LIVE STOPPAGE LOG AND SUMMARY
# =========================================================

live_stops = stoppages[stoppages["Minute of Shift"] < elapsed].copy()
live_stops["Lost Minutes"] = (elapsed - live_stops["Minute of Shift"]).clip(lower=0)
live_stops["Lost Minutes"] = np.minimum(live_stops["Lost Minutes"], live_stops["Downtime (min)"])

total_stops = len(live_stops)
total_downtime = float(sum(downtime_by_loom.values()))

stop_summary = (
    live_stops.groupby("Stop Reason")
    .agg(Stops=("Stop Reason","count"), Lost_Minutes=("Lost Minutes","sum"))
    .reset_index().sort_values("Lost_Minutes", ascending=False)
)

# =========================================================
# 7. BREAKAGE ANALYSIS
# =========================================================

break_types = ["Warp Break", "Weft Break", "Mechanical"]
if live_stops.empty:
    stop_counts = pd.DataFrame({
        "Loom ID": loom_ids,
        "Warp Break": [0]*len(loom_ids),
        "Weft Break": [0]*len(loom_ids),
        "Mechanical": [0]*len(loom_ids)
    })
else:
    stop_counts = pd.crosstab(live_stops["Loom ID"], live_stops["Stop Reason"])
    stop_counts = stop_counts.reindex(columns=break_types, fill_value=0).reset_index()

production = production.merge(stop_counts, on="Loom ID", how="left")
for t in break_types:
    production[t] = production[t].fillna(0).astype(int)
production["Total Stops"] = production[["Warp Break","Weft Break","Mechanical"]].sum(axis=1)
production["Warp Stops/100k Picks"] = (
    production["Warp Break"] / production["Live Actual Picks"].replace(0, np.nan) * 100000
).fillna(0).round(2)
RISK_THR = 2.0
production["Quality Risk"] = np.where(
    production["Warp Stops/100k Picks"] >= RISK_THR,
    "High - Inspect", "Normal - Inspect"
)

# =========================================================
# 8. YARN CONSUMPTION AND ISSUANCE
# =========================================================

WARP_KG_PER_M = 0.15
WEFT_KG_PER_M = 0.10

# Actual consumed so far:
production["Warp Used (kg)"] = (production["Fabric Produced (m)"] * WARP_KG_PER_M).round(2)
production["Weft Used (kg)"] = (production["Fabric Produced (m)"] * WEFT_KG_PER_M).round(2)
production["Total Yarn Used (kg)"] = (production["Warp Used (kg)"] + production["Weft Used (kg)"]).round(2)

# Determine fixed issuance per loom based on full shift, plus a 5% waste reserve
predicted_length = (production["Speed (PPM)"] * SHIFT_MINUTES) / production["Picks per Inch"] / 39.37
production["Warp Issued (kg)"] = np.ceil(predicted_length * WARP_KG_PER_M * 1.05 * 100) / 100
production["Weft Issued (kg)"] = np.ceil(predicted_length * WEFT_KG_PER_M * 1.05 * 100) / 100

# Simulate yarn waste from stoppages
production["Warp Waste (kg)"] = (production["Warp Break"] * 0.2).round(2)
production["Weft Waste (kg)"] = (production["Weft Break"] * 0.1).round(2)
production["Total Waste (kg)"] = production["Warp Waste (kg)"] + production["Weft Waste (kg)"]

# Calculate unused (WIP) on each loom
production["Warp Unused (kg)"] = (production["Warp Issued (kg)"] - production["Warp Used (kg)"] - production["Warp Waste (kg)"]).round(2)
production["Weft Unused (kg)"] = (production["Weft Issued (kg)"] - production["Weft Used (kg)"] - production["Weft Waste (kg)"]).round(2)

# Build material issues table (one row per material per loom)
issues = []
for _, row in production.iterrows():
    issues.append({
        "Loom ID": row["Loom ID"],
        "Beam ID": row["Beam ID"],
        "Material Type": "Warp",
        "Yarn Batch": row["Warp Yarn Batch"],
        "Issued (kg)": row["Warp Issued (kg)"],
        "Consumed (kg)": row["Warp Used (kg)"],
        "Wasted (kg)": row["Warp Waste (kg)"],
        "Unused (kg)": row["Warp Unused (kg)"]
    })
    issues.append({
        "Loom ID": row["Loom ID"],
        "Beam ID": row["Beam ID"],
        "Material Type": "Weft",
        "Yarn Batch": row["Weft Yarn Batch"],
        "Issued (kg)": row["Weft Issued (kg)"],
        "Consumed (kg)": row["Weft Used (kg)"],
        "Wasted (kg)": row["Weft Waste (kg)"],
        "Unused (kg)": row["Weft Unused (kg)"]
    })
issues_df = pd.DataFrame(issues)

# =========================================================
# 9. INVENTORY RECONCILIATION
# =========================================================

# Sum up by yarn batch
batch_issued = issues_df.groupby("Yarn Batch")["Issued (kg)"].sum().reset_index()
batch_unused = issues_df.groupby("Yarn Batch")["Unused (kg)"].sum().reset_index()
batch_waste  = issues_df.groupby("Yarn Batch")["Wasted (kg)"].sum().reset_index()

inventory = yarn_batches.merge(batch_issued, on="Yarn Batch", how="left")
inventory = inventory.rename(columns={"Issued (kg)": "Issued (kg)"})
inventory["Issued (kg)"] = inventory["Issued (kg)"].fillna(0).round(2)
inventory = inventory.merge(batch_unused, on="Yarn Batch", how="left")
inventory = inventory.rename(columns={"Unused (kg)": "WIP (kg)"})
inventory["WIP (kg)"] = inventory["WIP (kg)"].fillna(0).round(2)
inventory = inventory.merge(batch_waste, on="Yarn Batch", how="left")
inventory = inventory.rename(columns={"Wasted (kg)": "Wasted (kg)"})
inventory["Wasted (kg)"] = inventory["Wasted (kg)"].fillna(0).round(2)

inventory["Warehouse Remaining (kg)"] = (inventory["Opening Stock (kg)"] - inventory["Issued (kg)"]).round(2)
inventory["Status"] = np.where(
    inventory["Warehouse Remaining (kg)"] < 0, "SHORTAGE", "Available"
)

# Material balance: fixed issued = consumed + wasted + unused.
issues_df["Balance Difference (kg)"] = (
    issues_df["Issued (kg)"] - issues_df["Consumed (kg)"]
    - issues_df["Wasted (kg)"] - issues_df["Unused (kg)"]
).round(2)


# =========================================================
# 10. FABRIC ROLLS (Quality Tracking)
# =========================================================

fabric_rolls = production.copy()
fabric_rolls["Fabric Roll ID"] = [f"FR-{i:03d}" for i in range(1, len(fabric_rolls)+1)]
fabric_rolls["Inspection Status"] = np.where(
    fabric_rolls["Fabric Produced (m)"] > 0, "Pending Inspection", "Not Produced"
)
fabric_rolls["Inspection Priority"] = np.where(
    fabric_rolls["Quality Risk"] == "High - Inspect", "Priority", "Routine"
)
fabric_rolls["Inventory Category"] = "Produced / Awaiting Inspection"

# =========================================================
# 11. SUPPLIER TRACEABILITY
# =========================================================

supplier_map = yarn_batches.set_index("Yarn Batch")["Supplier"].to_dict()
traceability = fabric_rolls[[
    "Fabric Roll ID", "Loom ID", "Beam ID",
    "Warp Yarn Batch", "Weft Yarn Batch",
    "Fabric Produced (m)", "Inspection Priority"
]].copy()
traceability["Warp Supplier"] = traceability["Warp Yarn Batch"].map(supplier_map)
traceability["Weft Supplier"] = traceability["Weft Yarn Batch"].map(supplier_map)

flagged_rolls = traceability[
    (traceability["Inspection Priority"] == "Priority") &
    (traceability["Fabric Produced (m)"] > 0)
].copy()
flagged_rolls["Investigation Reason"] = "Elevated simulated warp-break rate"

flagged_batches = set(flagged_rolls["Warp Yarn Batch"]) | set(flagged_rolls["Weft Yarn Batch"])
potentially_affected = traceability[
    (
        traceability["Warp Yarn Batch"].isin(flagged_batches) |
        traceability["Weft Yarn Batch"].isin(flagged_batches)
    ) & ~traceability["Fabric Roll ID"].isin(flagged_rolls["Fabric Roll ID"])
].copy()

# =========================================================
# 12. LIVE PRODUCTION HISTORY (for trend charts)
# =========================================================

total_fabric = float(production["Fabric Produced (m)"].sum())
total_yarn_used = float(production["Total Yarn Used (kg)"].sum())
running_count = int((production["Live Status"] == "Running").sum())
stopped_count = int(production["Live Status"].str.startswith("Stopped").sum())

if not st.session_state.production_history or st.session_state.production_history[-1]["Minute"] != sim_min:
    st.session_state.production_history.append({
        "Minute": sim_min,
        "Fabric Produced (m)": round(total_fabric,2)
    })
if not st.session_state.loom_history or st.session_state.loom_history[-1]["Minute"] != sim_min:
    record = {"Minute": sim_min}
    for _, r in production.iterrows():
        record[r["Loom ID"]] = r["Fabric Produced (m)"]
    st.session_state.loom_history.append(record)
if not st.session_state.status_history or st.session_state.status_history[-1]["Minute"] != sim_min:
    st.session_state.status_history.append({
        "Minute": sim_min,
        "Running Looms": running_count,
        "Stopped Looms": stopped_count
    })

status_df = pd.DataFrame(st.session_state.status_history).set_index("Minute")
loom_hist_df = pd.DataFrame(st.session_state.loom_history).set_index("Minute")

# =========================================================
# 13. DASHBOARD LAYOUT (3 tabs: Production, Inventory, Lost Fabric)
# =========================================================

page1, page2, page3 = st.tabs([
    "Live Production & Operations",
    "Inventory, Quality & Traceability",
    "Lost Fabric Due to Downtime"
])

with page1:
    st.subheader("Live Production Overview")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Looms", len(production))
    k2.metric("Running", running_count)
    k3.metric("Stopped", stopped_count)
    k4.metric("Fabric Produced", f"{total_fabric:,.1f} m")
    avg_eff = float(production["Live Efficiency (%)"].mean())
    k5.metric("Avg Efficiency", f"{avg_eff:.1f}%")
    k6.metric("Total Downtime", f"{total_downtime:.0f} min")
    st.divider()

    # Live loom production table and bar chart
    left, right = st.columns([1.5, 1], gap="medium")
    with left:
        st.markdown("#### Loom Production (Live)")
        loom_table = production[[
            "Loom ID", "Beam ID", "Live Status",
            "Live Downtime (min)", "Fabric Produced (m)", "Live Efficiency (%)"
        ]].rename(columns={
            "Loom ID": "Loom", "Beam ID": "Beam",
            "Live Status": "Status", "Live Downtime (min)": "Downtime",
            "Fabric Produced (m)": "Fabric (m)", "Live Efficiency (%)": "Eff (%)"
        })
        st.dataframe(loom_table, use_container_width=True, hide_index=True, height=420)
    with right:
        st.markdown("#### Production by Loom")
        st.bar_chart(production.set_index("Loom ID")["Fabric Produced (m)"], height=420)

    # Trend charts
    tr1, tr2 = st.columns(2, gap="medium")
    with tr1:
        st.markdown("#### Looms Running vs Stopped (Trend)")
        st.line_chart(status_df, height=290, x_label="Minute", y_label="Looms")
    with tr2:
        st.markdown("#### Fabric by Loom (Trend)")
        st.line_chart(loom_hist_df, height=290, x_label="Minute", y_label="Fabric (m)")

    st.divider()

    # Warping data
    wleft, wright = st.columns([1.6,1], gap="medium")
    with wleft:
        st.markdown("#### Warping & Sizing Data")
        st.dataframe(warp_beams, use_container_width=True, hide_index=True, height=340)
    with wright:
        st.markdown("#### Warping Breaks by Beam")
        st.bar_chart(warp_beams.set_index("Beam ID")["Warping End Breaks"], height=340)

    st.divider()

    # Downtime analysis
    st.markdown("#### Downtime Analysis")
    d1, d2, d3 = st.columns([1,1,1], gap="medium")
    with d1:
        st.markdown("**Downtime by Loom**")
        st.bar_chart(production.set_index("Loom ID")["Live Downtime (min)"], height=260)
    with d2:
        st.markdown("**Warp vs Weft Breaks**")
        st.bar_chart(production.set_index("Loom ID")[["Warp Break","Weft Break"]], height=260)
    with d3:
        st.markdown("**Stop Time by Cause**")
        if not stop_summary.empty:
            st.bar_chart(stop_summary.set_index("Stop Reason")["Lost_Minutes"], height=260)
        else:
            st.info("No stoppages recorded yet.")
    el, er = st.columns([2,1], gap="medium")
    with el:
        st.markdown("#### Live Stoppage Events")
        log = live_stops[["Time","Loom ID","Beam ID","Stop Reason","Lost Minutes"]].sort_values("Time", ascending=False)
        st.dataframe(log, use_container_width=True, hide_index=True, height=260)
    with er:
        st.markdown("#### Operational Alert")
        st.metric("Stoppage Events", total_stops)
        if total_stops > 0:
            worst = production.loc[production["Live Downtime (min)"].idxmax()]
            st.warning(
                f"{worst['Loom ID']} longest downtime: {worst['Live Downtime (min)']:.0f} min (Beam {worst['Beam ID']})."
            )
        else:
            st.success("No downtime events yet.")

with page2:
    st.subheader("Inventory, Quality & Traceability")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Yarn Consumed", f"{total_yarn_used:.1f} kg")
    a2.metric("Fabric Produced", f"{total_fabric:,.1f} m")
    a3.metric("Priority Rolls", len(flagged_rolls))
    a4.metric("Other Rolls", len(potentially_affected))
    st.divider()

    # Yarn inventory and issuance
    inv_l, inv_r = st.columns([1.2,1], gap="medium")
    with inv_l:
        st.markdown("#### Yarn Batch Inventory")
        inv_view = inventory[[
            "Yarn Batch","Supplier","Yarn Type","Opening Stock (kg)",
            "Issued (kg)","Warehouse Remaining (kg)","WIP (kg)","Wasted (kg)","Status"
        ]]
        st.dataframe(inv_view, use_container_width=True, hide_index=True, height=280)
        if (inventory["Warehouse Remaining (kg)"] < 0).any():
            st.error("Yarn shortage detected in inventory!")
        else:
            st.success("Inventory levels are within available stock.")
    with inv_r:
        st.markdown("#### Material Issued to Production")
        st.dataframe(issues_df.drop(columns=["Balance Difference (kg)"]), use_container_width=True, hide_index=True, height=280)
        if (issues_df["Unused (kg)"] < -0.01).any():
            st.error("Material shortage on one or more looms: simulated use and waste exceed issued yarn.")
        elif (issues_df["Balance Difference (kg)"].abs() > 0.01).any():
            st.error("Material balance mismatch detected.")
        else:
            st.caption("Issued = Consumed + Wasted + Unused (per loom and yarn batch).")

    st.divider()

    # Fabric quality tracking
    ql, qr = st.columns([1.7,1], gap="medium")
    with ql:
        st.markdown("#### Fabric Roll Quality Tracking")
        roll_view = fabric_rolls[[
            "Fabric Roll ID","Loom ID","Beam ID","Fabric Produced (m)",
            "Warp Break","Weft Break","Warp Stops/100k Picks","Inspection Priority"
        ]]
        st.dataframe(roll_view, use_container_width=True, hide_index=True, height=320)
    with qr:
        st.markdown("#### Fabric Inventory Status")
        st.metric("Produced Fabric", f"{total_fabric:,.1f} m")
        st.metric("Approved Fabric", "0.0 m")
        st.metric("Awaiting Inspection", int((fabric_rolls["Fabric Produced (m)"] > 0).sum()))
        st.caption("Quality alerts are based on simulated warp breaks.")

    st.divider()

    # Supplier traceability tables
    st.markdown("#### Yarn Roll ➞ Batch ➞ Supplier Trace")
    st.dataframe(traceability, use_container_width=True, hide_index=True, height=310)
    tl, tr = st.columns([1,1], gap="medium")
    with tl:
        st.markdown("#### Priority Rolls (to Inspect)")
        if not flagged_rolls.empty:
            st.dataframe(flagged_rolls, use_container_width=True, hide_index=True, height=270)
        else:
            st.success("No priority rolls at this time.")
    with tr:
        st.markdown("#### Other Rolls with Flagged Yarn")
        if not potentially_affected.empty:
            st.dataframe(potentially_affected, use_container_width=True, hide_index=True, height=270)
        else:
            st.info("No additional rolls share flagged yarn.")

    st.divider()

    # Shared batch impact and recommendations
    imp_l, imp_r = st.columns([1,1], gap="medium")
    with imp_l:
        st.markdown("#### Shared Yarn Batch Impact")
        # Each roll can be linked to a batch as warp or weft.
        batch_links = pd.concat([
            traceability[["Fabric Roll ID", "Loom ID", "Warp Yarn Batch", "Fabric Produced (m)"]]
                .rename(columns={"Warp Yarn Batch": "Yarn Batch"}),
            traceability[["Fabric Roll ID", "Loom ID", "Weft Yarn Batch", "Fabric Produced (m)"]]
                .rename(columns={"Weft Yarn Batch": "Yarn Batch"})
        ], ignore_index=True)
        batch_links = batch_links[batch_links["Fabric Produced (m)"] > 0]
        batch_impact = (
            batch_links.groupby("Yarn Batch")
            .agg(Looms=("Loom ID", "nunique"), Rolls=("Fabric Roll ID", "nunique"))
            .reset_index()
        )
        batch_impact = yarn_batches[["Yarn Batch", "Supplier"]].merge(
            batch_impact, on="Yarn Batch", how="left"
        ).fillna({"Looms": 0, "Rolls": 0})
        batch_impact[["Looms", "Rolls"]] = batch_impact[["Looms", "Rolls"]].astype(int)
        st.dataframe(batch_impact, use_container_width=True, hide_index=True, height=240)
    with imp_r:
        st.markdown("#### Investigation Recommendations")
        top_breaks = production.sort_values("Warp Stops/100k Picks", ascending=False).head(3)
        for _, row in top_breaks.iterrows():
            if row["Warp Break"] > 0:
                st.write(f"**{row['Loom ID']}** (Beam {row['Beam ID']})")
                st.caption(f"Warp breaks: {row['Warp Break']}, Downtime: {row['Live Downtime (min)']:.0f} min, Batch: {row['Warp Yarn Batch']}")
        if top_breaks["Warp Break"].max() == 0:
            st.info("No high-break looms to investigate.")

    st.caption("All data is simulated for demonstration. Yarn issuance and usage are illustrative, not actual sensor readings.")


# =========================================================
# 14. ESTIMATED FABRIC PRODUCTION LOST TO DOWNTIME
# =========================================================
# A loom cannot lose the same minute twice. Assign each stopped minute
# to the first chronological stoppage that covers it for cause reporting.
loss_rows = []
for _, loom in production.iterrows():
    lid = loom["Loom ID"]
    meters_per_minute = float(loom["Speed (PPM)"]) / (float(loom["Picks per Inch"]) * 39.37)
    loom_stops = stoppages[stoppages["Loom ID"] == lid].sort_values(
        ["Minute of Shift", "Stop Reason"], kind="stable"
    )
    cause_for_minute = {}
    for _, stop in loom_stops.iterrows():
        start = int(stop["Minute of Shift"])
        end = min(elapsed, start + int(stop["Downtime (min)"]))
        for minute in range(start, end):
            cause_for_minute.setdefault(minute, stop["Stop Reason"])
    for cause in ["Warp Break", "Weft Break", "Mechanical"]:
        lost_minutes = sum(reason == cause for reason in cause_for_minute.values())
        loss_rows.append({
            "Loom ID": lid,
            "Stop Reason": cause,
            "Downtime (min)": lost_minutes,
            "Lost Fabric (m)": lost_minutes * meters_per_minute,
        })

loss_by_cause_loom = pd.DataFrame(loss_rows)
loss_by_loom = (
    loss_by_cause_loom.groupby("Loom ID", as_index=False)
    .agg({"Downtime (min)": "sum", "Lost Fabric (m)": "sum"})
)
loss_by_cause = (
    loss_by_cause_loom.groupby("Stop Reason", as_index=False)
    .agg({"Downtime (min)": "sum", "Lost Fabric (m)": "sum"})
)
total_lost_fabric = float(loss_by_loom["Lost Fabric (m)"].sum())

with page3:
    st.subheader("Lost Fabric Due to Downtime")
    st.caption("Estimated meters that could have been woven during recorded loom stoppages. This is lost production opportunity, not damaged fabric or yarn waste.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Estimated Lost Fabric", f"{total_lost_fabric:,.2f} m")
    c2.metric("Downtime (All Looms)", f"{total_downtime:,.0f} min")
    c3.metric("Actual Fabric Produced", f"{total_fabric:,.2f} m")

    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown("#### Lost Fabric by Loom")
        st.bar_chart(loss_by_loom.set_index("Loom ID")["Lost Fabric (m)"], height=310)
    with right:
        st.markdown("#### Lost Fabric by Stoppage Cause")
        st.bar_chart(loss_by_cause.set_index("Stop Reason")["Lost Fabric (m)"], height=310)

    st.markdown("#### Loom-Level Lost Production")
    loom_loss_table = loss_by_loom.merge(
        production[["Loom ID", "Speed (PPM)", "Picks per Inch"]],
        on="Loom ID", how="left"
    )
    loom_loss_table["Lost Fabric (m)"] = loom_loss_table["Lost Fabric (m)"].round(2)
    st.dataframe(loom_loss_table, use_container_width=True, hide_index=True)

    st.markdown("#### Stoppage Cause Breakdown")
    cause_table = loss_by_cause.copy()
    cause_table["Lost Fabric (m)"] = cause_table["Lost Fabric (m)"].round(2)
    st.dataframe(cause_table, use_container_width=True, hide_index=True)
    st.caption(
        "Method: lost meters = unique stopped minutes × loom picks/min ÷ "
        "(picks/inch × 39.37). Overlapping stoppages are counted only once; "
        "their minutes are assigned to the first recorded cause. "
        "All values are simulated estimates."
    )
