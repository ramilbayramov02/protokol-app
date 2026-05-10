# ═══════════════════════════════════════════════════════════════════════════
#  app.py  —  Azərbaycan Respublikası Prezidentinin Protokol Xidməti
#  VIP Kortej Koordinasiya Sistemi  |  Streamlit + Supabase
# ═══════════════════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import re

from data_loader import load_excel, HOTEL_COORDS, BOS, EVENT_ORDER
from calculations import (hotel_distances, scenario_simultaneous,
                           scenario_staggered, time_diff_min, infer_status,
                           calc_distance_km)
from db import init_db, get_log, update_event, reset_event, upsert_gps, get_gps
from report import generate_word_report

# ── Logo ─────────────────────────────────────────────────────────────────────
import base64, os

def get_logo_b64():
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "logo.jpeg")
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

LOGO_B64 = get_logo_b64()
LOGO_HTML = f"<img src='data:image/jpeg;base64,{LOGO_B64}' style='height:90px;border-radius:50%;border:2px solid #D4AF37;box-shadow:0 0 20px rgba(212,175,55,0.4);'>" if LOGO_B64 else "🏛"

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Protokol Xidməti — Kortej Sistemi",
    page_icon="🏛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── LOGIN SİSTEMİ ─────────────────────────────────────────────────────────────
USERS = {
    "admin":  {"password": "protokol2024",  "role": "Bütün (Admin)"},
    "pcc1":   {"password": "pcc1_2024",     "role": "PCC1"},
    "pcc2":   {"password": "pcc2_2024",     "role": "PCC2"},
    "pcc3":   {"password": "pcc3_2024",     "role": "PCC3"},
}

def check_login(username, password):
    u = USERS.get(username.lower().strip())
    if u and u["password"] == password:
        return u["role"]
    return None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.markdown(f"""
    <div style="max-width:420px;margin:60px auto 0;padding:40px;
      background:#0f2040;border:1px solid #D4AF37;border-radius:14px;
      box-shadow:0 8px 32px rgba(0,0,0,0.5);">
      <div style="text-align:center;margin-bottom:30px;">
        <div style="margin-bottom:16px;">{LOGO_HTML}</div>
        <div style="font-size:11px;color:#8a9bb0;letter-spacing:1px;">
          Azərbaycan Respublikası Prezidentinin</div>
        <div style="font-size:18px;font-weight:900;color:#D4AF37;
          letter-spacing:2px;margin-top:4px;">PROTOKOL XİDMƏTİ</div>
        <div style="font-size:11px;color:#6a8aaa;margin-top:4px;
          letter-spacing:2px;">VIP KORTEJ KOORDİNASİYA SİSTEMİ</div>
        <div style="width:60px;height:2px;background:#D4AF37;
          margin:16px auto 0;"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        st.markdown("<div style='max-width:420px;margin:0 auto;'>", unsafe_allow_html=True)
        username = st.text_input("👤 İstifadəçi adı:", placeholder="pcc1 / pcc2 / pcc3 / admin")
        password = st.text_input("🔒 Parol:", type="password", placeholder="Parolu daxil edin")
        submitted = st.form_submit_button("🔑 Daxil ol", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            role = check_login(username, password)
            if role:
                st.session_state.logged_in = True
                st.session_state.user_role = role
                st.session_state.username  = username.lower().strip()
                st.rerun()
            else:
                st.error("❌ İstifadəçi adı və ya parol yanlışdır!")
    st.stop()

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"]{background:#0d1e35;}
[data-testid="stSidebar"]{background:#071120;border-right:1px solid #D4AF37;}
[data-testid="stSidebar"] *{color:#c0d0e0 !important;}
.stSelectbox label, .stTextInput label, .stNumberInput label,
.stSlider label, .stRadio label, .stCheckbox label{color:#8a9bb0 !important;font-size:11px !important;}
.stButton>button{background:#1B2A4A;color:#D4AF37;border:1px solid #D4AF37;
  border-radius:6px;font-weight:700;transition:all .2s;}
.stButton>button:hover{background:#D4AF37;color:#071120;}
.stDownloadButton>button{background:linear-gradient(135deg,#2563EB,#1d4ed8);
  color:white;border:none;border-radius:6px;font-weight:700;width:100%;padding:10px;}
h1,h2,h3{color:#D4AF37 !important;}
.stDataFrame{background:#0f2040;}
div[data-testid="metric-container"]{background:#0f2040;border:1px solid #1e3a5f;
  border-radius:8px;padding:12px;}
div[data-testid="metric-container"] label{color:#8a9bb0 !important;}
div[data-testid="metric-container"] div{color:#D4AF37 !important;}
.st-emotion-cache-1gulkj5{background:#152238;}
.stTabs [data-baseweb="tab"]{color:#8a9bb0;font-weight:600;}
.stTabs [aria-selected="true"]{color:#D4AF37 !important;border-bottom:2px solid #D4AF37;}
.alert-ok{background:#0a2010;border:1px solid #16a34a;border-radius:8px;
  padding:10px 16px;color:#5fb87a;font-weight:700;margin-bottom:8px;}
.alert-delay{background:#2a0a0a;border:1px solid #dc2626;border-left:4px solid #dc2626;
  border-radius:8px;padding:10px 16px;color:#f87171;font-weight:700;margin-bottom:8px;}
.alert-warn{background:#2a1500;border:1px solid #D4AF37;border-left:4px solid #D4AF37;
  border-radius:8px;padding:10px 16px;color:#fcd34d;font-weight:700;margin-bottom:8px;
  animation:pulse 2s infinite;}
.badge-ok{background:#0a2010;color:#5fb87a;padding:2px 10px;border-radius:10px;
  font-size:11px;font-weight:700;border:1px solid #16a34a;}
.badge-delay{background:#2a0a0a;color:#f87171;padding:2px 10px;border-radius:10px;
  font-size:11px;font-weight:700;border:1px solid #dc2626;}
.badge-pend{background:#1a1400;color:#c8a820;padding:2px 10px;border-radius:10px;
  font-size:11px;font-weight:700;border:1px solid #5f4a00;}
.badge-hs{background:#1a0a30;color:#c87af5;padding:2px 10px;border-radius:10px;
  font-size:11px;font-weight:700;border:1px solid #7c3aed;}
.pcc1{background:#0a1f3a;color:#7ab8f5;padding:2px 9px;border-radius:8px;
  font-size:11px;font-weight:700;border:1px solid #1e4a80;}
.pcc2{background:#150825;color:#b87af5;padding:2px 9px;border-radius:8px;
  font-size:11px;font-weight:700;border:1px solid #4a1a6f;}
.pcc3{background:#0a2010;color:#5fb87a;padding:2px 9px;border-radius:8px;
  font-size:11px;font-weight:700;border:1px solid #1a5f3a;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.6}}
</style>
""", unsafe_allow_html=True)

