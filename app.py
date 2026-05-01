import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN DE CONEXIÓN ---
SUPABASE_URL = "https://bsukwllutoxmedamscof.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJzdWt3bGx1dG94bWVkYW1zY29mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc1MDU4NDgsImV4cCI6MjA5MzA4MTg0OH0.qKVXRLYFYSb_rJPjdpkvSPxljzTdBsmtwvnPGv_veoQ"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="AC-BOTS Licorería Premium", layout="wide")

# --- 2. FUNCIONES DE BASE DE DATOS ---
def obtener_datos(tabla):
    res = supabase.table(tabla).select("*").execute()
    df = pd.DataFrame(res.data)
    if not df.empty and 'fecha_hora' in df.columns:
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'])
    return df

def actualizar_stock(nombre_prod, cantidad_cambio, operacion="restar"):
    res = supabase.table("productos").select("stock").eq("nombre", nombre_prod).execute()
    if res.data:
        stock_actual = res.data[0]['stock']
        nuevo_stock = stock_actual - cantidad_cambio if operacion == "restar" else stock_actual + cantidad_cambio
        supabase.table("productos").update({"stock": nuevo_stock}).eq("nombre", nombre_prod).execute()

# --- 3. INTERFAZ ---
st.title("🍾 Sistema de Gestión AC-BOTS")
menu = st.sidebar.radio("Navegación:", ["Ventas", "Entradas", "Inventario", "Editar Productos", "Reporte Detallado"])

# --- SECCIÓN: INVENTARIO ---
if menu == "Inventario":
    st.header("📦 Control de Inventario")
    with st.expander("➕ AGREGAR NUEVO PRODUCTO"):
        with st.form("nuevo_p", clear_on_submit=True):
            n = st.text_input("Nombre")
            p = st.number_input("Precio ($)", min_value=0.0)
            s = st.number_input("Stock Inicial", min_value=0)
            if st.form_submit_button("REGISTRAR"):
                if n:
                    supabase.table("productos").insert({"nombre": n, "precio": p, "stock": s}).execute()
                    st.success(f"{n} registrado.")
                    st.rerun()

    df_p = obtener_datos("productos")
    if not df_p.empty:
        stock_bajo = df_p[df_p['stock'] <= 5]
        if not stock_bajo.empty:
            for _, fila in stock_bajo.iterrows():
                st.warning(f"⚠️ STOCK BAJO: {fila['nombre']} ({fila['stock']} unid.)")
        st.dataframe(df_p, use_container_width=True, hide_index=True)

# --- SECCIÓN: VENTAS ---
elif menu == "Ventas":
    st.header("💰 Nueva Venta")
    df_p = obtener_datos("productos")
    if not df_p.empty:
        p_sel = st.selectbox("Producto:", df_p['nombre'])
        info = df_p[df_p['nombre'] == p_sel].iloc[0]
        c_sel = st.number_input("Cantidad:", min_value=1, max_value=int(info['stock']) if info['stock'] > 0 else 1)
        total = info['precio'] * c_sel
        st.subheader(f"Total: ${total:.2f}")
        if st.button("VENDER"):
            supabase.table("ventas").insert({
                "producto": p_sel, "cantidad": c_sel, "total": total, 
                "fecha_hora": datetime.now().isoformat()
            }).execute()
            actualizar_stock(p_sel, c_sel, "restar")
            st.success("Venta guardada.")
            st.rerun()

# --- SECCIÓN: ENTRADAS ---
elif menu == "Entradas":
    st.header("🚚 Ingreso de Mercadería")
    df_p = obtener_datos("productos")
    if not df_p.empty:
        with st.form("ent"):
            p_e = st.selectbox("¿Qué llegó?", df_p['nombre'])
            c_e = st.number_input("Cantidad:", min_value=1)
            if st.form_submit_button("Ingresar"):
                supabase.table("entradas").insert({
                    "producto": p_e, "cantidad": c_e, 
                    "fecha_hora": datetime.now().isoformat()
                }).execute()
                actualizar_stock(p_e, c_e, "sumar")
                st.success("Inventario actualizado.")
                st.rerun()

# --- SECCIÓN: EDITAR PRODUCTOS ---
elif menu == "Editar Productos":
    st.header("✏️ Modificar Bebidas")
    df_p = obtener_datos("productos")
    if not df_p.empty:
        p_edit = st.selectbox("Seleccione bebida:", df_p['nombre'])
        datos = df_p[df_p['nombre'] == p_edit].iloc[0]
        with st.form("edit"):
            nuevo_n = st.text_input("Nombre:", value=datos['nombre'])
            nuevo_p = st.number_input("Precio:", value=float(datos['precio']))
            if st.form_submit_button("GUARDAR"):
                supabase.table("productos").update({"nombre": nuevo_n, "precio": nuevo_p}).eq("id", datos['id']).execute()
                st.success("Cambios realizados.")
                st.rerun()

# --- SECCIÓN: REPORTE DETALLADO (CON FILTRO DE FECHAS RECUPERADO) ---
elif menu == "Reporte Detallado":
    st.header("📊 Inteligencia de Negocio")
    
    df_v = obtener_datos("ventas")
    
    if not df_v.empty:
        # AQUÍ ESTÁ EL SELECTOR DE RANGO QUE FALTABA
        st.subheader("📅 Filtrar Reportes")
        hoy = datetime.now().date()
        filtro = st.date_input("Seleccione el periodo de análisis:", [hoy - timedelta(days=7), hoy])
        
        if len(filtro) == 2:
            # Filtramos los datos según el rango
            df_v_f = df_v[(df_v['fecha_hora'].dt.date >= filtro[0]) & (df_v['fecha_hora'].dt.date <= filtro[1])]
            
            st.metric("Ventas Totales en el Periodo", f"${df_v_f['total'].sum():.2f}")
            
            tab1, tab2, tab3 = st.tabs(["🍺 Por Marca", "📈 Evolución Temporal", "🚚 Historial de Entradas"])
            
            with tab1:
                resumen = df_v_f.groupby('producto').agg({'cantidad': 'sum', 'total': 'sum'}).reset_index()
                st.dataframe(resumen, use_container_width=True, hide_index=True)
                st.bar_chart(resumen.set_index('producto')['total'])
            
            with tab2:
                df_v_f['Fecha'] = df_v_f['fecha_hora'].dt.date
                st.line_chart(df_v_f.groupby('Fecha')['total'].sum())
                st.dataframe(df_v_f.sort_values(by="fecha_hora", ascending=False), use_container_width=True)

            with tab3:
                df_e = obtener_datos("entradas")
                if not df_e.empty:
                    st.dataframe(df_e.sort_values(by="fecha_hora", ascending=False), use_container_width=True)
    else:
        st.info("No hay datos para mostrar.")
