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
    st.title("📊 Reportes y Gráficos de Alertas")
    st.markdown("---")

    df = obtener_alertas()
    if df.empty:
        st.warning("No hay alertas registradas.")
        return

    # -------------------------------
    # Sidebar: Filtros en cascada
    # -------------------------------
    st.sidebar.header("Filtros de Alertas")

    # Rango de fechas
    df["fechaAlerta"] = pd.to_datetime(df["fechaAlerta"])
    min_fecha = df["fechaAlerta"].min()
    max_fecha = df["fechaAlerta"].max()
    rango = st.sidebar.date_input("Rango de fechas", [min_fecha, max_fecha])
    if len(rango) == 2:
        ini, fin = rango
        df = df[(df["fechaAlerta"] >= pd.to_datetime(ini)) & (df["fechaAlerta"] <= pd.to_datetime(fin))]

    # Filtro por Línea
    lineas = obtener_lineas()
    opciones_linea = {nombre: id for id, nombre in lineas}
    linea = st.sidebar.selectbox("Línea de Producción", ["Todas"] + list(opciones_linea.keys()))
    if linea != "Todas":
        df = df[df["idLinea"] == opciones_linea[linea]]
        linea_id = opciones_linea[linea]
    else:
        linea_id = None

    # Filtro por Presentación
    presentaciones = obtener_presentaciones()
    if linea_id:
        presentaciones = [p for p in presentaciones if p[2]==linea_id]  # filtrar por línea
    opciones_pres = {nombre: id for id, nombre, _ in presentaciones}
    presentacion = st.sidebar.selectbox("Presentación", ["Todas"] + list(opciones_pres.keys()))
    if presentacion != "Todas":
        df = df[df["idPresentacion"] == opciones_pres[presentacion]]
        pres_id = opciones_pres[presentacion]
    else:
        pres_id = None

    # Filtro por Tipo de Control
    tipos = obtener_tipos_control()
    if linea_id:
        tipos = [t for t in tipos if t[2]==linea_id]  # filtrar por línea
    opciones_tipo = {nombre: id for id, nombre, _ in tipos}
    tipo_control = st.sidebar.selectbox("Tipo de Control", ["Todos"] + list(opciones_tipo.keys()))
    if tipo_control != "Todos":
        df = df[df["idTipoControl"] == opciones_tipo[tipo_control]]
        tipo_id = opciones_tipo[tipo_control]
    else:
        tipo_id = None

    # Filtro por Parámetro
    parametros = obtener_parametros()
    if tipo_id:
        parametros = [p for p in parametros if p[2]==tipo_id]
    opciones_param = {nombre: id for id, nombre, _ in parametros}
    parametro = st.sidebar.selectbox("Parámetro", ["Todos"] + list(opciones_param.keys()))
    if parametro != "Todos":
        df = df[df["idParametro"] == opciones_param[parametro]]

    st.subheader("📌 Total de alertas encontradas:")
    st.info(f"**{len(df)} alertas**")
    st.markdown("---")

    # ============================================
    #     1) GRÁFICO PUNTUAL FUERA DE LÍMITES
    # ============================================
    st.subheader("🔴 Alertas fuera de límites")
    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.scatter(df["fechaAlerta"], df["valorFuera"])
        ax.set_xlabel("Fecha")
        ax.set_ylabel("Valor fuera de rango")
        ax.set_title("Puntos donde se generaron alertas")
        plt.xticks(rotation=45)
        st.pyplot(fig)
    else:
        st.warning("No hay datos para mostrar este gráfico.")

    st.markdown("---")

    # ============================================
    #     2) GRÁFICO DE BARRAS
    # ============================================
    st.subheader("📊 Gráfico de barras: Alertas por día")
    if not df.empty:
        df_bar = df.copy()
        df_bar["dia"] = df_bar["fechaAlerta"].dt.date
        conteo = df_bar.groupby("dia").size()
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(conteo.index, conteo.values)
        ax.set_title("Cantidad de alertas por día")
        ax.set_xlabel("Fecha")
        ax.set_ylabel("Alertas")
        plt.xticks(rotation=45)
        st.pyplot(fig)
    else:
        st.warning("No hay datos para mostrar este gráfico.")

    st.markdown("---")

    # ============================================
    #     TABLA DE DETALLE
    # ============================================
    st.subheader("📋 Tabla de alertas filtradas")
    st.dataframe(df)

    st.download_button(
        label="📥 Descargar Excel",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="alertas_filtradas.csv",
        mime="text/csv"
    )
