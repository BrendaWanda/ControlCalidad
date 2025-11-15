import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_connection import get_connection
from modules.estandares import obtener_lineas_produccion, obtener_tipos_control, obtener_parametros_por_tipo


# ============================================================
# OBTENER TIPOS POR LÍNEA
# ============================================================
def obtener_tipos_por_linea(id_linea):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT idTipoControl, nombreTipo, descripcion
        FROM TipoControl
        WHERE idLinea = %s
        ORDER BY nombreTipo
    """, (id_linea,))
    data = cursor.fetchall()
    conn.close()
    return data


# ============================================================
# REGISTRO PRINCIPAL DE CONTROL DE CALIDAD
# ============================================================
def registrar_control():
    st.title("Registro de Controles de Calidad")
    st.markdown("---")

    # =============================
    # 1️⃣ SELECCIÓN DE LÍNEA
    # =============================
    lineas = obtener_lineas_produccion()
    opciones_lineas = ["— Seleccionar Línea —"] + [l[1] for l in lineas]

    linea_sel = st.selectbox("Seleccione la línea de producción", opciones_lineas)

    if linea_sel == "— Seleccionar Línea —":
        st.info("Seleccione una línea para continuar.")
        return

    id_linea = next(l[0] for l in lineas if l[1] == linea_sel)

    # =============================
    # 2️⃣ SELECCIÓN DE TIPO DE CONTROL
    # =============================
    tipos = obtener_tipos_por_linea(id_linea)

    if not tipos:
        st.warning("No hay tipos de control configurados para esta línea.")
        return

    opciones_tipos = ["— Seleccionar Tipo de Control —"] + [t["nombreTipo"] for t in tipos]

    tipo_sel = st.selectbox("Seleccione el tipo de control", opciones_tipos)

    if tipo_sel == "— Seleccionar Tipo de Control —":
        return

    id_tipo = next(t["idTipoControl"] for t in tipos if t["nombreTipo"] == tipo_sel)

    # =============================
    # 3️⃣ CARGAR PARÁMETROS DEL TIPO DE CONTROL
    # =============================
    df_param = obtener_parametros_por_tipo(id_tipo)

    if df_param.empty:
        st.warning("Este tipo de control no tiene parámetros configurados.")
        return

    st.subheader("Parámetros a Registrar")
    st.markdown("Ingrese los valores medidos:")

    resultados = {}
    for _, row in df_param.iterrows():
        nombre = row["nombreParametro"]
        unidad = row["unidadMedida"]
        lim_inf = row["limiteInferior"]
        lim_sup = row["limiteSuperior"]

        # Campo numérico para el parámetro
        valor = st.number_input(
            f"{nombre} ({unidad}) — Rango permitido: {lim_inf} a {lim_sup}",
            step=0.01,
            format="%.2f"
        )

        resultados[row["idParametro"]] = {
            "valor": valor,
            "nombre": nombre,
            "lim_inf": lim_inf,
            "lim_sup": lim_sup
        }

    observaciones = st.text_area("Observaciones generales (opcional)")

    # =============================
    # 4️⃣ GUARDAR REGISTRO
    # =============================
    if st.button("Guardar Control", use_container_width=True):

        id_usuario = st.session_state["usuario"]["idUsuario"]

        conn = get_connection()
        cursor = conn.cursor()

        for id_param, data in resultados.items():

            cursor.execute("""
                INSERT INTO ControlCalidad (fechaControl, resultado, observaciones, idUsuario, idParametro)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                datetime.now(),
                data["valor"],
                observaciones,
                id_usuario,
                id_param
            ))

        conn.commit()
        conn.close()

        st.success("Control registrado correctamente para todos los parámetros.")
        st.balloons()


# ============================================================
# VER ALERTAS (placeholder inicial)
# ============================================================
def ver_alertas():
    st.title("Alertas Automáticas")
    st.info("Módulo en construcción — Se activará cuando un parámetro esté fuera de límites.")


# ============================================================
# CONFIRMAR REGISTROS (placeholder inicial)
# ============================================================
def confirmar_registros():
    st.title("Confirmación de Registros")
    st.info("Aquí los supervisores podrán confirmar los controles ingresados.")
