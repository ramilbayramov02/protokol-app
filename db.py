# db.py — Supabase-siz, yalnız session_state
import streamlit as st
import pandas as pd
from datetime import datetime

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

def upsert_gps(vehicle_id, country, driver_name, lat, lon, speed=0):
    if "gps_data" not in st.session_state:
        st.session_state["gps_data"] = []
    gps = st.session_state["gps_data"]
    for g in gps:
        if g["vehicle_id"] == vehicle_id:
            g.update({"country": country, "driver_name": driver_name,
                      "lat": lat, "lon": lon, "speed_kmh": speed,
                      "updated_at": datetime.now().strftime("%H:%M:%S")})
            st.session_state["gps_data"] = gps
            return
    gps.append({"vehicle_id": vehicle_id, "country": country,
                "driver_name": driver_name, "lat": lat, "lon": lon,
                "speed_kmh": speed,
                "updated_at": datetime.now().strftime("%H:%M:%S")})
    st.session_state["gps_data"] = gps

def get_gps() -> pd.DataFrame:
    data = st.session_state.get("gps_data", [])
    return pd.DataFrame(data) if data else pd.DataFrame()
