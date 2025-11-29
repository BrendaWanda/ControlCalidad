# modules/graficos_alertas.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from database.db_connection import get_connection
from datetime import datetime

# ============================================
#   CONSULTAS A BASE DE DATOS
# ============================================

def obtener_alertas():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.idAlerta, a.tipoAlerta, a.descripcion, a.idControl, a.idParametro,
               a.idLinea, a.idDetalle, a.valorFuera, a.limiteInferior, a.limiteSuperior,
               a.fechaAlerta, a.estado, a.idOrdenTrabajo, a.idPresentacion,
               c.resultado, c.fechaControl, c.idTipoControl
        FROM alerta a
        LEFT JOIN controlcalidad c ON a.idControl = c.idControl
        ORDER BY a.fechaAlerta DESC;
    """)
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return pd.DataFrame(data)

def obtener_lineas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT idLinea, nombreLinea FROM lineaproduccion ORDER BY nombreLinea;")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

def obtener_presentaciones():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT idPresentacion, nombrePresentacion, idLinea FROM presentacionproducto ORDER BY nombrePresentacion;")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

def obtener_tipos_control():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT idTipoControl, nombreTipo, idLinea FROM tipocontrol ORDER BY nombreTipo;")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

def obtener_parametros():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT idParametro, nombreParametro, idTipoControl FROM parametrocalidad ORDER BY nombreParametro;")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

# ============================================
#   MÓDULO PRINCIPAL DE GRÁFICOS
# ============================================

def ver_graficos_alertas():
    st.set_page_config(page_title="Alertas de Calidad", layout="wide")
    st.title("🚨 Reporte de Alertas de Calidad")
    st.caption("Monitoreo de desviaciones fuera de límites")
    st.markdown("---")

    df = obtener_alertas()
    if df.empty:
        st.warning("No hay alertas registradas.")
        return

    df["fechaAlerta"] = pd.to_datetime(df["fechaAlerta"])

    # -------------------------------
    # Sidebar: Filtros en cascada
    # -------------------------------
    st.sidebar.header("🔎 Filtros de Alertas")

    min_fecha = df["fechaAlerta"].min()
    max_fecha = df["fechaAlerta"].max()

    rango = st.sidebar.date_input("📅 Rango de fechas", [min_fecha, max_fecha])
    if len(rango) == 2:
        ini, fin = rango
        df = df[(df["fechaAlerta"] >= pd.to_datetime(ini)) & (df["fechaAlerta"] <= pd.to_datetime(fin))]

    # Línea
    lineas = obtener_lineas()
    opciones_linea = {nombre: id for id, nombre in lineas}
    linea = st.sidebar.selectbox("🏭 Línea", ["Todas"] + list(opciones_linea.keys()))
    linea_id = opciones_linea.get(linea) if linea != "Todas" else None

    if linea_id:
        df = df[df["idLinea"] == linea_id]

    # Presentación
    presentaciones = obtener_presentaciones()
    if linea_id:
        presentaciones = [p for p in presentaciones if p[2] == linea_id]

    opciones_pres = {nombre: id for id, nombre, _ in presentaciones}
    presentacion = st.sidebar.selectbox("📦 Presentación", ["Todas"] + list(opciones_pres.keys()))
    pres_id = opciones_pres.get(presentacion) if presentacion != "Todas" else None

    if pres_id:
        df = df[df["idPresentacion"] == pres_id]

    # Tipo de Control
    tipos = obtener_tipos_control()
    if linea_id:
        tipos = [t for t in tipos if t[2] == linea_id]

    opciones_tipo = {nombre: id for id, nombre, _ in tipos}
    tipo_control = st.sidebar.selectbox("🧪 Tipo de Control", ["Todos"] + list(opciones_tipo.keys()))
    tipo_id = opciones_tipo.get(tipo_control) if tipo_control != "Todos" else None

    if tipo_id:
        df = df[df["idTipoControl"] == tipo_id]

    # Parámetro
    parametros = obtener_parametros()
    if tipo_id:
        parametros = [p for p in parametros if p[2] == tipo_id]

    opciones_param = {nombre: id for id, nombre, _ in parametros}
    parametro = st.sidebar.selectbox("📏 Parámetro", ["Todos"] + list(opciones_param.keys()))

    if parametro != "Todos":
        df = df[df["idParametro"] == opciones_param[parametro]]

    # ===============================
    #          KPIs SUPERIORES
    # ===============================
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("🚨 Total Alertas", len(df))
    col2.metric("🔴 Fuera de Límite", df["valorFuera"].notna().sum())
    col3.metric("✅ Cerradas", df[df["estado"] == "Cerrada"].shape[0] if "estado" in df else 0)
    col4.metric("⏳ Pendientes", df[df["estado"] != "Cerrada"].shape[0] if "estado" in df else 0)

    st.markdown("---")

    # ===============================
    #        GRÁFICOS EN 2 COLUMNAS
    # ===============================
    colA, colB = st.columns(2)

    # --- GRÁFICO PUNTUAL ---
    with colA:
        st.subheader("🔴 Alertas fuera de límites")
        fig, ax = plt.subplots()
        ax.scatter(df["fechaAlerta"], df["valorFuera"])
        ax.set_xlabel("Fecha")
        ax.set_ylabel("Valor fuera de rango")
        plt.xticks(rotation=45)
        st.pyplot(fig)

    # --- GRÁFICO BARRAS ---
    with colB:
        st.subheader("📊 Alertas por día")
        df_bar = df.copy()
        df_bar["dia"] = df_bar["fechaAlerta"].dt.date
        conteo = df_bar.groupby("dia").size()

        fig2, ax2 = plt.subplots()
        ax2.bar(conteo.index, conteo.values)
        ax2.set_xlabel("Fecha")
        ax2.set_ylabel("Cantidad")
        plt.xticks(rotation=45)
        st.pyplot(fig2)

    st.markdown("---")

    # ===============================
    #      TABLA DE DETALLE
    # ===============================
    st.subheader("📋 Detalle de Alertas")
    st.dataframe(df, use_container_width=True)

    st.download_button(
        label="📥 Descargar Alertas (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="alertas_filtradas.csv",
        mime="text/csv"
    )
