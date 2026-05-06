# data_loader.py
import pandas as pd
import streamlit as st

@st.cache_data
def load_excel():
    f = "logistics_v2.xlsx"
    delegations = pd.read_excel(f, sheet_name="4_delegations",     skiprows=1)
    vehicles    = pd.read_excel(f, sheet_name="2_vehicles",         skiprows=1)
    staff       = pd.read_excel(f, sheet_name="3_vehicle_staff",    skiprows=1)
    pcc         = pd.read_excel(f, sheet_name="5_pcc_assignments",  skiprows=1)
    log_base    = pd.read_excel(f, sheet_name="6_movement_log",     skiprows=1)

    delegations.columns = [c.lower().strip() for c in delegations.columns]
    vehicles.columns    = [c.lower().strip() for c in vehicles.columns]
    staff.columns       = [c.lower().strip() for c in staff.columns]
    pcc.columns         = [c.lower().strip() for c in pcc.columns]
    log_base.columns    = [c.lower().strip() for c in log_base.columns]

    # delegations-a pcc sütununu əlavə et
    pcc_map = pcc[["delegation_id","pcc_code"]].rename(columns={"pcc_code":"pcc"})
    delegations = delegations.merge(pcc_map, on="delegation_id", how="left")
    delegations["pcc"] = delegations["pcc"].fillna("—")

    for col in ["actual_time","delay_reason","notes"]:
        if col not in log_base.columns:
            log_base[col] = ""
        log_base[col] = log_base[col].fillna("").astype(str)

    log_base["planned_time"] = log_base["planned_time"].fillna("").astype(str)
    log_base["status"]       = log_base["status"].fillna("Pending").astype(str)
    log_base["is_handshake"] = log_base["is_handshake"].fillna("").astype(str)

    return delegations, vehicles, staff, pcc, log_base

# Hotel coordinates (Baku)
HOTEL_COORDS = {
    "Four Seasons":  {"lat": 40.3532, "lon": 49.8337, "color": "#16a34a"},
    "Fairmont":      {"lat": 40.3495, "lon": 49.8325, "color": "#d97706"},
    "JW Marriott":   {"lat": 40.3760, "lon": 49.8352, "color": "#7c3aed"},
    "Ritz Carlton":  {"lat": 40.3667, "lon": 49.8372, "color": "#db2777"},
    "GYD Airport":   {"lat": 40.4670, "lon": 50.0467, "color": "#2563eb"},
}

BOS = {"name": "BOS", "lat": 40.3983, "lon": 49.8672}

EVENT_ORDER = [
    "Depot Departure",
    "1st Destination Arrival",
    "Hotel Departure",
    "BOS Arrival",
    "Handshake",
    "BOS Departure",
]

SUPABASE_URL = "https://vsbxbqklsvtmvuxoenut.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZzYnhicWtsc3Z0bXZ1eG9lbnV0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgwOTExMTEsImV4cCI6MjA5MzY2NzExMX0.XTuQD6W4AhJ5s6tlhYrZmNirMNskS_lNBkzrG4prt04"
