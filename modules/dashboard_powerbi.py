import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database.db_connection import get_connection
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# Carga de tablas
@st.cache_data(ttl=300)
def cargar_tablas_dashboard():
    conn = get_connection()
    tablas = {}
    try:
        tablas['controles'] = pd.read_sql("""
            SELECT cc.*, p.nombreParametro, p.unidadMedida, p.limiteInferior, p.limiteSuperior,
                    pr.nombrePresentacion, pr.idLinea AS pres_idLinea,
                    tc.nombreTipo AS nombreTipoControl, l.nombreLinea,
                    d.lote
            FROM controlcalidad cc
            LEFT JOIN parametrocalidad p ON cc.idParametro = p.idParametro
            LEFT JOIN presentacionproducto pr ON cc.idPresentacion = pr.idPresentacion
            LEFT JOIN tipocontrol tc ON cc.idTipoControl = tc.idTipoControl
            LEFT JOIN lineaproduccion l ON cc.idLinea = l.idLinea
            LEFT JOIN detalleordentrabajo d ON cc.idDetalle = d.idDetalle
        """, conn, parse_dates=['fechaControl'])
    except Exception:
        # Estructura mínima si falla
        tablas['controles'] = pd.DataFrame(columns=[
            'idControl','fechaControl','idOrdenTrabajo','resultado','observaciones','idUsuario',
            'idParametro','idPresentacion','idTipoControl','idLinea','idDetalle','sabor',
            'nombreParametro','unidadMedida','limiteInferior','limiteSuperior','nombrePresentacion','pres_idLinea','nombreTipoControl','nombreLinea','lote'
        ])

    # presentacionproducto
    try:
        tablas['presentacionproducto'] = pd.read_sql("SELECT idPresentacion, nombrePresentacion, idLinea, codigoPresentacion FROM presentacionproducto;", conn)
    except Exception:
        tablas['presentacionproducto'] = pd.DataFrame(columns=['idPresentacion','nombrePresentacion','idLinea','codigoPresentacion'])

    # presentaciontipocontrol (relación presentacion <-> tipocontrol)
    try:
        tablas['presentaciontipocontrol'] = pd.read_sql("SELECT idRel, idPresentacion, idTipoControl FROM presentaciontipocontrol;", conn)
    except Exception:
        tablas['presentaciontipocontrol'] = pd.DataFrame(columns=['idRel','idPresentacion','idTipoControl'])

    # parametrocalidad
    try:
        tablas['parametrocalidad'] = pd.read_sql("SELECT idParametro, nombreParametro, unidadMedida, limiteInferior, limiteSuperior, idTipoControl, tipoParametro, idPresentacion FROM parametrocalidad;", conn)
    except Exception:
        tablas['parametrocalidad'] = pd.DataFrame(columns=['idParametro','nombreParametro','unidadMedida','limiteInferior','limiteSuperior','idTipoControl','tipoParametro','idPresentacion'])

    # tipocontrol
    try:
        tablas['tipocontrol'] = pd.read_sql("SELECT idTipoControl, nombreTipo, idLinea FROM tipocontrol;", conn)
    except Exception:
        tablas['tipocontrol'] = pd.DataFrame(columns=['idTipoControl','nombreTipo','idLinea'])

    # lineaproduccion
    try:
        tablas['lineaproduccion'] = pd.read_sql("SELECT idLinea, nombreLinea FROM lineaproduccion;", conn)
    except Exception:
        tablas['lineaproduccion'] = pd.DataFrame(columns=['idLinea','nombreLinea'])

    # alertas (opcional, si existe)
    try:
        tablas['alerta'] = pd.read_sql("SELECT * FROM alerta;", conn, parse_dates=['fechaAlerta'])
    except Exception:
        tablas['alerta'] = pd.DataFrame()

    conn.close()
    return tablas


# Utilidades
def safe_str(v):
    return "" if pd.isna(v) else str(v)


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Devuelve un Excel bytes para descargar (usa openpyxl si está instalado)."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


