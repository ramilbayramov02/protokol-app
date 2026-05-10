# db.py — Session_state + Supabase (yalnız GPS üçün)
import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

SUPABASE_URL = "https://vsbxbqklsvtmvuxoenut.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZzYnhicWtsc3Z0bXZ1eG9lbnV0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgwOTExMTEsImV4cCI6MjA5MzY2NzExMX0.XTuQD6W4AhJ5s6tlhYrZmNirMNskS_lNBkzrG4prt04"

@st.cache_resource
def get_db():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Movement log — session_state ────────────────────────────────────────────
def init_db():
    if "log_data" not in st.session_state:
        from data_loader import load_excel
        _, _, _, _, log_base = load_excel()
        st.session_state["log_data"] = log_base.copy()

def get_log() -> pd.DataFrame:
    if "log_data" not in st.session_state:
        init_db()
    return st.session_state["log_data"].copy()

def update_event(log_id, actual_time, status, delay_reason, notes, recorded_by):
    df = st.session_state["log_data"]
    mask = df["id"] == log_id if "id" in df.columns else df.index == log_id
    for i in df[mask].index:
        df.at[i, "actual_time"]  = actual_time
        df.at[i, "status"]       = status
        df.at[i, "delay_reason"] = delay_reason
        df.at[i, "notes"]        = notes
        df.at[i, "recorded_by"]  = recorded_by
    st.session_state["log_data"] = df

def reset_event(log_id):
    df = st.session_state["log_data"]
    mask = df["id"] == log_id if "id" in df.columns else df.index == log_id
    for i in df[mask].index:
        df.at[i, "actual_time"]  = ""
        df.at[i, "status"]       = "Pending"
        df.at[i, "delay_reason"] = ""
        df.at[i, "notes"]        = ""
        df.at[i, "recorded_by"]  = ""
    st.session_state["log_data"] = df

# ── GPS — Supabase ───────────────────────────────────────────────────────────
def upsert_gps(vehicle_id, country, driver_name, lat, lon, speed=0):
    try:
        db  = get_db()
        now = datetime.utcnow().isoformat()
        existing = db.table("gps_tracking").select("id").eq("vehicle_id", vehicle_id).execute()
        if existing.data:
            db.table("gps_tracking").update({
                "country": country, "driver_name": driver_name,
                "lat": lat, "lon": lon, "speed_kmh": speed, "updated_at": now,
            }).eq("vehicle_id", vehicle_id).execute()
        else:
            db.table("gps_tracking").insert({
                "vehicle_id": vehicle_id, "country": country,
                "driver_name": driver_name, "lat": lat, "lon": lon,
                "speed_kmh": speed, "updated_at": now,
            }).execute()
    except Exception as e:
        st.warning(f"GPS xətası: {e}")

def get_gps() -> pd.DataFrame:
    try:
        db  = get_db()
        res = db.table("gps_tracking").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()
