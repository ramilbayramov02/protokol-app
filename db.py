# db.py — Supabase əməliyyatları (tam yenilənmiş)
import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

SUPABASE_URL = "https://vsbxbqklsvtmvuxoenut.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZzYnhicWtsc3Z0bXZ1eG9lbnV0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgwOTExMTEsImV4cCI6MjA5MzY2NzExMX0.XTuQD6W4AhJ5s6tlhYrZmNirMNskS_lNBkzrG4prt04"


@st.cache_resource
def get_db():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def init_db():
    """Excel-dəki movement_log-u Supabase-ə yüklə (yalnız ilk dəfə)"""
    try:
        db = get_db()
        res = db.table("movement_log").select("id").limit(1).execute()
        if res.data:
            return  # artıq data var
        from data_loader import load_excel
        _, _, _, _, log_base = load_excel()
        records = []
        for _, row in log_base.iterrows():
            records.append({
                "delegation_id": int(row["delegation_id"]) if pd.notna(row.get("delegation_id")) else 0,
                "convoy_order":  int(row["convoy_order"])  if pd.notna(row.get("convoy_order"))  else 0,
                "pcc":           str(row.get("pcc", "")),
                "country_name":  str(row.get("country_name", "")),
                "leader_name":   str(row.get("leader_name", "")),
                "event_name":    str(row.get("event_name", "")),
                "planned_time":  str(row.get("planned_time", "")),
                "actual_time":   "",
                "status":        "Pending",
                "delay_reason":  "",
                "notes":         "",
                "is_handshake":  str(row.get("is_handshake", "")) in ["YES", "True", "true", "1"],
                "recorded_by":   "",
            })
        for i in range(0, len(records), 50):
            db.table("movement_log").insert(records[i:i+50]).execute()
    except Exception as e:
        st.warning(f"DB init xətası: {e}")


def get_log() -> pd.DataFrame:
    try:
        db = get_db()
        res = db.table("movement_log").select("*").order("convoy_order").execute()
        if not res.data:
            return pd.DataFrame()
        df = pd.DataFrame(res.data)
        for col in ["actual_time", "delay_reason", "notes"]:
            if col not in df.columns:
                df[col] = ""
            df[col] = df[col].fillna("").astype(str)
        return df
    except Exception as e:
        st.error(f"Log oxuma xətası: {e}")
        return pd.DataFrame()


def update_event(log_id: int, actual_time: str, status: str,
                 delay_reason: str, notes: str, recorded_by: str):
    try:
        db = get_db()
        db.table("movement_log").update({
            "actual_time":  actual_time,
            "status":       status,
            "delay_reason": delay_reason,
            "notes":        notes,
            "recorded_by":  recorded_by,
            "recorded_at":  datetime.utcnow().isoformat(),
        }).eq("id", log_id).execute()
    except Exception as e:
        st.error(f"Yeniləmə xətası: {e}")


def reset_event(log_id: int):
    try:
        db = get_db()
        db.table("movement_log").update({
            "actual_time":  "",
            "status":       "Pending",
            "delay_reason": "",
            "notes":        "",
            "recorded_by":  "",
        }).eq("id", log_id).execute()
    except Exception as e:
        st.error(f"Sıfırlama xətası: {e}")


def upsert_gps(vehicle_id: str, country: str, driver_name: str,
               lat: float, lon: float, speed: float = 0):
    try:
        db  = get_db()
        now = datetime.utcnow().isoformat()
        existing = db.table("gps_tracking").select("id").eq("vehicle_id", vehicle_id).execute()
        if existing.data:
            db.table("gps_tracking").update({
                "country":     country,
                "driver_name": driver_name,
                "lat":         lat,
                "lon":         lon,
                "speed_kmh":   speed,
                "updated_at":  now,
            }).eq("vehicle_id", vehicle_id).execute()
        else:
            db.table("gps_tracking").insert({
                "vehicle_id":  vehicle_id,
                "country":     country,
                "driver_name": driver_name,
                "lat":         lat,
                "lon":         lon,
                "speed_kmh":   speed,
                "updated_at":  now,
            }).execute()
    except Exception as e:
        st.error(f"GPS xətası: {e}")


def get_gps() -> pd.DataFrame:
    try:
        db  = get_db()
        res = db.table("gps_tracking").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()