# Dashboard principal 
def dashboard_powerbi_module():
    st.set_page_config(page_title="Dashboard (PowerBI-like)", layout="wide")
    st.title("Dashboard — Visualización dinámica desde la base de datos")

    tablas = cargar_tablas_dashboard()
    df_ctrl = tablas['controles']
    pres_prod = tablas['presentacionproducto']
    rel_pres_tipo = tablas['presentaciontipocontrol']
    params = tablas['parametrocalidad']
    tipos = tablas['tipocontrol']
    lineas = tablas['lineaproduccion']
    df_alertas = tablas.get('alerta', pd.DataFrame())

    # Sidebar: filtros en cascada
    with st.sidebar:
        st.header("Filtros (cascada)")

        # Línea
        if not lineas.empty:
            opciones_linea = {row.idLinea: row.nombreLinea for row in lineas.itertuples()}
        else:
            # fallback desde controles
            tmp = df_ctrl[['idLinea','nombreLinea']].drop_duplicates().dropna() if not df_ctrl.empty else pd.DataFrame()
            opciones_linea = {int(r.idLinea): r.nombreLinea for r in tmp.itertuples()} if not tmp.empty else {}

        linea_keys = [None] + list(opciones_linea.keys())
        linea_sel = st.selectbox("Línea", options=linea_keys, format_func=lambda x: "Todas" if x is None else opciones_linea.get(x, str(x)))

        # Presentación filtrada por línea (desde presentacionproducto)
        if linea_sel is not None and not pres_prod.empty:
            pres_df = pres_prod[pres_prod['idLinea'] == int(linea_sel)]
        else:
            pres_df = pres_prod.copy() if not pres_prod.empty else pd.DataFrame()

        # fallback: si no hay presentaciones con esa linea, tomar presentaciones presentes en controles/parametros
        if pres_df.empty:
            ids1 = df_ctrl[['idPresentacion']].drop_duplicates().dropna() if not df_ctrl.empty else pd.DataFrame()
            ids2 = params[['idPresentacion']].drop_duplicates().dropna() if not params.empty else pd.DataFrame()
            pres_ids = pd.concat([ids1, ids2]).drop_duplicates() if not ids1.empty or not ids2.empty else pd.DataFrame()
            pres_df = pd.DataFrame({'idPresentacion': pres_ids['idPresentacion'].astype('Int64')}) if not pres_ids.empty else pd.DataFrame()

        pres_opts = pres_df['idPresentacion'].dropna().astype(int).unique().tolist() if not pres_df.empty else []
        pres_map = dict(zip(pres_prod['idPresentacion'].astype(int).tolist(), pres_prod['nombrePresentacion'].tolist())) if not pres_prod.empty else {}
        pres_keys = [None] + pres_opts
        pres_sel = st.selectbox("Presentación", options=pres_keys, format_func=lambda x: "Todas" if x is None else pres_map.get(int(x), str(x)))

        # Tipo de control filtrado por presentación o por línea
        tipo_opts = []
        if pres_sel is not None and not rel_pres_tipo.empty:
            tipo_opts = rel_pres_tipo[rel_pres_tipo['idPresentacion'] == int(pres_sel)]['idTipoControl'].drop_duplicates().astype(int).tolist()
        elif pres_sel is not None:
            # fallback: tipos en controles o parametros para esa presentacion
            t1 = df_ctrl[df_ctrl['idPresentacion'] == int(pres_sel)]['idTipoControl'].dropna().astype(int).unique().tolist() if not df_ctrl.empty else []
            t2 = params[params['idPresentacion'] == int(pres_sel)]['idTipoControl'].dropna().astype(int).unique().tolist() if not params.empty else []
            tipo_opts = sorted(set(t1 + t2))
        else:
            # si no presentacion, preferir tipos por linea
            if linea_sel is not None and not tipos.empty:
                tipo_opts = tipos[tipos['idLinea'] == int(linea_sel)]['idTipoControl'].drop_duplicates().astype(int).tolist()
                if not tipo_opts:
                    tipo_opts = tipos['idTipoControl'].drop_duplicates().astype(int).tolist()
            else:
                tipo_opts = tipos['idTipoControl'].drop_duplicates().astype(int).tolist() if not tipos.empty else df_ctrl['idTipoControl'].drop_duplicates().dropna().astype(int).tolist()

        tipo_map = dict(zip(tipos['idTipoControl'].tolist(), tipos['nombreTipo'].tolist())) if not tipos.empty else {}
        tipo_keys = [None] + (tipo_opts if tipo_opts else [])
        tipo_sel = st.selectbox("Tipo de control", options=tipo_keys, format_func=lambda x: "Todos" if x is None else tipo_map.get(int(x), str(x)))

        # Parámetros filtrados por (presentación OR tipo) preferentemente
        param_candidates = pd.DataFrame()
        if not params.empty:
            tmp = params.copy()
            if pres_sel is not None:
                tmp_pres = tmp[tmp['idPresentacion'] == int(pres_sel)]
            else:
                tmp_pres = pd.DataFrame()
            if tipo_sel is not None:
                tmp_tipo = tmp[tmp['idTipoControl'] == int(tipo_sel)]
            else:
                tmp_tipo = pd.DataFrame()

            # preferir la intersección, si está vacía usar la unión
            inter = pd.merge(tmp_pres, tmp_tipo, how='inner', on=list(tmp.columns)) if (not tmp_pres.empty and not tmp_tipo.empty) else pd.DataFrame()
            if not inter.empty:
                param_candidates = inter
            else:
                union = pd.concat([tmp_pres, tmp_tipo]).drop_duplicates() if (not tmp_pres.empty or not tmp_tipo.empty) else tmp
                param_candidates = union
        else:
            # fallback desde controles
            param_candidates = df_ctrl[['idParametro','nombreParametro']].drop_duplicates()

        # ultimo fallback: todos los parametros conocidos
        if param_candidates.empty and not params.empty:
            param_candidates = params[['idParametro','nombreParametro']].drop_duplicates()

        param_map = {int(r.idParametro): r.nombreParametro for r in param_candidates.itertuples()} if not param_candidates.empty else {}
        param_keys = list(param_map.keys())
        param_sel = st.multiselect("Parámetro(s)", options=param_keys, format_func=lambda x: param_map.get(x, str(x)), default=(param_keys[:3] if len(param_keys)>0 else []))

        # Rango de fechas
        if not df_ctrl.empty and 'fechaControl' in df_ctrl.columns:
            min_date = df_ctrl['fechaControl'].min().date()
            max_date = df_ctrl['fechaControl'].max().date()
        else:
            today = datetime.today().date()
            min_date = today - timedelta(days=30)
            max_date = today
        date_range = st.date_input("Rango de fechas", value=(min_date, max_date), min_value=min_date, max_value=max_date)

        # Opciones adicionales
        st.markdown("---")
        st.write("Opciones:")
        mostrar_tabla = st.checkbox("Mostrar tabla de datos filtrada", value=False)
        agregar_alertas = st.checkbox("Incluir métricas de alertas (si existen)", value=True)
        boton_reset = st.button("Resetear filtros")

        if boton_reset:
            # simple workaround: recargar la página para limpiar widget states
            st.experimental_rerun()

    # Aplicar filtros sobre df_ctrl
    df_f = df_ctrl.copy()

    # fecha
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start = pd.to_datetime(date_range[0])
        end = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df_f = df_f[(df_f['fechaControl'] >= start) & (df_f['fechaControl'] <= end)]

    if linea_sel is not None:
        df_f = df_f[df_f['idLinea'] == int(linea_sel)]
    if pres_sel is not None:
        df_f = df_f[df_f['idPresentacion'] == int(pres_sel)]
    if tipo_sel is not None:
        df_f = df_f[df_f['idTipoControl'] == int(tipo_sel)]
    if param_sel:
        df_f = df_f[df_f['idParametro'].isin(param_sel)]

    # KPIs (fila superior) - 5 tarjetas
    total_mediciones = len(df_f)
    mean_val = float(df_f['resultado'].mean()) if (not df_f.empty and 'resultado' in df_f.columns) else np.nan
    median_val = float(df_f['resultado'].median()) if (not df_f.empty and 'resultado' in df_f.columns) else np.nan
    out_of_spec = 0
    if not df_f.empty and 'limiteInferior' in df_f.columns and 'limiteSuperior' in df_f.columns:
        out_of_spec = int(((df_f['resultado'] < df_f['limiteInferior']) | (df_f['resultado'] > df_f['limiteSuperior'])).sum())
    alert_count = len(df_alertas) if agregar_alertas and not df_alertas.empty else 0

    # Display KPIs in cards 
    k1, k2, k3, k4, k5 = st.columns([1.2,1.2,1.2,1.2,1.2])
    k1.metric(label="Total mediciones", value=f"{total_mediciones:,}")
    k2.metric(label="Media (resultado)", value=f"{mean_val:.2f}" if not np.isnan(mean_val) else "—")
    k3.metric(label="Mediana", value=f"{median_val:.2f}" if not np.isnan(median_val) else "—")
    k4.metric(label="Fuera especificación", value=f"{out_of_spec}")
    k5.metric(label="Alertas registradas", value=f"{alert_count}")

    st.markdown("---")

    # Gráficas (fila principal) - 3 columnas
    col1, col2, col3 = st.columns([1.1,1.1,1.0])

    # 1) Serie temporal: resultados en el tiempo (por parámetro si hay varios)
    with col1:
        st.subheader("Tendencia: Resultados en el tiempo")
        if df_f.empty:
            st.info("No hay datos para graficar.")
        else:
            # si hay varios parametros, permitir elegir uno para la serie
            unique_params = df_f['idParametro'].dropna().unique().tolist()
            if len(unique_params) > 1:
                choice_param = st.selectbox("Parámetro para serie", options=[None] + unique_params, format_func=lambda x: "Todos" if x is None else param_map.get(int(x), str(x)))
            else:
                choice_param = unique_params[0] if unique_params else None

            df_time = df_f.copy()
            if choice_param is not None:
                df_time = df_time[df_time['idParametro'] == int(choice_param)]

            df_time = df_time.sort_values('fechaControl')
            if df_time.empty:
                st.info("No hay datos para la selección.")
            else:
                fig_ts = px.line(df_time, x='fechaControl', y='resultado', markers=True, title="Serie temporal de resultados")
                # marcar puntos fuera de especificación si hay limites
                if 'limiteInferior' in df_time.columns and 'limiteSuperior' in df_time.columns:
                    li = df_time['limiteInferior'].iloc[0] if not pd.isna(df_time['limiteInferior'].iloc[0]) else None
                    ls = df_time['limiteSuperior'].iloc[0] if not pd.isna(df_time['limiteSuperior'].iloc[0]) else None
                    if li is not None:
                        fig_ts.add_hline(y=li, line_dash="dot", line_color="green", annotation_text=f"Spec LI={li}")
                    if ls is not None:
                        fig_ts.add_hline(y=ls, line_dash="dot", line_color="green", annotation_text=f"Spec LS={ls}")
                st.plotly_chart(fig_ts, use_container_width=True)
                # download PNG
                try:
                    png = fig_ts.to_image(format="png")
                    st.download_button("Descargar Serie (PNG)", data=png, file_name="serie_temporal.png", mime="image/png")
                except Exception:
                    st.caption("Instala 'kaleido' para descargar PNG (pip install -U kaleido).")

    # 2) Barra: promedio / conteo por presentación o tipo
    with col2:
        st.subheader("Bar: Promedio por Presentación / Tipo")
        if df_f.empty:
            st.info("No hay datos para graficar.")
        else:
            group_by = st.radio("Agrupar por", options=["Presentación","Tipo de control","Parámetro"], horizontal=True, index=0)
            if group_by == "Presentación":
                if 'nombrePresentacion' in df_f.columns:
                    agg = df_f.groupby('nombrePresentacion')['resultado'].agg(['mean','count']).reset_index().sort_values('mean', ascending=False)
                    fig_bar = px.bar(agg, x='mean', y='nombrePresentacion', orientation='h', labels={'mean':'Promedio'}, title="Promedio por Presentación")
                else:
                    st.info("No hay nombres de presentación en los datos.")
                    fig_bar = None
            elif group_by == "Tipo de control":
                if 'nombreTipoControl' in df_f.columns:
                    agg = df_f.groupby('nombreTipoControl')['resultado'].agg(['mean','count']).reset_index().sort_values('mean', ascending=False)
                    fig_bar = px.bar(agg, x='mean', y='nombreTipoControl', orientation='h', labels={'mean':'Promedio'}, title="Promedio por Tipo de control")
                else:
                    st.info("No hay tipos en los datos.")
                    fig_bar = None
            else:
                agg = df_f.groupby('nombreParametro')['resultado'].agg(['mean','count']).reset_index().sort_values('mean', ascending=False)
                fig_bar = px.bar(agg, x='mean', y='nombreParametro', orientation='h', labels={'mean':'Promedio'}, title="Promedio por Parámetro")

            if fig_bar is not None:
                st.plotly_chart(fig_bar, use_container_width=True)
                try:
                    pngb = fig_bar.to_image(format="png")
                    st.download_button("Descargar Barra (PNG)", data=pngb, file_name="barra_promedios.png", mime="image/png")
                except Exception:
                    st.caption("Instala 'kaleido' para descargar PNG (pip install -U kaleido).")

    # 3) Pie / Donut: distribución de alertas o proporción por presentación
    with col3:
        st.subheader("Distribución (Donut)")
        choice_dist = st.selectbox("Mostrar", options=["Alertas por tipo" if not df_alertas.empty else None, "Mediciones por presentación"], format_func=lambda x: x or "No disponible")
        if choice_dist is None:
            st.info("No hay datos de alertas ni presentaciones para mostrar.")
        else:
            if choice_dist == "Alertas por tipo":
                df_a = df_alertas.copy()
                if not df_a.empty and 'tipoAlerta' in df_a.columns:
                    counts = df_a['tipoAlerta'].value_counts().reset_index()
                    counts.columns = ['tipo','count']
                    fig_p = px.pie(counts, names='tipo', values='count', hole=0.45, title="Alertas por tipo")
                    st.plotly_chart(fig_p, use_container_width=True)
                else:
                    st.info("No hay tipos de alerta.")
            else:
                if not df_f.empty and 'nombrePresentacion' in df_f.columns:
                    counts = df_f['nombrePresentacion'].value_counts().reset_index()
                    counts.columns = ['presentacion','count']
                    fig_p = px.pie(counts, names='presentacion', values='count', hole=0.45, title="Mediciones por Presentación")
                    st.plotly_chart(fig_p, use_container_width=True)
                else:
                    st.info("No hay datos de presentaciones en la selección.")

    st.markdown("---")

    # Tabla detallada y descarga
    if mostrar_tabla:
        st.subheader("Tabla: Datos filtrados")
        st.dataframe(df_f.sort_values('fechaControl').reset_index(drop=True))

        # Descargar CSV / Excel
        csv = df_f.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar CSV", data=csv, file_name="dashboard_datos_filtrados.csv", mime="text/csv")

        # Excel (revisar openpyxl)
        try:
            excel_bytes = to_excel_bytes(df_f.sort_values('fechaControl').reset_index(drop=True))
            st.download_button("Descargar Excel", data=excel_bytes, file_name="dashboard_datos_filtrados.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception:
            st.info("Para descargar Excel instala 'openpyxl' (pip install openpyxl).")

    st.caption("Dashboard generado dinámicamente desde la base de datos. Diseñado para ser similar a un panel PowerBI, pero 100% Streamlit + Plotly.")

# Ejecutable principal
if __name__ == "__main__":
    dashboard_powerbi_module()
