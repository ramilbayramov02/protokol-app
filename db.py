# db.py — Supabase əməliyyatları
import streamlit as st
from supabase import create_client
from data_loader import SUPABASE_URL, SUPABASE_KEY, load_excel, EVENT_ORDER
import pandas as pd
from datetime import datetime

@st.cache_resource
def get_db():
    try:
        from supabase import create_client, ClientOptions
        return create_client(SUPABASE_URL, SUPABASE_KEY, options=ClientOptions())
    except Exception:
        return create_client(SUPABASE_URL, SUPABASE_KEY)

def init_db():
    """Excel-dəki movement_log-u Supabase-ə yüklə (ilk dəfə)"""
    db = get_db()
    # Artıq data varsa yükləmə
    res = db.table("movement_log").select("id").limit(1).execute()
    if res.data:
        return
    _, _, _, _, log_base = load_excel()
    records = []
    for _, row in log_base.iterrows():
        records.append({
            "delegation_id": int(row.get("delegation_id", 0)) if pd.notna(row.get("delegation_id")) else 0,
            "convoy_order":  int(row.get("convoy_order", 0))  if pd.notna(row.get("convoy_order"))  else 0,
            "pcc":           str(row.get("pcc", "")),
            "country_name":  str(row.get("country_name", "")),
            "leader_name":   str(row.get("leader_name", "")),
            "event_name":    str(row.get("event_name", "")),
            "planned_time":  str(row.get("planned_time", "")),
            "actual_time":   "",
            "status":        "Pending",
            "delay_reason":  "",
            "notes":         "",
            "is_handshake":  str(row.get("is_handshake","")) in ["YES","True","true","1"],
            "recorded_by":   "",
        })
    # Batch insert
    for i in range(0, len(records), 50):
        db.table("movement_log").insert(records[i:i+50]).execute()

def get_log() -> pd.DataFrame:
    db = get_db()
    res = db.table("movement_log")\
        .select("*")\
        .order("convoy_order")\
        .execute()
    if not res.data:
        return pd.DataFrame()
    df = pd.DataFrame(res.data)
    for col in ["actual_time","delay_reason","notes"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)
    return df

def update_event(log_id: int, actual_time: str, status: str,
                 delay_reason: str, notes: str, recorded_by: str):
    db = get_db()
    db.table("movement_log").update({
        "actual_time":  actual_time,
        "status":       status,
        "delay_reason": delay_reason,
        "notes":        notes,
        "recorded_by":  recorded_by,
        "recorded_at":  datetime.utcnow().isoformat(),
    }).eq("id", log_id).execute()

def reset_event(log_id: int):
    db = get_db()
    db.table("movement_log").update({
        "actual_time":  "",
        "status":       "Pending",
        "delay_reason": "",
        "notes":        "",
        "recorded_by":  "",
    }).eq("id", log_id).execute()

def upsert_gps(vehicle_id: str, country: str, driver_name: str,
               lat: float, lon: float, speed: float = 0):
    db = get_db()
    db.table("gps_tracking").upsert({
        "vehicle_id":  vehicle_id,
        "country":     country,
        "driver_name": driver_name,
        "lat":         lat,
        "lon":         lon,
        "speed_kmh":   speed,
        "updated_at":  datetime.utcnow().isoformat(),
    }, on_conflict="vehicle_id").execute()

def get_gps() -> pd.DataFrame:
    db = get_db()
    res = db.table("gps_tracking").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()
