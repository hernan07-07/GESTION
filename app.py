import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import secrets
import unicodedata
import os
import streamlit.components.v1 as components

# 1. CONFIGURACIÓN
st.set_page_config(page_title="TONUCOS Gestor", layout="wide")

# --- FUNCIONES NÚCLEO ---
def normalizar_texto(texto):
    if not texto: return ""
    texto = str(texto).upper().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto)
                  if unicodedata.category(c) != 'Mn')

def conectar_google_sheet(nombre_archivo):
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        s = st.secrets["gcp_service_account"]
        p_key = s["private_key"].replace("\\n", "\n")
        creds_info = {
            "type": s["type"], "project_id": s["project_id"],
            "private_key_id": s["private_key_id"], "private_key": p_key,
            "client_email": s["client_email"], "client_id": s["client_id"],
            "auth_uri": s["auth_uri"], "token_uri": s["token_uri"],
            "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
            "client_x509_cert_url": s["client_x509_cert_url"]
        }
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        return client.open(nombre_archivo).worksheet("Invitados")
    except Exception as e:
        st.error(f"Error conexión: {e}")
        return None

def cargar_datos(archivo):
    sheet = conectar_google_sheet(archivo)
    if sheet:
        df = get_as_dataframe(sheet, evaluate_formulas=True, dtype=str).dropna(how='all')
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        for col in ["ID", "Mesa", "Nombre", "Categoria", "Observaciones", "Asistio"]:
            if col not in df.columns: df[col] = ""
        return df.fillna("")
    return pd.DataFrame(columns=["ID", "Mesa", "Nombre", "Categoria", "Observaciones", "Asistio"])

def guardar_datos(df_to_save, archivo):
    sheet = conectar_google_sheet(archivo)
    if sheet:
        sheet.clear()
        set_with_dataframe(sheet, df_to_save.drop(columns=['Mesa_Num'], errors='ignore'))

