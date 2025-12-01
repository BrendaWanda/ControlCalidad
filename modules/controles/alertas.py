import streamlit as st
from .utils import get_conn
import pandas as pd

def ver_alertas():
    st.title("Historial de Alertas")
    st.markdown("---")

    conn = get_conn()
    df = pd.read_sql("""
        SELECT 
            a.idAlerta, a.tipoAlerta, a.descripcion, a.fechaAlerta, a.estado,
            a.idControl, a.idOrdenTrabajo, a.idLinea, a.idParametro, 
            a.idPresentacion, a.valorFuera, a.limiteInferior, a.limiteSuperior,
            o.codigoOrden, l.nombreLinea, p.nombrePresentacion, 
            par.nombreParametro, tc.nombreTipo AS tipoControl
        FROM alerta a
        LEFT JOIN ordentrabajo o ON a.idOrdenTrabajo = o.idOrdenTrabajo
        LEFT JOIN lineaproduccion l ON a.idLinea = l.idLinea
        LEFT JOIN presentacionproducto p ON a.idPresentacion = p.idPresentacion
        LEFT JOIN parametrocalidad par ON a.idParametro = par.idParametro
        LEFT JOIN controlcalidad c ON c.idControl = a.idControl
        LEFT JOIN tipocontrol tc ON tc.idTipoControl = c.idTipoControl
        ORDER BY a.fechaAlerta DESC
    """, conn)

    if df.empty:
        st.info("No hay alertas registradas.")
        return

    st.subheader("Filtros")

    # ============================================================
    # 1) ORDEN
    # ============================================================
    col1, col2, col3 = st.columns(3)

    with col1:
        orden_sel = st.selectbox(
            "Orden",
            ["Todas"] + sorted(df["codigoOrden"].dropna().unique().tolist())
        )

    df_fil = df.copy()
    if orden_sel != "Todas":
        df_fil = df_fil[df_fil["codigoOrden"] == orden_sel]

    # ============================================================
    # 2) LÍNEA
    # ============================================================
    with col2:
        lineas_disp = sorted(df_fil["nombreLinea"].dropna().unique().tolist())
        linea_sel = st.selectbox("Línea", ["Todas"] + lineas_disp)

    if linea_sel != "Todas":
        df_fil = df_fil[df_fil["nombreLinea"] == linea_sel]

    # ============================================================
    # 3) PRESENTACIÓN
    # ============================================================
    with col3:
        present_disp = sorted(df_fil["nombrePresentacion"].dropna().unique().tolist())
        present_sel = st.selectbox("Presentación", ["Todas"] + present_disp)

    if present_sel != "Todas":
        df_fil = df_fil[df_fil["nombrePresentacion"] == present_sel]

    # ============================================================
    # 4) TIPO DE CONTROL
    # ============================================================
    col4 = st.columns(1)[0]
    with col4:
        tipo_disp = sorted(df_fil["tipoControl"].dropna().unique().tolist())
        tipo_sel = st.selectbox("Tipo de Control", ["Todos"] + tipo_disp)

    if tipo_sel != "Todos":
        df_fil = df_fil[df_fil["tipoControl"] == tipo_sel]

    # ============================================================
    # 5) PARÁMETRO (DEPENDIENTE)
    # ============================================================
    col5 = st.columns(1)[0]
    with col5:
        param_disp = sorted(df_fil["nombreParametro"].dropna().unique().tolist())
        param_sel = st.selectbox("Parámetro", ["Todos"] + param_disp)

    if param_sel != "Todos":
        df_fil = df_fil[df_fil["nombreParametro"] == param_sel]

    # ============================================================
    # 6) ESTADO (se mantiene como filtro adicional)
    # ============================================================
    col6 = st.columns(1)[0]
    with col6:
        estado_disp = sorted(df["estado"].dropna().unique().tolist())
        estado_sel = st.selectbox("Estado", ["Todos"] + estado_disp)

    if estado_sel != "Todos":
        df_fil = df_fil[df_fil["estado"] == estado_sel]

    # ============================================================
    #  RESULTADOS
    # ============================================================
    st.subheader("Resultados")
    st.dataframe(df_fil, use_container_width=True)

    # ============================================================
    #  CONFIRMAR / CERRAR ALERTA
    # ============================================================
    st.markdown("### Confirmar / Cerrar Alerta")

    id_alerta = st.text_input("ID de alerta para confirmar/cerrar")
    nuevo_estado = st.selectbox("Acción", ["confirmada", "en_proceso", "rechazada"])
    comentario = st.text_area("Comentario (opcional)")

    if st.button("Actualizar estado"):
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE alerta SET estado = %s WHERE idAlerta = %s",
                (nuevo_estado, int(id_alerta))
            )
            conn.commit()
            st.success("Alerta actualizada.")
            st.rerun()
        except Exception as e:
            st.error(f"Error actualizando alerta: {e}")
        finally:
            conn.close()
