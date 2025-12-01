import streamlit as st
import pandas as pd
from datetime import datetime
from .utils import get_conn

def ver_registros_guardados():
    st.title("Registros Guardados de Control de Calidad")
    st.markdown("---")

    conn = get_conn()
    query = """
        SELECT
            c.idControl,
            c.fechaControl,
            o.codigoOrden,
            l.nombreLinea,
            p.nombrePresentacion,
            tc.nombreTipo AS tipoControl,
            pa.nombreParametro,
            c.resultado,
            c.observaciones,
            c.idUsuario,
            c.idDetalle
        FROM controlcalidad c
        LEFT JOIN ordentrabajo o ON o.idOrdenTrabajo = c.idOrdenTrabajo
        LEFT JOIN lineaproduccion l ON l.idLinea = c.idLinea
        LEFT JOIN presentacionproducto p ON p.idPresentacion = c.idPresentacion
        LEFT JOIN tipocontrol tc ON tc.idTipoControl = c.idTipoControl
        LEFT JOIN parametrocalidad pa ON pa.idParametro = c.idParametro
        ORDER BY c.fechaControl DESC
    """
    df = pd.read_sql(query, conn)

    if df.empty:
        st.info("No hay registros.")
        return

    st.subheader("Filtros")

    #  1) ORDEN
    col1, col2, col3 = st.columns(3)
    with col1:
        orden = st.selectbox(
            "Orden",
            ["Todas"] + sorted(df["codigoOrden"].dropna().unique().tolist())
        )

    df_fil = df.copy()
    if orden != "Todas":
        df_fil = df_fil[df_fil["codigoOrden"] == orden]

    #  2) LÍNEA
    with col2:
        lineas_disp = sorted(df_fil["nombreLinea"].dropna().unique().tolist())
        linea = st.selectbox("Línea", ["Todas"] + lineas_disp)

    if linea != "Todas":
        df_fil = df_fil[df_fil["nombreLinea"] == linea]

    #  3) PRESENTACIÓN
    with col3:
        presentaciones_disp = sorted(df_fil["nombrePresentacion"].dropna().unique().tolist())
        presentacion = st.selectbox("Presentación", ["Todas"] + presentaciones_disp)

    if presentacion != "Todas":
        df_fil = df_fil[df_fil["nombrePresentacion"] == presentacion]

    #  4) TIPO DE CONTROL
    col4 = st.columns(1)[0]
    with col4:
        tipos_disp = sorted(df_fil["tipoControl"].dropna().unique().tolist())
        tipo = st.selectbox("Tipo de control", ["Todos"] + tipos_disp)

    if tipo != "Todos":
        df_fil = df_fil[df_fil["tipoControl"] == tipo]

    #  5) PARÁMETRO (DEPENDIENTE)
    col5 = st.columns(1)[0]
    with col5:
        parametros_disp = sorted(df_fil["nombreParametro"].dropna().unique().tolist())
        parametro = st.selectbox("Parámetro", ["Todos"] + parametros_disp)

    if parametro != "Todos":
        df_fil = df_fil[df_fil["nombreParametro"] == parametro]

    #  6) FECHA
    col6, col7 = st.columns(2)
    with col6:
        usar_fecha = st.checkbox("Filtrar por Fecha")

    with col7:
        fecha = st.date_input("Fecha", datetime.now().date()) if usar_fecha else None

    if usar_fecha and fecha:
        df_fil = df_fil[pd.to_datetime(df_fil["fechaControl"]).dt.date == fecha]

    #   RESULTADOS
    st.subheader("Resultados")
    st.dataframe(df_fil, use_container_width=True)

    #   EXPORTAR
    if not df_fil.empty:
        colx, coly = st.columns(2)
        with colx:
            csv = df_fil.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Exportar CSV",
                csv,
                file_name="controles_filtrados.csv",
                mime="text/csv"
            )

        with coly:
            try:
                excel_bytes = to_excel_bytes(df_fil)
                st.download_button(
                    "Exportar Excel",
                    excel_bytes,
                    file_name="controles_filtrados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except:
                pass

    #   DETALLE POR REGISTRO
    st.markdown("### Detalle por registro")
    for _, row in df_fil.iterrows():
        with st.expander(f"Control {row['idControl']} — {row['nombreParametro']}"):
            st.write(f"**Orden:** {row['codigoOrden']}")
            st.write(f"**Línea:** {row['nombreLinea']}")
            st.write(f"**Presentación:** {row['nombrePresentacion']}")
            st.write(f"**Tipo:** {row['tipoControl']}")
            st.write(f"**Parámetro:** {row['nombreParametro']}")
            st.write(f"**Resultado:** {row['resultado']}")
            st.write(f"**Observaciones:** {row['observaciones']}")
            st.write(f"**Usuario ID:** {row['idUsuario']}")
            st.write(f"**Detalle ID:** {row['idDetalle']}")

# Exportar a Excel
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    from io import BytesIO
    import pandas as pd
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Controles")
    return buf.getvalue()