# ── Init ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3)
def cached_log():
    return get_log()

def get_fresh_log():
    cached_log.clear()
    return get_log()

# Load static data
delegations, vehicles, staff, pcc_df, log_base = load_excel()
init_db()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style='text-align:center;padding:15px 0 10px;border-bottom:1px solid #D4AF37;margin-bottom:15px;'>
      <div style='margin-bottom:10px;'><img src='data:image/jpeg;base64,{LOGO_B64}' style='height:70px;border-radius:50%;border:2px solid #D4AF37;box-shadow:0 0 12px rgba(212,175,55,0.4);'></div>
      <div style='font-size:10px;color:#8a9bb0;'>Azərbaycan Respublikası Prezidentinin</div>
      <div style='font-size:13px;font-weight:900;color:#D4AF37;letter-spacing:1px;'>PROTOKOL XİDMƏTİ</div>
      <div style='font-size:10px;color:#6a8aaa;margin-top:3px;'>VIP Kortej Koordinasiya Sistemi</div>
    </div>
    """, unsafe_allow_html=True)

    # PCC rolu login-dən gəlir
    pcc_role = st.session_state.user_role
    st.markdown(f"**👤 Rol:** `{pcc_role}`")
    st.markdown("---")

    # Canlı saat
    clock_ph = st.empty()
    clock_ph.markdown(f"<div style='text-align:center;font-size:22px;font-weight:700;color:#D4AF37;font-family:monospace;'>{datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

    # Panel seçimi
    st.markdown("**📋 Panellər**")
    page = st.radio("", [
        "🏠 Ana Panel",
        "✍️ Vaxt Qeydiyyatı",
        "🌍 Ölkə & Kortej",
        "🏨 Otel & Məsafə",
        "🗺️ Canlı Xəritə",
        "📡 GPS İzləmə",
        "📱 Sürücü GPS",
        "🧮 Ssenari Modu",
        "📄 Hesabat",
    ], label_visibility="collapsed")

    st.markdown("---")
    st.markdown(f"**👤 {st.session_state.username.upper()}** giriş edib")
    if st.button("🔄 Yenilə", key="sidebar_refresh"):
        get_fresh_log()
        st.rerun()
    if st.button("🚪 Çıxış", key="logout"):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.username  = ""
        st.rerun()

# ── Load live log ─────────────────────────────────────────────────────────────
log = cached_log()
if log.empty:
    st.warning("Məlumat yüklənir...")
    time.sleep(1)
    st.rerun()

# Filter by PCC if not admin
def pcc_filter(df):
    if pcc_role == "Bütün (Admin)":
        return df
    return df[df["pcc"] == pcc_role]

# ── Helper functions ──────────────────────────────────────────────────────────
def status_badge(s):
    if s == "OK":    return '<span class="badge-ok">✓ OK</span>'
    if s == "Delay": return '<span class="badge-delay">⚡ Gecikdi</span>'
    if s == "Handshake": return '<span class="badge-hs">🤝 HS</span>'
    return '<span class="badge-pend">⏳ Gözləyir</span>'

def pcc_badge(p):
    cls = {"PCC1":"pcc1","PCC2":"pcc2","PCC3":"pcc3"}.get(p,"pcc1")
    return f'<span class="{cls}">{p}</span>'

def next_pending(ev):
    df = log[(log["event_name"]==ev)&(log["status"]=="Pending")]
    if pcc_role != "Bütün (Admin)":
        df = df[df["pcc"]==pcc_role]
    df = df.sort_values("convoy_order")
    return df.iloc[0] if len(df) > 0 else None

# ══════════════════════════════════════════════════════════════════════════════
# 1. ANA PANEL
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Ana Panel":
    col_logo, col_title = st.columns([1, 8])
    with col_logo:
        if LOGO_B64:
            st.markdown(f"<img src='data:image/jpeg;base64,{LOGO_B64}' style='height:64px;border-radius:50%;border:2px solid #D4AF37;box-shadow:0 0 12px rgba(212,175,55,0.4);margin-top:4px;'>", unsafe_allow_html=True)
    with col_title:
        st.markdown("## Canlı Əməliyyat Paneli")

    log_f = pcc_filter(log)
    tot   = len(log_f)
    nok   = (log_f["status"]=="OK").sum()
    ndl   = (log_f["status"]=="Delay").sum()
    npd   = (log_f["status"]=="Pending").sum()

    # KPI
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("🌍 Delegasiya", log_f["country_name"].nunique())
    c2.metric("✅ Vaxtında", f"{nok}", f"{round(nok/tot*100,1)}%" if tot>0 else "")
    c3.metric("⚡ Gecikmiş", f"{ndl}", delta_color="inverse")
    c4.metric("⏳ Gözləyir", f"{npd}")
    c5.metric("🤝 Handshake OK", (log_f[log_f["event_name"]=="Handshake"]["status"]=="OK").sum())

    st.markdown("---")

    # Alert panel
    delays = log_f[log_f["status"]=="Delay"]
    if not delays.empty:
        st.markdown("### 🚨 Aktiv Gecikdirmələr")
        for _, r in delays.iterrows():
            dm = time_diff_min(r["planned_time"], r["actual_time"])
            dm_str = f"+{dm} dəq" if dm else ""
            rsn = r.get("delay_reason","")
            st.markdown(f"""<div class="alert-delay">
            ⚡ <b>{r['country_name']}</b> — {r['event_name']} | Plan: {r['planned_time']} | Faktiki: {r['actual_time']} {dm_str}
            {f'| Səbəb: {rsn}' if rsn else ''}
            </div>""", unsafe_allow_html=True)

    # Delegation status table
    st.markdown("### 📊 Delegasiya Status Cədvəli")
    summ = log_f.groupby(["convoy_order","pcc","country_name","leader_name"]).agg(
        ok=("status", lambda x: (x=="OK").sum()),
        delay=("status", lambda x: (x=="Delay").sum()),
        pending=("status", lambda x: (x=="Pending").sum()),
    ).reset_index().sort_values("convoy_order")

    hs_log = log_f[log_f["event_name"]=="Handshake"][["country_name","planned_time","actual_time","status"]]\
        .rename(columns={"planned_time":"hs_plan","actual_time":"hs_act","status":"hs_st"})
    summ = summ.merge(hs_log, on="country_name", how="left")

    rows = []
    for _, r in summ.iterrows():
        hs_st = r.get("hs_st","Pending")
        rows.append({
            "#":       r["convoy_order"],
            "PCC":     r["pcc"],
            "Ölkə":    r["country_name"],
            "Başçı":   r["leader_name"],
            "OK":      r["ok"],
            "Gecik":   r["delay"],
            "Gözl":    r["pending"],
            "HS Plan": r.get("hs_plan","—"),
            "HS Fakt": r.get("hs_act","—") or "—",
            "HS St":   hs_st,
        })

    df_show = pd.DataFrame(rows)

    def color_status(val):
        if val == "Delay" or (isinstance(val,int) and val > 0 and df_show.columns.tolist().index("Gecik") == df_show.columns.tolist().index("Gecik")):
            return "background-color:#2a0a0a;color:#f87171"
        if val == "OK": return "background-color:#0a2010;color:#5fb87a"
        return ""

    st.dataframe(
        df_show.style.map(
            lambda v: "background-color:#2a0a0a;color:#f87171;font-weight:700" if v=="Delay" else "",
            subset=["HS St"]
        ).map(
            lambda v: "background-color:#2a0a0a;color:#f87171;font-weight:700" if isinstance(v,int) and v>0 else "",
            subset=["Gecik"]
        ),
        use_container_width=True, hide_index=True
    )

    # Pie chart
    st.markdown("### 📈 Status Paylanması")
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(go.Pie(
            labels=["Vaxtında","Gecikmiş","Gözləyir"],
            values=[nok, ndl, npd],
            marker_colors=["#16a34a","#dc2626","#b89010"],
            hole=0.4,
            textinfo="label+percent",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#c0d0e0",
            showlegend=False,
            margin=dict(t=20,b=20,l=20,r=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        pcc_stats = log_f.groupby("pcc").agg(
            ok=("status", lambda x:(x=="OK").sum()),
            delay=("status", lambda x:(x=="Delay").sum()),
        ).reset_index()
        fig2 = px.bar(pcc_stats, x="pcc", y=["ok","delay"],
            color_discrete_map={"ok":"#16a34a","delay":"#dc2626"},
            barmode="group", title="PCC üzrə OK vs Gecik")
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", font_color="#c0d0e0",
            title_font_color="#D4AF37", margin=dict(t=40,b=20))
        st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 2. VAXT QEYDİYYATI
# ══════════════════════════════════════════════════════════════════════════════
elif page == "✍️ Vaxt Qeydiyyatı":
    st.markdown("## ✍️ Vaxt Qeydiyyatı")

    col1, col2 = st.columns([3,1])
    with col1:
        ev_sel = st.selectbox("Mərhələ seçin:", EVENT_ORDER)
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Yenilə", key="refresh_vaxt"):
            get_fresh_log()
            st.rerun()

    # Alert — növbəti ölkə
    nx = next_pending(ev_sel)
    if nx is not None:
        pm = nx["planned_time"]
        now_min = datetime.now().hour*60 + datetime.now().minute
        try:
            pp = pm.split(":"); p_min = int(pp[0])*60+int(pp[1])
            mins_to = p_min - now_min
            st.markdown(f"""<div class="alert-warn">
            ⚡ NÖVBƏ: <b>{nx['country_name']}</b> — {ev_sel} | Plan: {pm}
            {f'| ≈ {mins_to} dəqiqə sonra' if mins_to > 0 else '| İNDİ!'}
            </div>""", unsafe_allow_html=True)
        except:
            st.markdown(f"""<div class="alert-warn">⚡ NÖVBƏ: <b>{nx['country_name']}</b> — Plan: {pm}</div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-ok">✅ Bu mərhələ üzrə bütün qeydiyyatlar tamamlanıb.</div>', unsafe_allow_html=True)

    # Table header
    st.markdown("""
    <div style='display:grid;grid-template-columns:30px 150px 120px 80px 80px 120px 200px;
      gap:8px;padding:8px 10px;background:#071120;border-radius:6px;margin-bottom:6px;
      border-bottom:2px solid #D4AF37;'>
      <span style='font-size:10px;color:#D4AF37;font-weight:700;'>#</span>
      <span style='font-size:10px;color:#D4AF37;font-weight:700;'>Ölkə</span>
      <span style='font-size:10px;color:#D4AF37;font-weight:700;'>Başçı</span>
      <span style='font-size:10px;color:#D4AF37;font-weight:700;'>Plan</span>
      <span style='font-size:10px;color:#D4AF37;font-weight:700;'>Faktiki</span>
      <span style='font-size:10px;color:#D4AF37;font-weight:700;'>Status</span>
      <span style='font-size:10px;color:#D4AF37;font-weight:700;'>Səbəb / Əməliyyat</span>
    </div>
    """, unsafe_allow_html=True)

    log_f  = pcc_filter(log)
    ev_log = log_f[log_f["event_name"]==ev_sel].sort_values("convoy_order")

    for _, r in ev_log.iterrows():
        lid    = r["id"]
        cn     = r["country_name"]
        is_nx  = nx is not None and cn == nx["country_name"]
        st_val = r["status"]
        act    = r.get("actual_time","")
        rsn    = r.get("delay_reason","")

        bg = "#1a1800" if is_nx and st_val=="Pending" else \
             "#0a1a0a" if st_val=="OK" else \
             "#1a0808" if st_val=="Delay" else "#0f2040"

        with st.container():
            cols = st.columns([0.5, 2, 2, 1, 1, 1.5, 3])
            cols[0].markdown(f"<span style='color:#D4AF37;font-weight:700;'>{r['convoy_order']}</span>", unsafe_allow_html=True)
            cols[1].markdown(f"<span style='color:#c0d0e0;font-weight:600;'>{cn}</span>" +
                             (" 🤝" if ev_sel=="Handshake" else ""), unsafe_allow_html=True)
            cols[2].markdown(f"<span style='color:#8a9bb0;font-size:11px;'>{r['leader_name'][:20]}</span>", unsafe_allow_html=True)
            cols[3].markdown(f"<span style='color:#5fb87a;font-family:monospace;font-weight:700;'>{r['planned_time']}</span>", unsafe_allow_html=True)
            cols[4].markdown(f"<span style='color:{'#f87171' if st_val=='Delay' else '#5fb87a'};font-family:monospace;font-weight:700;'>{act or '—'}</span>", unsafe_allow_html=True)

            # Status
            if st_val == "OK":
                cols[5].markdown('<span class="badge-ok">✓ OK</span>', unsafe_allow_html=True)
            elif st_val == "Delay":
                dm = time_diff_min(r["planned_time"], act)
                cols[5].markdown(f'<span class="badge-delay">⚡ +{dm}dəq</span>', unsafe_allow_html=True)
            elif is_nx:
                cols[5].markdown('<span style="color:#f5d020;font-weight:700;animation:pulse 1.5s infinite;">🟡 Növbəti</span>', unsafe_allow_html=True)
            else:
                cols[5].markdown('<span class="badge-pend">⏳ Gözləyir</span>', unsafe_allow_html=True)

            # Actions
            with cols[6]:
                if st_val in ["OK","Delay"]:
                    c1, c2 = st.columns(2)
                    c1.markdown(f"<span style='color:#6a8aaa;font-size:10px;'>{rsn or '—'}</span>", unsafe_allow_html=True)
                    if c2.button("↩", key=f"undo_{lid}", help="Geri al"):
                        reset_event(lid)
                        get_fresh_log()
                        st.rerun()
                else:
                    c1, c2 = st.columns(2)
                    if c1.button("✅", key=f"ok_{lid}", help="Vaxtında"):
                        update_event(lid, r["planned_time"], "OK", "", "", pcc_role)
                        get_fresh_log()
                        st.rerun()
                    if c2.button("⚡", key=f"dl_{lid}", help="Gecikdi"):
                        st.session_state[f"delay_modal_{lid}"] = True

            # Delay modal
            if st.session_state.get(f"delay_modal_{lid}"):
                with st.expander(f"⚡ Gecikmə — {cn}", expanded=True):
                    act_inp = st.text_input("Faktiki vaxt (HH:MM):", key=f"act_{lid}", placeholder="14:35")
                    rsn_inp = st.selectbox("Səbəb (mütləqdir):", ["","Tıxac / Traffic",
                        "Təhlükəsizlik gecikmə","Protokol gecikmə","Hava şəraiti",
                        "VİP tələbi","Texniki problem","Digər"], key=f"rsn_{lid}")
                    if rsn_inp == "Digər":
                        rsn_inp = st.text_input("Səbəbi yazın:", key=f"rsn2_{lid}")
                    note_inp = st.text_input("Qeyd:", key=f"note_{lid}")
                    dc1, dc2 = st.columns(2)
                    if dc1.button("💾 Qeyd et", key=f"save_{lid}"):
                        if not re.match(r"^\d{1,2}:\d{2}$", act_inp.strip()):
                            st.error("HH:MM formatında daxil edin!")
                        elif not rsn_inp:
                            st.error("Səbəb mütləqdir!")
                        else:
                            update_event(lid, act_inp.strip(), "Delay", rsn_inp, note_inp, pcc_role)
                            st.session_state[f"delay_modal_{lid}"] = False
                            get_fresh_log()
                            st.rerun()
                    if dc2.button("Ləğv et", key=f"cancel_{lid}"):
                        st.session_state[f"delay_modal_{lid}"] = False
                        st.rerun()

        st.markdown("<hr style='border-color:#152238;margin:4px 0;'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 3. ÖLKƏ & KORTEJ
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Ölkə & Kortej":
    st.markdown("## 🌍 Ölkə & Kortej Məlumatı")

    tab1, tab2, tab3, tab4 = st.tabs(["🌍 Ölkə Kartı","🚗 Maşınlar","👤 Sürücülər","🤝 LO & Könüllülər"])

    with tab1:
        countries = sorted(delegations["country_name"].tolist())
        sel = st.selectbox("Ölkə seçin:", countries)
        d   = delegations[delegations["country_name"]==sel].iloc[0]

        col1, col2 = st.columns([1,1])
        with col1:
            st.markdown(f"""
            <div style='background:#152238;border:1px solid #D4AF37;border-radius:10px;padding:16px;'>
              <div style='font-size:20px;font-weight:800;color:#D4AF37;margin-bottom:8px;'>{d['leader_name']}</div>
              <div style='font-size:13px;color:#8a9bb0;margin-bottom:12px;'>{d['position']}</div>
              <table style='width:100%;font-size:12px;'>
                <tr><td style='color:#6a8aaa;padding:4px 0;'>🌍 Ölkə</td><td style='color:#c0d0e0;'>{sel}</td></tr>
                <tr><td style='color:#6a8aaa;padding:4px 0;'>📍 PCC</td><td>{pcc_badge(d.get('pcc','—'))}</td></tr>
                <tr><td style='color:#6a8aaa;padding:4px 0;'>🏨 Qarşılama</td><td style='color:#c0d0e0;'>{d['greeting_location']}</td></tr>
                <tr><td style='color:#6a8aaa;padding:4px 0;'>🛣 Marşrut</td><td style='color:#c0d0e0;'>{d['route_description']}</td></tr>
                <tr><td style='color:#6a8aaa;padding:4px 0;'>🏁 Sıra</td><td style='color:#D4AF37;font-weight:700;'>{d['convoy_order']}</td></tr>
              </table>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            # Event timeline for this country
            country_log = log[log["country_name"]==sel].sort_values("convoy_order")
            st.markdown("**⏱ Mərhələ Statusu:**")
            for _, r in country_log.iterrows():
                st_val = r["status"]
                ihs    = r.get("is_handshake","") in [True,"YES","yes","1","True"]
                dot    = "🟣" if ihs else ("🟢" if st_val=="OK" else ("🔴" if st_val=="Delay" else "⚪"))
                act    = r.get("actual_time","")
                st.markdown(f"""
                <div style='display:flex;align-items:center;gap:10px;padding:6px 0;
                  border-bottom:1px solid #1e3a5f;'>
                  <span style='font-size:16px;'>{dot}</span>
                  <div>
                    <div style='font-size:12px;font-weight:600;color:#c0d0e0;'>{r['event_name']}</div>
                    <div style='font-size:10px;color:#6a8aaa;'>Plan: {r['planned_time']}  |  Faktiki: {act or '—'}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

    with tab2:
        # Vehicles
        sel_country = st.selectbox("Ölkə:", ["Hamısı"] + sorted(vehicles["country_name"].unique().tolist()), key="veh_country")
        veh_show = vehicles if sel_country=="Hamısı" else vehicles[vehicles["country_name"]==sel_country]

        CONVOY_COLORS = {"DYP":"#f87171","S1":"#7ab8f5","VVİP":"#fcd34d","P1":"#5fb87a","D1":"#b87af5"}
        for _, v in veh_show.iterrows():
            vstf    = staff[staff["vehicle_id"]==v["vehicle_id"]]
            drivers = vstf[vstf["role"].isin(["Driver 1","Driver 2"])]
            lo      = vstf[vstf["role"]=="LO"]
            ks      = vstf[vstf["role"].isin(["K1","K2","K3"])]
            col     = CONVOY_COLORS.get(v["convoy_type"],"#94a3b8")

            with st.expander(f"{v['convoy_type']} — {v['country_name']} | {v['plate_number']}"):
                c1,c2,c3 = st.columns(3)
                c1.markdown(f"**Növ:** {v.get('car_type','—')}")
                c2.markdown(f"**Nişan:** `{v['plate_number']}`")
                c3.markdown(f"**Məntəqə:** {v.get('location','—')}")
                st.markdown("---")
                for _, drv in drivers.iterrows():
                    st.markdown(f"🚗 **{drv['role']}:** {drv['full_name']} — `{drv['phone_number']}`")
                for _, l in lo.iterrows():
                    st.markdown(f"🎗 **LO:** {l['full_name']} — `{l['phone_number']}`")
                for _, k in ks.iterrows():
                    st.markdown(f"👥 **{k['role']}:** {k['full_name']} — `{k['phone_number']}`")

    with tab3:
        search = st.text_input("🔍 Ad / Telefon / Nişan:", placeholder="Axtar...")
        drv = staff[staff["role"].isin(["Driver 1","Driver 2"])]\
            .merge(vehicles[["vehicle_id","country_name","convoy_type","plate_number"]], on="vehicle_id", how="left")
        if search:
            mask = (drv["full_name"].str.contains(search,case=False,na=False) |
                    drv["phone_number"].str.contains(search,case=False,na=False) |
                    drv["plate_number"].str.contains(search,case=False,na=False))
            drv = drv[mask]
        st.dataframe(drv[["country_name","convoy_type","plate_number","role","full_name","phone_number"]]
            .rename(columns={"country_name":"Ölkə","convoy_type":"Kortej","plate_number":"Nişan",
                             "role":"Rol","full_name":"Ad","phone_number":"Telefon"}),
            use_container_width=True, hide_index=True)

    with tab4:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**🎗 Liaison Officers**")
            lo_df = staff[staff["role"]=="LO"]\
                .merge(vehicles[["vehicle_id","country_name","convoy_type"]], on="vehicle_id", how="left")
            st.dataframe(lo_df[["country_name","convoy_type","full_name","phone_number"]]
                .rename(columns={"country_name":"Ölkə","convoy_type":"Kortej",
                                 "full_name":"Ad","phone_number":"Telefon"}),
                use_container_width=True, hide_index=True)
        with c2:
            st.markdown("**👥 Könüllülər (K1/K2/K3)**")
            k_df = staff[staff["role"].isin(["K1","K2","K3"])]\
                .merge(vehicles[["vehicle_id","country_name","convoy_type"]], on="vehicle_id", how="left")
            st.dataframe(k_df[["country_name","convoy_type","role","full_name","phone_number"]]
                .rename(columns={"country_name":"Ölkə","convoy_type":"Kortej","role":"Rol",
                                 "full_name":"Ad","phone_number":"Telefon"}),
                use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# 4. OTEL & MƏSAFƏ
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏨 Otel & Məsafə":
    st.markdown("## 🏨 Otel & BOS Məsafə Analizi")

    dist_data = hotel_distances()
    df_dist   = pd.DataFrame(dist_data)

    c1,c2 = st.columns(2)
    with c1:
        st.markdown("### 📏 Oteldən BOS-a Məsafə")
        for row in dist_data:
            st.markdown(f"""
            <div style='background:#0f2040;border:1px solid #1e3a5f;border-left:4px solid {row['color']};
              border-radius:8px;padding:12px;margin-bottom:8px;'>
              <div style='font-size:14px;font-weight:700;color:{row['color']};'>{row['hotel']}</div>
              <div style='font-size:12px;color:#c0d0e0;margin-top:4px;'>
                📏 <b>{row['distance_km']} km</b>
              </div>
            </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown("### 🌍 Otel üzrə Delegasiya sayı")
        hotel_counts = delegations.groupby("greeting_location")["country_name"].count().reset_index()
        hotel_counts.columns = ["Otel","Delegasiya sayı"]
        fig = px.bar(hotel_counts, x="Otel", y="Delegasiya sayı",
            color="Delegasiya sayı",
            color_continuous_scale=["#1e3a5f","#D4AF37"])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", font_color="#c0d0e0",
            title_font_color="#D4AF37")
        st.plotly_chart(fig, use_container_width=True)

    # Per hotel delegations
    st.markdown("### 🏨 Otel üzrə Delegasiyalar")
    for hotel in HOTEL_COORDS:
        hotel_dels = delegations[delegations["greeting_location"].str.contains(hotel, na=False, case=False)]
        if hotel_dels.empty:
            continue
        with st.expander(f"🏨 {hotel} — {len(hotel_dels)} delegasiya"):
            for _, d in hotel_dels.iterrows():
                country_log = log[log["country_name"]==d["country_name"]]
                n_ok  = (country_log["status"]=="OK").sum()
                n_dl  = (country_log["status"]=="Delay").sum()
                st.markdown(f"""
                <div style='display:flex;align-items:center;justify-content:space-between;
                  padding:8px 0;border-bottom:1px solid #1e3a5f;'>
                  <div>
                    <span style='color:#D4AF37;font-weight:700;margin-right:8px;'>#{d['convoy_order']}</span>
                    <span style='color:#c0d0e0;font-weight:600;'>{d['country_name']}</span>
                    <span style='color:#8a9bb0;font-size:11px;margin-left:8px;'>{d['leader_name']}</span>
                  </div>
                  <div style='display:flex;gap:6px;'>
                    {pcc_badge(d.get('pcc','—'))}
                    <span class="badge-ok">✓{n_ok}</span>
                    {f'<span class="badge-delay">⚡{n_dl}</span>' if n_dl>0 else ''}
                  </div>
                </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 5. CAN Lİ XƏRİTƏ
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗺️ Canlı Xəritə":
    st.markdown("## 🗺️ Bakı — VIP Kortej Canlı Xəritəsi")

    c1,c2,c3 = st.columns(3)
    map_status = c1.selectbox("Status filtri:", ["Hamısı","OK","Delay","Pending"])
    map_hotel  = c2.selectbox("Otel filtri:", ["Hamısı"] + list(HOTEL_COORDS.keys()))
    map_theme  = c3.selectbox("Xəritə temi:", ["Qaranlıq","Açıq"])

    tile = "CartoDB.DarkMatter" if map_theme=="Qaranlıq" else "CartoDB.Positron"
    m    = folium.Map(location=[40.40, 49.87], zoom_start=12, tiles=tile)

    # Hotels
    for hotel, coords in HOTEL_COORDS.items():
        hotel_dels = delegations[delegations["greeting_location"].str.contains(hotel,na=False,case=False)]
        n = len(hotel_dels)
        folium.CircleMarker(
            [coords["lat"], coords["lon"]], radius=14,
            color=coords["color"], fill=True, fill_color=coords["color"], fill_opacity=0.3,
            popup=folium.Popup(f"<b style='color:{coords['color']}'>{hotel}</b><br>{n} delegasiya", max_width=200),
            tooltip=hotel,
        ).add_to(m)
        folium.Marker(
            [coords["lat"], coords["lon"]],
            icon=folium.DivIcon(html=f"<div style='color:{coords['color']};font-size:10px;font-weight:700;white-space:nowrap;'>{hotel}</div>"),
        ).add_to(m)

    # BOS
    folium.CircleMarker(
        [BOS["lat"], BOS["lon"]], radius=18,
        color="#ff4444", fill=True, fill_color="#ff4444", fill_opacity=0.4,
        tooltip="BOS",
        popup=folium.Popup("<b style='color:#ff4444'>BOS — Bakı Olimpiya Stadionu</b>", max_width=200),
    ).add_to(m)

    # Delegation dots + routes
    log_summ = log.groupby(["country_name","pcc"]).agg(
        has_delay=("status", lambda x: (x=="Delay").any()),
        all_pend=("status",  lambda x: (x=="Pending").all()),
        hs_status=("status", lambda x: x[log[log["country_name"]==x.name[0] if isinstance(x.name,tuple) else x.name]["event_name"]=="Handshake"].values[0] if len(x[log["event_name"]=="Handshake"])>0 else "Pending"),
    ).reset_index() if False else log.groupby("country_name").agg(
        pcc=("pcc","first"),
        has_delay=("status", lambda x:(x=="Delay").any()),
        all_pend=("status",  lambda x:(x=="Pending").all()),
    ).reset_index()

    log_summ["map_status"] = log_summ.apply(
        lambda r: "Delay" if r["has_delay"] else ("Pending" if r["all_pend"] else "OK"), axis=1)
    log_summ["dot_color"] = log_summ["map_status"].map(
        {"OK":"#16a34a","Delay":"#dc2626","Pending":"#f5d020"})

    if map_status != "Hamısı":
        log_summ = log_summ[log_summ["map_status"]==map_status]

    log_summ = log_summ.merge(
        delegations[["country_name","greeting_location","convoy_order"]], on="country_name", how="left")

    if map_hotel != "Hamısı":
        log_summ = log_summ[log_summ["greeting_location"].str.contains(map_hotel,na=False,case=False)]

    for _, r in log_summ.iterrows():
        hotel = r.get("greeting_location","")
        h_coords = next((v for k,v in HOTEL_COORDS.items() if k.lower() in (hotel or "").lower()), None)
        if h_coords is None:
            continue
        # Jitter
        lat = h_coords["lat"] + (r["convoy_order"]-10)*0.00025
        lon = h_coords["lon"] + (r["convoy_order"]%5)*0.0003

        # Route line
        folium.PolyLine(
            [[lat,lon],[BOS["lat"],BOS["lon"]]],
            color=r["dot_color"], weight=1.5, opacity=0.5, dash_array="6 4",
        ).add_to(m)

        # Delegation marker
        st_lbl = {"OK":"✓ Vaxtında","Delay":"⚡ Gecikmiş"}.get(r["map_status"],"⏳ Gözləyir")
        folium.CircleMarker(
            [lat,lon], radius=8,
            color=r["dot_color"], fill=True,
            fill_color=r["dot_color"], fill_opacity=0.9,
            tooltip=r["country_name"],
            popup=folium.Popup(
                "<div style='min-width:160px'><b>" + str(r["country_name"]) + "</b><br>"
                + str(r["pcc"]) + "<br>"
                + "<b style='color:" + str(r["dot_color"]) + "'>" + str(st_lbl) + "</b><br>"
                + str(hotel) + "</div>", max_width=200),
        ).add_to(m)

    st_folium(m, height=560, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 6. GPS İZLƏMƏ
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📡 GPS İzləmə":
    st.markdown("## 📡 Sürücü GPS İzləmə")

    tab1, tab2 = st.tabs(["🗺️ Canlı Xəritə","📱 Sürücü Linki"])

    with tab1:
        gps_data = get_gps()
        if gps_data.empty:
            st.info("Hələ GPS məlumatı yoxdur. Sürücülər 'Sürücü Linki' tabından GPS göndərə bilər.")
        else:
            m2 = folium.Map(location=[40.40,49.87], zoom_start=12, tiles="CartoDB.DarkMatter")
            # Hotels
            for hotel, coords in HOTEL_COORDS.items():
                folium.CircleMarker([coords["lat"],coords["lon"]], radius=10,
                    color=coords["color"], fill=True, fill_color=coords["color"],
                    fill_opacity=0.3, tooltip=hotel).add_to(m2)
            # BOS
            folium.CircleMarker([BOS["lat"],BOS["lon"]], radius=15,
                color="#ff4444", fill=True, fill_color="#ff4444", fill_opacity=0.4, tooltip="BOS").add_to(m2)
            # GPS dots
            for _, g in gps_data.iterrows():
                folium.Marker(
                    [g["lat"],g["lon"]],
                    icon=folium.DivIcon(html=f"""
                    <div style='background:#D4AF37;color:#071120;font-size:10px;font-weight:700;
                      padding:3px 7px;border-radius:12px;white-space:nowrap;'>
                      🚗 {g['country']}
                    </div>"""),
                    tooltip=f"{g['country']} — {g['driver_name']}",
                    popup=folium.Popup(
                        f"<b>{g['country']}</b><br>{g['driver_name']}<br>"
                        f"Speed: {g.get('speed_kmh',0)} km/h<br>"
                        f"Updated: {g.get('updated_at','')[:19]}", max_width=200),
                ).add_to(m2)
            st_folium(m2, height=500, use_container_width=True)
            st.dataframe(gps_data[["country","driver_name","lat","lon","speed_kmh","updated_at"]],
                use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("### 📱 Sürücü GPS Göndərmə")
        st.info("Aşağıdakı formu sürücü telefonunda açaraq GPS koordinatlarını göndərə bilər.")

        with st.form("gps_form"):
            col1,col2 = st.columns(2)
            v_country = col1.selectbox("Ölkə:", sorted(vehicles["country_name"].unique()))
            v_id      = col2.selectbox("Kortej:", ["DYP","S1","VVİP","P1","D1"])

            # Driver name from staff
            veh_match = vehicles[(vehicles["country_name"]==v_country)&(vehicles["convoy_type"]==v_id)]
            if not veh_match.empty:
                vid      = veh_match.iloc[0]["vehicle_id"]
                drv_match= staff[(staff["vehicle_id"]==vid)&(staff["role"]=="Driver 1")]
                drv_name = drv_match.iloc[0]["full_name"] if not drv_match.empty else ""
            else:
                drv_name = ""

            st.markdown(f"**Sürücü:** {drv_name}")
            lat_inp = st.number_input("Latitude:",  value=40.3983, format="%.6f")
            lon_inp = st.number_input("Longitude:", value=49.8672, format="%.6f")
            spd_inp = st.number_input("Sürət (km/h):", value=0.0, min_value=0.0)

            if st.form_submit_button("📡 GPS Göndər"):
                upsert_gps(f"{v_country}_{v_id}", v_country, drv_name, lat_inp, lon_inp, spd_inp)
                st.success(f"✅ {v_country} — GPS göndərildi!")
                st.rerun()

     
# ══════════════════════════════════════════════════════════════════════════════
# 6b. SÜRÜCÜ GPS SƏHİFƏSİ
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📱 Sürücü GPS":
    st.markdown("## 📱 Sürücü GPS Göndərmə")

    # URL parametrindən driver ID al
    params = st.query_params
    driver_id = params.get("driver", "")

    st.markdown("""
    <div style='background:#0f2040;border:1px solid #D4AF37;border-radius:10px;
      padding:20px;margin-bottom:20px;'>
      <div style='font-size:13px;color:#D4AF37;font-weight:700;margin-bottom:10px;'>
        📱 Bu səhifəni sürücüyə göndər
      </div>
      <div style='font-size:11px;color:#8a9bb0;'>
        Sürücü bu linki telefonunda açır → "GPS Göndər" düyməsini basır →
        koordinatlar avtomatik göndərilir
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Sürücü məlumatları
    col1, col2 = st.columns(2)
    with col1:
        from data_loader import load_excel
        _, vehicles, staff, _, _ = load_excel()
        v_country = st.selectbox("Ölkə:", sorted(vehicles["country_name"].unique()))
        v_type    = st.selectbox("Kortej:", ["DYP","S1","VVİP","P1","D1"])

    with col2:
        veh_m = vehicles[(vehicles["country_name"]==v_country)&(vehicles["convoy_type"]==v_type)]
        if not veh_m.empty:
            vid      = veh_m.iloc[0]["vehicle_id"]
            drv_m    = staff[(staff["vehicle_id"]==vid)&(staff["role"]=="Driver 1")]
            drv_name = drv_m.iloc[0]["full_name"] if not drv_m.empty else "Sürücü"
        else:
            drv_name = "Sürücü"
        st.markdown(f"<br><div style='color:#D4AF37;font-weight:700;margin-top:20px;'>👤 {drv_name}</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📍 GPS Koordinat Göndər")

    # JavaScript ilə real telefon GPS
    st.components.v1.html("""
    <div style="font-family:Arial;background:#0f2040;padding:20px;border-radius:10px;
      border:1px solid #D4AF37;max-width:400px;margin:0 auto;">
      <div id="status" style="color:#8a9bb0;font-size:12px;margin-bottom:12px;">
        GPS hazırlanır...
      </div>
      <div id="coords" style="font-family:monospace;font-size:13px;color:#5fb87a;
        margin-bottom:16px;"></div>
      <button onclick="getGPS()" style="background:#D4AF37;color:#071120;border:none;
        padding:12px 24px;border-radius:8px;font-weight:700;font-size:14px;
        cursor:pointer;width:100%;">
        📍 GPS Koordinatı Al
      </button>
    </div>
    <script>
    function getGPS() {
      var status = document.getElementById('status');
      var coords = document.getElementById('coords');
      status.innerText = 'GPS alınır...';
      status.style.color = '#D4AF37';
      if (!navigator.geolocation) {
        status.innerText = 'GPS dəstəklənmir!';
        status.style.color = '#f87171';
        return;
      }
      navigator.geolocation.getCurrentPosition(
        function(pos) {
          var lat = pos.coords.latitude.toFixed(6);
          var lon = pos.coords.longitude.toFixed(6);
          var spd = pos.coords.speed ? (pos.coords.speed * 3.6).toFixed(1) : 0;
          coords.innerText = 'Lat: ' + lat + '\nLon: ' + lon + '\nSürət: ' + spd + ' km/h';
          status.innerText = '✅ GPS alındı! Aşağıdakı dəyərləri kopyala:';
          status.style.color = '#5fb87a';
          // Streamlit-ə göndər
          window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: {lat: parseFloat(lat), lon: parseFloat(lon), speed: parseFloat(spd)}
          }, '*');
        },
        function(err) {
          status.innerText = 'GPS xətası: ' + err.message;
          status.style.color = '#f87171';
        },
        {enableHighAccuracy: true, timeout: 10000}
      );
    }
    // Avtomatik al
    getGPS();
    setInterval(getGPS, 15000);
    </script>
    """, height=200)

    st.markdown("---")
    st.markdown("**Əl ilə daxil et (GPS işləməsə):**")
    col1, col2, col3 = st.columns(3)
    lat_inp = col1.number_input("Latitude:",  value=40.3983, format="%.6f", step=0.0001)
    lon_inp = col2.number_input("Longitude:", value=49.8672, format="%.6f", step=0.0001)
    spd_inp = col3.number_input("Sürət (km/h):", value=0.0, min_value=0.0, step=1.0)

    if st.button("📡 GPS Göndər", use_container_width=True):
        vehicle_id = f"{v_country}_{v_type}"
        upsert_gps(vehicle_id, v_country, drv_name, lat_inp, lon_inp, spd_inp)
        st.success(f"✅ {v_country} — {drv_name} GPS göndərildi!")
        st.markdown(f"""
        <div style='background:#0a2010;border:1px solid #16a34a;border-radius:8px;
          padding:12px;font-family:monospace;font-size:12px;color:#5fb87a;'>
          📍 Lat: {lat_inp} | Lon: {lon_inp} | Sürət: {spd_inp} km/h
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 7. SSENARİ MODU
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧮 Ssenari Modu":
    st.markdown("## 🧮 Ssenari Modu — Çatma & Çıxış Hesablaması")

    tab1, tab2, tab3 = st.tabs(["⏱ Ssenari A — Eyni anda","🔢 Ssenari B — İnterval","🕐 Zaman Xətti"])

    with tab1:
        st.markdown("### Hamı eyni anda BOS-a çatsın → çıxış vaxtları")
        c1,c2 = st.columns(2)
        arr_time = c1.text_input("BOS çatma vaxtı (HH:MM):", value="15:45")
        speed_a  = c2.slider("Orta sürət (km/saat):", 20, 80, 40)

        if st.button("▶ Hesabla (Ssenari A)"):
            res = scenario_simultaneous(arr_time, speed_a)
            df  = pd.DataFrame(res)
            st.markdown("#### Nəticə:")
            for row in res:
                st.markdown(f"""
                <div style='background:#0f2040;border:1px solid #1e3a5f;
                  border-left:4px solid #D4AF37;border-radius:8px;
                  padding:12px;margin-bottom:8px;
                  display:flex;justify-content:space-between;align-items:center;'>
                  <div>
                    <span style='color:#D4AF37;font-weight:700;font-size:14px;'>{row['hotel']}</span>
                    <span style='color:#8a9bb0;font-size:11px;margin-left:10px;'>{row['distance_km']} km</span>
                  </div>
                  <div style='text-align:right;'>
                    <div style='color:#f87171;font-size:10px;'>Çıxış</div>
                    <div style='color:#f87171;font-family:monospace;font-weight:700;font-size:16px;'>{row['departure_time']}</div>
                  </div>
                  <div style='text-align:right;'>
                    <div style='color:#5fb87a;font-size:10px;'>Çatma</div>
                    <div style='color:#5fb87a;font-family:monospace;font-weight:700;font-size:16px;'>{row['arrival_time']}</div>
                  </div>
                  <div style='text-align:right;'>
                    <div style='color:#8a9bb0;font-size:10px;'>Yol</div>
                    <div style='color:#c0d0e0;font-family:monospace;'>{row['travel_min']} dəq</div>
                  </div>
                </div>""", unsafe_allow_html=True)

    with tab2:
        st.markdown("### N saniyə intervalla BOS-a çatmaq")
        c1,c2,c3 = st.columns(3)
        first_arr   = c1.text_input("İlk çatma vaxtı (HH:MM):", value="15:45")
        interval_s  = c2.number_input("İnterval (saniyə):", value=50, min_value=10, max_value=300, step=5)
        speed_b     = c3.slider("Sürət (km/saat):", 20, 80, 40, key="spd_b")

        if st.button("▶ Hesabla (Ssenari B)"):
            res2 = scenario_staggered(first_arr, int(interval_s), speed_b)
            df2  = pd.DataFrame(res2)
            st.markdown("#### Nəticə:")

            # Merge with delegations to show which countries from each hotel
            hotel_dels_map = {}
            for _, d in delegations.iterrows():
                for hotel in HOTEL_COORDS:
                    if hotel.lower() in (d.get("greeting_location","") or "").lower():
                        hotel_dels_map.setdefault(hotel, []).append(f"#{d['convoy_order']} {d['country_name']}")

            for row in res2:
                dels = hotel_dels_map.get(row["hotel"], [])
                dels_str = ", ".join(dels[:3]) + ("..." if len(dels)>3 else "")
                st.markdown(f"""
                <div style='background:#0f2040;border:1px solid #1e3a5f;
                  border-radius:8px;padding:12px;margin-bottom:8px;'>
                  <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <div>
                      <span style='color:#D4AF37;font-weight:700;font-size:14px;'>
                        #{row['sira']} {row['hotel']}
                      </span>
                      <span style='color:#8a9bb0;font-size:11px;margin-left:10px;'>
                        {row['distance_km']} km | {row['travel_min']} dəq
                      </span>
                    </div>
                    <div style='display:flex;gap:20px;'>
                      <div style='text-align:center;'>
                        <div style='color:#f87171;font-size:10px;'>Çıxış</div>
                        <div style='color:#f87171;font-family:monospace;font-weight:700;font-size:15px;'>{row['departure_time']}</div>
                      </div>
                      <div style='text-align:center;'>
                        <div style='color:#5fb87a;font-size:10px;'>BOS Çatma</div>
                        <div style='color:#5fb87a;font-family:monospace;font-weight:700;font-size:15px;'>{row['arrival_time']}</div>
                      </div>
                    </div>
                  </div>
                  {f'<div style="font-size:10px;color:#6a8aaa;margin-top:6px;">Delegasiyalar: {dels_str}</div>' if dels_str else ''}
                </div>""", unsafe_allow_html=True)

    with tab3:
        st.markdown("### ⏱ Bütün Delegasiyalar — Zaman Xətti")
        log_tl = log.sort_values(["convoy_order","event_name"])
        tl_data = []
        for _, r in log_tl.iterrows():
            tl_data.append({
                "Ölkə":       r["country_name"],
                "Mərhələ":    r["event_name"],
                "Plan":       r["planned_time"],
                "Faktiki":    r.get("actual_time","") or "—",
                "Status":     r["status"],
                "PCC":        r["pcc"],
            })
        df_tl = pd.DataFrame(tl_data)
        pivot = df_tl.pivot_table(index=["Ölkə","PCC"], columns="Mərhələ",
            values="Plan", aggfunc="first").reset_index()
        pivot.columns = [str(c) for c in pivot.columns]
        # Reorder columns
        cols = ["Ölkə","PCC"] + [c for c in EVENT_ORDER if c in pivot.columns]
        pivot = pivot[[c for c in cols if c in pivot.columns]]
        st.dataframe(pivot, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# 8. HESABAT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📄 Hesabat":
    st.markdown("## 📄 Rəsmi Hesabat")

    c1,c2 = st.columns(2)
    with c1:
        st.markdown("### ⚙️ Parametrlər")
        rpt_operator  = st.text_input("Hazırlayan:", value="Protokol Xidməti")
        rpt_event     = st.text_input("Tədbir adı:", value="VIP Kortej Koordinasiya")
        rpt_del  = st.checkbox("Delegasiya icmalı",   value=True)
        rpt_hs   = st.checkbox("Handshake performansı", value=True)
        rpt_dl   = st.checkbox("Gecikmə analizi",     value=True)
        rpt_pcc  = st.checkbox("PCC performansı",     value=True)

    with c2:
        st.markdown("### 📊 Cari Statistika")
        log_r = pcc_filter(log)
        tot   = len(log_r)
        nok   = (log_r["status"]=="OK").sum()
        ndl   = (log_r["status"]=="Delay").sum()
        npd   = (log_r["status"]=="Pending").sum()
        pdl   = round(ndl/tot*100,1) if tot>0 else 0
        cls   = "GOOD" if pdl==0 else ("WARNING" if pdl<20 else "CRITICAL")
        cls_col = {"GOOD":"#16a34a","WARNING":"#D4AF37","CRITICAL":"#dc2626"}[cls]

        r1,r2 = st.columns(2)
        r1.metric("Ümumi hadisə", tot)
        r2.metric("Vaxtında",    f"{nok} ({round(nok/tot*100,1) if tot>0 else 0}%)")
        r3,r4 = st.columns(2)
        r3.metric("Gecikmiş",    f"{ndl} ({pdl}%)")
        r4.metric("Gözləyir",    npd)

        st.markdown(f"""
        <div style='background:#0f2040;border:2px solid {cls_col};border-radius:10px;
          padding:16px;text-align:center;margin-top:12px;'>
          <div style='font-size:22px;font-weight:900;color:{cls_col};
            letter-spacing:3px;'>{cls}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📥 Yüklə")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📄 Word Hesabat Hazırla", use_container_width=True):
            with st.spinner("Hazırlanır..."):
                word_bytes = generate_word_report(
                    log_r, delegations,
                    operator=rpt_operator,
                    event_name=rpt_event,
                )
                st.download_button(
                    label="⬇️ Word (.docx) Yüklə",
                    data=word_bytes,
                    file_name=f"Protokol_Hesabat_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

    with col2:
        # Gecikmiş cədvəl
        if not log_r[log_r["status"]=="Delay"].empty:
            st.markdown("**⚡ Gecikmiş Hadisələr:**")
            dl_show = log_r[log_r["status"]=="Delay"][["pcc","country_name","event_name","planned_time","actual_time","delay_reason"]]\
                .rename(columns={"pcc":"PCC","country_name":"Ölkə","event_name":"Mərhələ",
                                 "planned_time":"Plan","actual_time":"Faktiki","delay_reason":"Səbəb"})
            st.dataframe(dl_show, use_container_width=True, hide_index=True)

# ── Auto-refresh every 10 seconds ─────────────────────────────────────────────
time.sleep(0.5)
clock_ph.markdown(
    f"<div style='text-align:center;font-size:22px;font-weight:700;color:#D4AF37;font-family:monospace;'>"
    f"{datetime.now().strftime('%H:%M:%S')}</div>",
    unsafe_allow_html=True
)
