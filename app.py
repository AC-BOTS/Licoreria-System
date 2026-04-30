import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta
from io import BytesIO

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

def eliminar_producto(id_prod):
    supabase.table("productos").delete().eq("id", id_prod).execute()

# --- 3. INTERFAZ ---
st.title("🍾 Sistema de Gestión AC-BOTS")
menu = st.sidebar.radio("Navegación:", ["Ventas", "Entradas", "Inventario", "Editar Productos", "Reporte Detallado"])

# --- SECCIÓN: INVENTARIO ---
if menu == "Inventario":
    st.header("📦 Control de Inventario")
    df_p = obtener_datos("productos")
    if not df_p.empty:
        stock_bajo = df_p[df_p['stock'] <= 5]
        if not stock_bajo.empty:
            for _, fila in stock_bajo.iterrows():
                st.warning(f"⚠️ ¡STOCK BAJO! Solo quedan {fila['stock']} unidades de {fila['nombre']}.")
        st.dataframe(df_p, use_container_width=True, hide_index=True)
    else: st.info("Inventario vacío.")

# --- SECCIÓN: VENTAS ---
elif menu == "Ventas":
    st.header("💰 Nueva Venta")
    df_p = obtener_datos("productos")
    if not df_p.empty:
        p_sel = st.selectbox("Seleccione la bebida:", df_p['nombre'])
        info = df_p[df_p['nombre'] == p_sel].iloc[0]
        c_sel = st.number_input("Cantidad:", min_value=1, max_value=int(info['stock']))
        total = info['precio'] * c_sel
        st.subheader(f"Total: ${total:.2f}")
        if st.button("CONFIRMAR VENTA"):
            supabase.table("ventas").insert({"producto": p_sel, "cantidad": c_sel, "total": total, "fecha_hora": datetime.now().isoformat()}).execute()
            actualizar_stock(p_sel, c_sel, "restar")
            st.success(f"Venta de {p_sel} registrada.")
            st.rerun()

# --- SECCIÓN: ENTRADAS ---
elif menu == "Entradas":
    st.header("🚚 Ingreso de Mercadería")
    df_p = obtener_datos("productos")
    if not df_p.empty:
        with st.form("ent"):
            p_e = st.selectbox("¿Qué bebida llegó?", df_p['nombre'])
            c_e = st.number_input("Cantidad recibida:", min_value=1)
            if st.form_submit_button("Actualizar Inventario"):
                # Aquí se guarda la fecha y hora exacta de llegada
                supabase.table("entradas").insert({"producto": p_e, "cantidad": c_e, "fecha_hora": datetime.now().isoformat()}).execute()
                actualizar_stock(p_e, c_e, "sumar")
                st.success(f"Stock de {p_e} actualizado.")
                st.rerun()

# --- SECCIÓN: EDITAR PRODUCTOS ---
elif menu == "Editar Productos":
    st.header("✏️ Modificar Bebidas")
    df_p = obtener_datos("productos")
    if not df_p.empty:
        prod_edit = st.selectbox("Seleccione la bebida:", df_p['nombre'])
        datos_prod = df_p[df_p['nombre'] == prod_edit].iloc[0]
        with st.form("edit_form"):
            nuevo_nombre = st.text_input("Nombre:", value=datos_prod['nombre'])
            nuevo_precio = st.number_input("Precio ($):", value=float(datos_prod['precio']), min_value=0.0, step=0.10)
            if st.form_submit_button("GUARDAR CAMBIOS"):
                supabase.table("productos").update({"nombre": nuevo_nombre, "precio": nuevo_precio}).eq("id", datos_prod['id']).execute()
                st.success("Cambios guardados.")
                st.rerun()

# --- SECCIÓN: REPORTE DETALLADO (Historial de Entradas Recuperado) ---
elif menu == "Reporte Detallado":
    st.header("📊 Análisis y Trazabilidad AC-BOTS")
    
    tab1, tab2, tab3 = st.tabs(["📈 Ventas por Marca", "📅 Ventas Diarias", "🚚 Historial de Entradas"])
    
    df_v = obtener_datos("ventas")
    df_e = obtener_datos("entradas") # Traemos los datos de mercadería nueva
    
    with tab1:
        if not df_v.empty:
            hoy = datetime.now().date()
            filtro = st.date_input("Rango para ventas:", [hoy - timedelta(days=7), hoy])
            if len(filtro) == 2:
                df_v_f = df_v[(df_v['fecha_hora'].dt.date >= filtro[0]) & (df_v['fecha_hora'].dt.date <= filtro[1])]
                resumen = df_v_f.groupby('producto').agg({'cantidad': 'sum', 'total': 'sum'}).reset_index()
                st.dataframe(resumen, use_container_width=True, hide_index=True)
                st.bar_chart(resumen.set_index('producto')['total'])
        else: st.info("Sin ventas registradas.")

    with tab2:
        if not df_v.empty:
            df_v['Fecha'] = df_v['fecha_hora'].dt.date
            st.line_chart(df_v.groupby('Fecha')['total'].sum())
            st.subheader("Detalle de cada factura")
            st.dataframe(df_v.sort_values(by="fecha_hora", ascending=False), use_container_width=True)

    with tab3:
        st.subheader("📦 Registro de llegada de mercadería")
        if not df_e.empty:
            # Aquí se muestra exactamente cuándo llegó cada bebida
            df_e_display = df_e.sort_values(by="fecha_hora", ascending=False)
            st.dataframe(df_e_display, use_container_width=True, hide_index=True)
            st.info("Este reporte permite saber cuándo se aumentó el inventario y por qué cantidad.")
        else:
            st.info("No hay registros de entradas (mercadería nueva) todavía.")