# --- DISEÑO CSS (ALTO CONTRASTE Y COLORES DE CATEGORÍA) ---
st.markdown("""
    <style>
    .stApp { background-color: #e9ecef; }
    .block-container { padding-top: 0.5rem !important; }
    
    /* Totales */
    .total-black { background-color: #000; color: #fff; padding: 5px; border-radius: 4px; text-align: center; border: 1px solid #000; }
    .total-grey { background-color: #ffffff; border: 2px solid #000; padding: 5px; border-radius: 4px; text-align: center; color: #000; font-weight: bold; }
    
    /* Encabezados de Mesa */
    .mesa-header { background-color: #000; color: #fff; padding: 8px 15px; font-weight: bold; margin-top: 15px; border-radius: 4px; display: flex; align-items: center; gap: 15px; }
    .mesa-header span.count { background-color: #fff; color: #000; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
    
    /* Inputs y Bordes */
    .stTextInput input { height: 35px !important; border: 1.5px solid #000 !important; background-color: #ffffff !important; color: #000 !important; font-weight: 500; }
    div[data-baseweb="select"] { border: 1.5px solid #000 !important; background-color: #ffffff !important; }
    
    /* Botón Guardar Alineado */
    .stButton button { border: 1.5px solid #000 !important; font-weight: bold !important; }
    
    .stExpander { border: 2px solid #000 !important; background-color: #ffffff !important; border-radius: 8px !important; }
    .event-title { text-align: center; font-size: 22px; font-weight: bold; color: #000; margin-bottom: 10px; }
    
    #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
query_params = st.query_params
nombre_evento = query_params.get("id", "Boda Juan y Marta").replace("_", " ")

if 'df' not in st.session_state or st.session_state.get('last_event') != nombre_evento:
    st.session_state.df = cargar_datos(nombre_evento)
    st.session_state.last_event = nombre_evento

if "focus_key" not in st.session_state:
    st.session_state.focus_key = 0

# --- CABECERA ---
c_l, c_c, c_r = st.columns([1, 1, 1])
with c_c:
    if os.path.exists("logonegro.jpg"):
        st.image("logonegro.jpg", width=120)

st.markdown(f"<div class='event-title'>{nombre_evento.upper()}</div>", unsafe_allow_html=True)

# --- PANEL DE TOTALES ---
df_full = st.session_state.df
if not df_full.empty:
    mesas_reales = df_full[df_full['Mesa'].str.strip() != "0"]['Mesa'].nunique()
    cols = st.columns(6)
    data = [("MESAS", mesas_reales, "grey"), ("TOTAL", len(df_full), "black"), 
            ("MAYOR", len(df_full[df_full['Categoria']=='MAYOR']), "grey"),
            ("ADOL.", len(df_full[df_full['Categoria']=='ADOLESCENTE']), "grey"),
            ("MENOR", len(df_full[df_full['Categoria']=='MENOR']), "grey"),
            ("BEBÉ", len(df_full[df_full['Categoria']=='BEBÉ']), "grey")]
    
    for i, (lab, val, style) in enumerate(data):
        cols[i].markdown(f"<div class='total-{style}'><small>{lab}</small><br><b>{val}</b></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- REGISTRO ---
with st.expander("➕ AÑADIR NUEVO INVITADO", expanded=True):
    with st.form("alta", clear_on_submit=True):
        f1, f2 = st.columns([1, 3])
        f_m = f1.text_input("MESA", key=f"focus_{st.session_state.focus_key}")
        f_n = f2.text_input("APELLIDO y nombre")
        f3, f4 = st.columns(2)
        f_c = f3.selectbox("CATEGORÍA", ["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"])
        f_o = f4.text_input("OBSERVACIONES")
        
        if st.form_submit_button("📥 AÑADIR A LA LISTA", use_container_width=True):
            if f_n:
                nuevo = pd.DataFrame([{"ID": secrets.token_hex(3).upper(), "Mesa": f_m if f_m else "0", 
                                       "Nombre": f_n.upper(), "Categoria": f_c, "Observaciones": f_o.upper(), "Asistio": "NO"}])
                st.session_state.df = pd.concat([st.session_state.df, nuevo], ignore_index=True)
                guardar_datos(st.session_state.df, nombre_evento)
                st.session_state.focus_key += 1
                st.toast(f"Añadido: {f_n.upper()}", icon="✅")
                st.rerun()

# --- BUSCADOR Y BOTÓN GUARDAR (ALINEADOS) ---
st.markdown("---")
col_search, col_save = st.columns([3, 1])
with col_search:
    s_query = normalizar_texto(st.text_input("🔍 BUSCAR INVITADO", placeholder="Escribe el nombre aquí..."))
with col_save:
    st.write("<div style='margin-top:28px'></div>", unsafe_allow_html=True) # Espaciador para alinear
    if st.button("💾 GUARDAR CAMBIOS", use_container_width=True):
        guardar_datos(st.session_state.df, nombre_evento)
        st.toast("¡Cambios guardados!", icon="☁️")

# --- LISTADO Y EDICIÓN ---
df_v = st.session_state.df.copy()
if s_query:
    df_v = df_v[df_v['Nombre'].apply(lambda x: s_query in normalizar_texto(x))]

if not df_v.empty:
    df_v['Mesa_Int'] = pd.to_numeric(df_v['Mesa'], errors='coerce').fillna(0).astype(int)
    # Colores vivos para las categorías
    cat_colors = {"MAYOR": "#ced4da", "ADOLESCENTE": "#90cdf4", "MENOR": "#9ae6b4", "BEBÉ": "#feb2b2"}

    for mesa in sorted(df_v['Mesa_Int'].unique()):
        invs = df_v[df_v['Mesa_Int'] == mesa]
        st.markdown(f"""
            <div class='mesa-header'>
                <span>🪑 MESA {mesa}</span>
                <span class='count'>{len(invs)} PERS.</span>
            </div>
        """, unsafe_allow_html=True)
        
        for idx, row in invs.iterrows():
            c1, c2, c3, c4, c5 = st.columns([0.6, 2.5, 1.5, 1.5, 0.4])
            
            # Campo Mesa
            new_m = c1.text_input(f"m_{idx}", row['Mesa'], label_visibility="collapsed")
            if new_m != row['Mesa']: st.session_state.df.at[idx, 'Mesa'] = new_m
            
            # Campo Nombre
            new_n = c2.text_input(f"n_{idx}", row['Nombre'], label_visibility="collapsed")
            if new_n != row['Nombre']: st.session_state.df.at[idx, 'Nombre'] = new_n.upper()
            
            # Campo Categoría con Color
            cat_val = row['Categoria'].upper()
            bg_color = cat_colors.get(cat_val, "#ffffff")
            st.markdown(f'<style>div[data-baseweb="select"]:has(input[aria-label*="c_{idx}"]) {{ background-color: {bg_color} !important; }}</style>', unsafe_allow_html=True)
            
            new_c = c3.selectbox(f"c_{idx}", ["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"], 
                                 index=["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"].index(cat_val), label_visibility="collapsed")
            if new_c != row['Categoria']:
                st.session_state.df.at[idx, 'Categoria'] = new_c
            
            # Campo Observaciones
            new_o = c4.text_input(f"o_{idx}", row['Observaciones'], label_visibility="collapsed", placeholder="Obs...")
            if new_o != row['Observaciones']: st.session_state.df.at[idx, 'Observaciones'] = new_o.upper()
                
            if c5.button("🗑️", key=f"del_{idx}"):
                st.session_state.df = st.session_state.df.drop(idx)
                guardar_datos(st.session_state.df, nombre_evento)
                st.rerun()