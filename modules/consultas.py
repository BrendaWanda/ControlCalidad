# modules/consultas.py
import streamlit as st
import pandas as pd
import plotly.express as px
from database.db_connection import get_connection
from datetime import datetime, timedelta

# ================================================================
# FUNCIONES BASE DE DATOS
# ================================================================

def obtener_lineas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT idLinea, nombreLinea FROM lineaproduccion ORDER BY nombreLinea;")
    data = cursor.fetchall()
    conn.close()
    return data


def obtener_presentaciones_por_linea(idLinea):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT idPresentacion, nombrePresentacion 
        FROM presentacionproducto 
        WHERE idLinea = %s
        ORDER BY nombrePresentacion;
    """, (idLinea,))
    data = cursor.fetchall()
    conn.close()
    return data


def obtener_parametros_por_presentacion(idPresentacion):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.idParametro, p.nombreParametro
        FROM parametrocalidad p 
        JOIN presentacionparametro pp 
            ON pp.idParametro = p.idParametro
        WHERE pp.idPresentacion = %s
        ORDER BY p.nombreParametro;
    """, (idPresentacion,))
    data = cursor.fetchall()
    conn.close()
    return data


def obtener_limites_parametro(idPresentacion, idParametro):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tipoParametro, limiteInferior, limiteSuperior 
        FROM presentacionparametro 
        WHERE idPresentacion = %s AND idParametro = %s;
    """, (idPresentacion, idParametro))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "tipo": row[0],
            "inferior": row[1],
            "superior": row[2]
        }
    return None


def obtener_registros(idLinea, idPresentacion, idParametro, fecha_ini, fecha_fin):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT r.fechaRegistro, r.valor, 
                   l.nombreLinea, 
                   p.nombrePresentacion, 
                   pa.nombreParametro
            FROM registrocalidad r
            JOIN lineaproduccion l ON l.idLinea = r.idLinea
            JOIN presentacionproducto p ON p.idPresentacion = r.idPresentacion
            JOIN parametrocalidad pa ON pa.idParametro = r.idParametro
            WHERE r.idLinea = %s
              AND r.idPresentacion = %s
              AND r.idParametro = %s
              AND DATE(r.fechaRegistro) BETWEEN %s AND %s
            ORDER BY r.fechaRegistro;
        """

        cursor.execute(query, (idLinea, idPresentacion, idParametro, fecha_ini, fecha_fin))
        rows = cursor.fetchall()

    except Exception as e:
        st.error("❌ No se encontró la tabla 'registrocalidad'.")
        st.error("✅ Revisa el nombre real de la tabla en tu base de datos.")
        st.exception(e)

        cursor.execute("SHOW TABLES;")
        tablas = cursor.fetchall()
        st.info(f"Tablas existentes: {tablas}")

        return pd.DataFrame()

    finally:
        conn.close()

    df = pd.DataFrame(rows, columns=[
        "Fecha", "Valor", "Línea", "Presentación", "Parámetro"
    ])

    return df



# ================================================================
# MÓDULO PRINCIPAL DE CONSULTAS
# ================================================================

def ver_registros():
    st.title("📊 Consultas de Registros de Calidad")
    st.markdown("---")

    # -----------------------------
    # LÍNEAS
    # -----------------------------
    lineas = obtener_lineas()
    if not lineas:
        st.error("❌ No existen líneas registradas.")
        return

    linea_dict = {l[1]: l[0] for l in lineas}
    linea_sel = st.selectbox("Seleccione la línea:", list(linea_dict.keys()), index=0)

    if not linea_sel:
        return

    # -----------------------------
    # PRESENTACIONES
    # -----------------------------
    presentaciones = obtener_presentaciones_por_linea(linea_dict[linea_sel])

    if not presentaciones:
        st.warning("❌ Esta línea no tiene presentaciones registradas.")
        return

    pre_dict = {p[1]: p[0] for p in presentaciones}
    present_sel = st.selectbox("Seleccione la presentación:", list(pre_dict.keys()), index=0)

    if not present_sel:
        return

    # -----------------------------
    # PARÁMETROS
    # -----------------------------
    parametros = obtener_parametros_por_presentacion(pre_dict[present_sel])

    if not parametros:
        st.warning("❌ Esta presentación no tiene parámetros configurados.")
        return

    param_dict = {p[1]: p[0] for p in parametros}
    param_sel = st.selectbox("Seleccione el parámetro:", list(param_dict.keys()), index=0)

    if not param_sel:
        return

    # -----------------------------
    # FECHAS
    # -----------------------------
    hoy = datetime.now().date()
    fecha_ini = st.date_input("Fecha inicial:", hoy - timedelta(days=7))
    fecha_fin = st.date_input("Fecha final:", hoy)

    if fecha_ini > fecha_fin:
        st.error("❌ La fecha inicial no puede ser mayor que la final.")
        return

    # -----------------------------
    # CARGAR DATOS
    # -----------------------------
    df = obtener_registros(
        linea_dict[linea_sel],
        pre_dict[present_sel],
        param_dict[param_sel],
        fecha_ini,
        fecha_fin
    )

    if df.empty:
        st.warning("⚠️ No existen registros para los filtros seleccionados.")
        return

    # -----------------------------------------------------
    # CONFORMIDAD AUTOMÁTICA
    # -----------------------------------------------------
    limites = obtener_limites_parametro(pre_dict[present_sel], param_dict[param_sel])

    if limites and limites["tipo"] == "NUM":
        inf = float(limites["inferior"])
        sup = float(limites["superior"])

        df["Valor"] = df["Valor"].astype(float)

        df["Conforme"] = df["Valor"].apply(
            lambda v: "✔ Conforme" if inf <= v <= sup else "❌ No Conforme"
        )
    else:
        df["Conforme"] = "N/A"

    # -----------------------------
    # TABLA
    # -----------------------------
    st.subheader("📄 Tabla de registros")
    st.dataframe(df, use_container_width=True)

    # -----------------------------------------------------
    # GRÁFICOS INTERACTIVOS
    # -----------------------------------------------------
    st.subheader("📈 Evolución del parámetro")
    fig_line = px.line(df, x="Fecha", y="Valor", title="Evolución del parámetro")
    st.plotly_chart(fig_line, use_container_width=True)

    st.subheader("📦 Distribución del parámetro")
    fig_box = px.box(df, y="Valor", title="Distribución del parámetro")
    st.plotly_chart(fig_box, use_container_width=True)

    if limites and limites["tipo"] == "NUM":
        st.subheader("🟩 Conformidad Global")
        conf_df = df["Conforme"].value_counts().reset_index()
        conf_df.columns = ["Estado", "Cantidad"]

        fig_bar = px.bar(conf_df, x="Estado", y="Cantidad", title="Conformidad")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.success("✅ Consulta generada correctamente")