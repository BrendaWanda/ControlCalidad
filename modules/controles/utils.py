"""
Utilities for modules.controles:
- DB helpers
- insert/save helpers
- session user extraction
"""
import pandas as pd
import streamlit as st
from database.db_connection import get_connection

def get_conn():
    return get_connection()

def fetch_df(query, params=None):
    conn = get_conn()
    try:
        df = pd.read_sql(query, conn, params=params)
        return df
    finally:
        conn.close()

def insert_control_record(cursor, fecha_hora, resultado, observaciones, id_usuario,
                            id_param, id_tipo, id_linea, id_detalle, id_orden, id_presentacion):
    cursor.execute("""
        INSERT INTO controlcalidad
        (fechaControl, resultado, observaciones, idUsuario, idParametro, idTipoControl,
            idLinea, idDetalle, idOrdenTrabajo, idPresentacion)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (fecha_hora, resultado, observaciones, id_usuario, id_param, id_tipo,
            id_linea, id_detalle, id_orden, id_presentacion))

def save_alert(cursor, tipo, descripcion, id_control=None, id_orden=None, id_linea=None,
                id_param=None, id_presentacion=None, valor=None, lim_inf=None, lim_sup=None, estado="pendiente"):
    # Try insert with extended columns; fallback to minimal insert if schema differs
    try:
        cursor.execute("""
            INSERT INTO alerta
            (tipoAlerta, descripcion, idControl, idOrdenTrabajo, idLinea, idParametro, idPresentacion,
                valorFuera, limiteInferior, limiteSuperior, fechaAlerta, estado)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s)
        """, (tipo, descripcion, id_control, id_orden, id_linea, id_param, id_presentacion, valor, lim_inf, lim_sup, estado))
    except Exception:
        cursor.execute("INSERT INTO alerta (tipoAlerta, descripcion, idControl, fechaAlerta, estado) VALUES (%s,%s,%s,NOW(),%s)",
                        (tipo, descripcion, id_control, estado))

def get_user_id_from_session():
    # Flexible extraction: many possible session_state shapes
    if "usuario_id" in st.session_state:
        return st.session_state["usuario_id"]
    if "idUsuario" in st.session_state:
        return st.session_state["idUsuario"]
    if "usuario" in st.session_state:
        usr = st.session_state["usuario"]
        if isinstance(usr, dict):
            return usr.get("idUsuario") or usr.get("id") or usr.get("id_user")
        else:
            return getattr(usr, "idUsuario", None) or getattr(usr, "id", None)
    return None
