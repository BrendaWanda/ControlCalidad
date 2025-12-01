import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database.db_connection import get_connection
import plotly.graph_objects as go
from io import BytesIO

# I-MR constants for n=2 
D2_N2 = 1.128
D4_N2 = 3.267
D3_N2 = 0.0

# Data loading
@st.cache_data(ttl=300)
def cargar_tablas():
    conn = get_connection()
    tablas = {}
    # controles (join parcial para nombres)
    q_ctrl = """
    SELECT
        cc.idControl, cc.fechaControl, cc.idOrdenTrabajo, cc.resultado, cc.observaciones,
        cc.idUsuario, cc.idParametro, cc.idPresentacion, cc.idTipoControl, cc.idLinea,
        cc.idDetalle, cc.sabor,
        p.nombreParametro, p.unidadMedida, p.limiteInferior, p.limiteSuperior,
        tp.nombreTipo AS nombreTipoControl,
        l.nombreLinea,
        d.lote
    FROM controlcalidad cc
    LEFT JOIN parametrocalidad p ON cc.idParametro = p.idParametro
    LEFT JOIN tipocontrol tp ON cc.idTipoControl = tp.idTipoControl
    LEFT JOIN lineaproduccion l ON cc.idLinea = l.idLinea
    LEFT JOIN detalleordentrabajo d ON cc.idDetalle = d.idDetalle
    ;
    """
    try:
        tablas['controles'] = pd.read_sql(q_ctrl, conn, parse_dates=['fechaControl'])
    except Exception:
        tablas['controles'] = pd.DataFrame(columns=[
            'idControl','fechaControl','idOrdenTrabajo','resultado','observaciones','idUsuario',
            'idParametro','idPresentacion','idTipoControl','idLinea','idDetalle','sabor',
            'nombreParametro','unidadMedida','limiteInferior','limiteSuperior','nombreTipoControl','nombreLinea','lote'
        ])

    # presentacionproducto
    try:
        tablas['presentacionproducto'] = pd.read_sql("SELECT idPresentacion, nombrePresentacion, idLinea, codigoPresentacion FROM presentacionproducto;", conn)
    except Exception:
        tablas['presentacionproducto'] = pd.DataFrame(columns=['idPresentacion','nombrePresentacion','idLinea','codigoPresentacion'])

    # presentaciontipocontrol
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

    # detalleordentrabajo (lotes)
    try:
        tablas['detalleordentrabajo'] = pd.read_sql("SELECT idDetalle, idPresentacion, lote FROM detalleordentrabajo;", conn)
    except Exception:
        tablas['detalleordentrabajo'] = pd.DataFrame(columns=['idDetalle','idPresentacion','lote'])

    conn.close()
    return tablas

# Helper statistics
def calcular_limits_I_MR(series):
    x = np.array(series.dropna(), dtype=float)
    if x.size == 0:
        return None
    I_mean = np.mean(x)
    MR = np.abs(np.diff(x))
    MRbar = MR.mean() if MR.size > 0 else 0.0
    sigma = MRbar / D2_N2 if D2_N2 else 0.0
    UCL_I = I_mean + 3 * sigma
    LCL_I = I_mean - 3 * sigma
    UCL_MR = D4_N2 * MRbar
    LCL_MR = max(0.0, D3_N2 * MRbar)
    return {'I_mean': I_mean, 'sigma': sigma, 'UCL_I': UCL_I, 'LCL_I': LCL_I,
            'MR': MR, 'MRbar': MRbar, 'UCL_MR': UCL_MR, 'LCL_MR': LCL_MR}

def detectar_fuera_de_control(x_series, stats):
    if stats is None:
        return np.array([False]*len(x_series)), []
    x = np.array(x_series, dtype=float)
    mask = (x > stats['UCL_I']) | (x < stats['LCL_I'])
    idx = list(np.where(mask)[0])
    return mask, idx

# Plot
def plot_I_MR(df_subset, titulo, limite_inf=None, limite_sup=None):
    if df_subset.empty:
        return None, None, [], None, []
    df_subset = df_subset.sort_values('fechaControl').reset_index(drop=True)
    x_vals = df_subset['fechaControl']
    y_vals = df_subset['resultado'].astype(float)

    stats = calcular_limits_I_MR(y_vals)
    if stats is None:
        return None, None, [], None, []

    ooc_mask, ooc_indices = detectar_fuera_de_control(y_vals, stats)

    # spec detection
    spec_mask = np.zeros(len(y_vals), dtype=bool)
    spec_indices = []
    if (limite_inf is not None) or (limite_sup is not None):
        li = -np.inf if limite_inf is None else float(limite_inf)
        ls = np.inf if limite_sup is None else float(limite_sup)
        spec_mask = (y_vals < li) | (y_vals > ls)
        spec_indices = list(np.where(spec_mask)[0])

    # I chart
    fig_i = go.Figure()
    fig_i.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines+markers', name='Mediciones',
                                marker=dict(size=8), hovertemplate='%{x}<br>Valor: %{y}'))
    if spec_mask.any():
        fig_i.add_trace(go.Scatter(x=x_vals[spec_mask], y=y_vals[spec_mask], mode='markers',
                                    marker=dict(color='crimson', size=11, symbol='diamond'),
                                    name='Fuera de especificación',
                                    hovertemplate='%{x}<br>Valor: %{y} (Fuera de especificación)'))
    if any(ooc_mask):
        fig_i.add_trace(go.Scatter(x=x_vals[ooc_mask], y=y_vals[ooc_mask], mode='markers',
                                    marker=dict(color='red', size=12, symbol='x'),
                                    name='Fuera de control (I-MR)',
                                    hovertemplate='%{x}<br>Valor: %{y} (Fuera de control)'))

    # control lines
    fig_i.add_hline(y=stats['I_mean'], line=dict(dash='dash'),
                    annotation_text=f"Ī = {stats['I_mean']:.3f}", annotation_position="top left")
    fig_i.add_hline(y=stats['UCL_I'], line=dict(color='red'),
                    annotation_text=f"UCL = {stats['UCL_I']:.3f}", annotation_position="top right")
    fig_i.add_hline(y=stats['LCL_I'], line=dict(color='red'),
                    annotation_text=f"LCL = {stats['LCL_I']:.3f}", annotation_position="bottom right")

    # spec lines
    if limite_inf is not None:
        fig_i.add_hline(y=float(limite_inf), line=dict(color='green', dash='dot'),
                        annotation_text=f"Spec Límite inferior = {float(limite_inf):.3f}", annotation_position="bottom left")
    if limite_sup is not None:
        fig_i.add_hline(y=float(limite_sup), line=dict(color='green', dash='dot'),
                        annotation_text=f"Spec Límite superior = {float(limite_sup):.3f}", annotation_position="top left")

    fig_i.update_layout(title=f"I Chart — {titulo}", xaxis_title="Fecha", yaxis_title="Valor",
                        height=420, margin=dict(l=50, r=20, t=70, b=60))

    # MR chart
    MR = stats['MR']
    if getattr(MR, "size", 0) == 0:
        fig_mr = go.Figure()
        fig_mr.add_annotation(text="No hay suficientes pares consecutivos para MR.",
                                showarrow=False)
    else:
        x_mr = x_vals.iloc[1:].reset_index(drop=True)
        fig_mr = go.Figure()
        fig_mr.add_trace(go.Bar(x=x_mr, y=MR, name='MR'))
        fig_mr.add_hline(y=stats['MRbar'], line=dict(dash='dash'),
                            annotation_text=f"MR̄ = {stats['MRbar']:.3f}", annotation_position="top left")
        fig_mr.add_hline(y=stats['UCL_MR'], line=dict(color='red'),
                            annotation_text=f"UCL_MR = {stats['UCL_MR']:.3f}", annotation_position="top right")
        fig_mr.add_hline(y=stats['LCL_MR'], line=dict(color='red'),
                            annotation_text=f"LCL_MR = {stats['LCL_MR']:.3f}", annotation_position="bottom right")
        fig_mr.update_layout(title=f"MR Chart — {titulo}", xaxis_title="Fecha", yaxis_title="MR",
                                height=300, margin=dict(l=50, r=20, t=50, b=50))

    return fig_i, fig_mr, ooc_indices, stats, spec_indices

# Streamlit app
def app_graficos_control():
    st.set_page_config(page_title="Gráficos de Control", layout="wide")
    st.title("Gráficos de Control — I-MR (Línea → Presentación → Tipo → Parámetro)")

    tablas = cargar_tablas()
    df = tablas['controles']
    pres_prod = tablas['presentacionproducto']
    rel_pres_tipo = tablas['presentaciontipocontrol']
    parametros_all = tablas['parametrocalidad']
    tipocontrol_all = tablas['tipocontrol']
    detalle_ot = tablas['detalleordentrabajo']
    lineas_all = tablas['lineaproduccion']

    if df.empty and parametros_all.empty and pres_prod.empty:
        st.warning("No hay datos ni definiciones en la base de datos.")
        return

    # Sidebar - cascade filters
    with st.sidebar:
        st.header("Filtros")

        # 1) Línea
        line_map = {}
        if not lineas_all.empty:
            line_map = dict(zip(lineas_all['idLinea'].tolist(), lineas_all['nombreLinea'].tolist()))
        else:
            # fallback from controls
            if not df.empty:
                tmp = df[['idLinea','nombreLinea']].drop_duplicates().dropna()
                line_map = dict(zip(tmp['idLinea'].tolist(), tmp['nombreLinea'].tolist()))
        linea_sel = st.selectbox("1) Línea de producción", options=[None] + list(line_map.keys()),
                                    format_func=lambda x: "Todas" if x is None else line_map.get(x, str(x)),
                                    key="f_linea")

        # 2) Presentación (filtrada por línea si hay datos)
        if linea_sel is not None and not pres_prod.empty:
            pres_df = pres_prod[pres_prod['idLinea'] == int(linea_sel)].copy()
        else:
            pres_df = pres_prod.copy() if not pres_prod.empty else pd.DataFrame()

        # fallback to presentaciones found in controls or parametros
        if pres_df.empty:
            ids_ctrl = df[['idPresentacion']].drop_duplicates().dropna()['idPresentacion'] if not df.empty else pd.Series(dtype='int')
            ids_param = parametros_all[['idPresentacion']].drop_duplicates().dropna()['idPresentacion'] if not parametros_all.empty else pd.Series(dtype='int')
            pres_ids = pd.concat([ids_ctrl, ids_param]).drop_duplicates()
            pres_df = pd.DataFrame({'idPresentacion': pres_ids.astype('Int64')})

        present_options = pres_df['idPresentacion'].dropna().astype(int).unique().tolist()
        present_map = {}
        if not pres_prod.empty:
            present_map = dict(zip(pres_prod['idPresentacion'].astype(int).tolist(), pres_prod['nombrePresentacion'].tolist()))
        present_sel = st.selectbox("2) Presentación", options=[None] + present_options,
                                    format_func=lambda x: "Todas" if x is None else present_map.get(int(x), str(x)),
                                    key="f_present")

        # 3) Tipo de control (filtrado por presentación o línea)
        tipo_ids = []
        if present_sel is not None and not rel_pres_tipo.empty:
            tipo_ids = rel_pres_tipo[rel_pres_tipo['idPresentacion'] == int(present_sel)]['idTipoControl'].drop_duplicates().astype(int).tolist()
        elif present_sel is not None:
            # fallback: tipos presentes en controles o en parametrocalidad para esa presentacion
            t1 = df[df['idPresentacion'] == int(present_sel)]['idTipoControl'].dropna().astype(int).unique().tolist() if not df.empty else []
            t2 = parametros_all[parametros_all['idPresentacion'] == int(present_sel)]['idTipoControl'].dropna().astype(int).unique().tolist() if not parametros_all.empty else []
            tipo_ids = sorted(set(t1 + t2))
        else:
            # no present selected: preferir tipos de la línea
            if linea_sel is not None and not tipocontrol_all.empty:
                tipo_ids = tipocontrol_all[tipocontrol_all['idLinea'] == int(linea_sel)]['idTipoControl'].drop_duplicates().astype(int).tolist()
                if not tipo_ids:
                    tipo_ids = tipocontrol_all['idTipoControl'].drop_duplicates().astype(int).tolist()
            else:
                tipo_ids = tipocontrol_all['idTipoControl'].drop_duplicates().astype(int).tolist() if not tipocontrol_all.empty else df['idTipoControl'].drop_duplicates().dropna().astype(int).tolist()

        tipo_map = {}
        if not tipocontrol_all.empty:
            tipo_map = dict(zip(tipocontrol_all['idTipoControl'].tolist(), tipocontrol_all['nombreTipo'].tolist()))
        tipo_sel = st.selectbox("3) Tipo de control", options=[None] + tipo_ids,
                                format_func=lambda x: "Todos" if x is None else tipo_map.get(int(x), str(x)),
                                key="f_tipo")

        # 4) Parámetros filtrados: lógica flexible (OR) para evitar selects vacíos
        # Primero intentar filtrar por (presentación OR tipo), si queda vacío dar fallback
        param_candidates = pd.DataFrame()
        if not parametros_all.empty:
            tmp = parametros_all.copy()
            # apply filters if selected
            mask = pd.Series(True, index=tmp.index)
            if present_sel is not None:
                mask_pres = tmp['idPresentacion'] == int(present_sel)
            else:
                mask_pres = pd.Series(False, index=tmp.index)
            if tipo_sel is not None:
                mask_tipo = tmp['idTipoControl'] == int(tipo_sel)
            else:
                mask_tipo = pd.Series(False, index=tmp.index)

            # If both filters present -> accept rows that match either (OR)
            if present_sel is not None or tipo_sel is not None:
                mask_or = mask_pres | mask_tipo
                tmp = tmp[mask_or]
            # if no filters, tmp = all
            param_candidates = tmp[['idParametro','nombreParametro']].drop_duplicates()
        else:
            # fallback from controls
            param_candidates = df[['idParametro','nombreParametro']].drop_duplicates()

        # If still empty, widen the search: parameters for the same line, or from controls for same present/tipo
        if param_candidates.empty:
            # from controles
            tmpc = df.copy()
            if present_sel is not None:
                tmpc = tmpc[tmpc['idPresentacion'] == int(present_sel)]
            if tipo_sel is not None:
                tmpc = tmpc[tmpc['idTipoControl'] == int(tipo_sel)]
            param_candidates = tmpc[['idParametro','nombreParametro']].drop_duplicates()
        # final fallback: all parametros
        if param_candidates.empty and not parametros_all.empty:
            param_candidates = parametros_all[['idParametro','nombreParametro']].drop_duplicates()

        param_map = {int(r.idParametro): r.nombreParametro for r in param_candidates.itertuples()} if not param_candidates.empty else {}
        param_defaults = list(param_map.keys())[:3] if len(param_map) > 0 else []
        param_sel = st.multiselect("4) Parámetro(s)", options=list(param_map.keys()),
                                    format_func=lambda x: param_map.get(x, str(x)),
                                    default=param_defaults,
                                    key="f_param")

        # 5) Lote (filtrado)
        lote_options = []
        if not detalle_ot.empty:
            lotes = detalle_ot.copy()
            if present_sel is not None:
                lotes = lotes[lotes['idPresentacion'] == int(present_sel)]
            lote_options = lotes['lote'].dropna().unique().tolist()
        if not lote_options:
            lote_options = df['lote'].dropna().unique().tolist() if not df.empty else []
        lote_sel = st.selectbox("Lote", options=[None] + lote_options, format_func=lambda x: "Todos" if x is None else str(x), key="f_lote")

        # fecha
        if not df.empty:
            min_date = df['fechaControl'].min().date()
            max_date = df['fechaControl'].max().date()
        else:
            today = datetime.today().date()
            min_date = today - timedelta(days=30)
            max_date = today
        date_range = st.date_input("Rango de fechas", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="f_dates")

        st.markdown("---")
        st.write("Opciones:")
        agrupar = st.checkbox("Generar gráfico por presentación+línea automáticamente", value=True, key="f_agrupar")
        mostrar_todo = st.checkbox("Mostrar tabla de datos filtrada", value=False, key="f_mostrar")
        download_csv = st.checkbox("Añadir botón para descargar CSV", value=True, key="f_csv")

    # Aplicar filtros a df
    df_f = df.copy()

    # fecha
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start = pd.to_datetime(date_range[0])
        end = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df_f = df_f[(df_f['fechaControl'] >= start) & (df_f['fechaControl'] <= end)]

    if linea_sel is not None:
        df_f = df_f[df_f['idLinea'] == int(linea_sel)]
    if present_sel is not None:
        df_f = df_f[df_f['idPresentacion'] == int(present_sel)]
    if tipo_sel is not None:
        df_f = df_f[df_f['idTipoControl'] == int(tipo_sel)]
    if lote_sel is not None:
        df_f = df_f[df_f['lote'] == lote_sel]
    if param_sel:
        df_f = df_f[df_f['idParametro'].isin(param_sel)]
    else:
        st.warning("Selecciona al menos un parámetro para graficar.")
        return

    if mostrar_todo:
        st.markdown("#### Datos filtrados")
        st.dataframe(df_f.sort_values('fechaControl').reset_index(drop=True))

    if download_csv:
        csv = df_f.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar CSV (datos filtrados)", data=csv, file_name="controles_filtrados.csv", mime="text/csv", key="dl_csv_filtrados")

    # combos para graficar
    combos = []
    if agrupar:
        combos = df_f[['idParametro','idPresentacion','idLinea','nombreParametro','nombreLinea']].drop_duplicates().to_dict('records')
    else:
        combos = [{'idParametro': pid, 'idPresentacion': present_sel, 'idLinea': linea_sel,
                    'nombreParametro': (param_map.get(pid, f"Param {pid}")),
                    'nombreLinea': (line_map.get(linea_sel, '') if line_map else '')} for pid in (param_sel or [])]

    MAX_COMBOS = 50
    if len(combos) > MAX_COMBOS:
        st.warning(f"Se detectaron {len(combos)} combinaciones; solo se mostrarán las primeras {MAX_COMBOS}.")
        combos = combos[:MAX_COMBOS]

    # Render de cada combo
    for idx, combo in enumerate(combos):
        pid = combo.get('idParametro')
        pres = combo.get('idPresentacion')
        lid = combo.get('idLinea')

        sel_df = df_f[df_f['idParametro'] == pid]
        if pres is not None:
            sel_df = sel_df[sel_df['idPresentacion'] == pres]
        if lid is not None:
            sel_df = sel_df[sel_df['idLinea'] == lid]
        if sel_df.empty:
            continue

        # obtener limites desde parametrocalidad si existen
        limite_inf = None
        limite_sup = None
        if not parametros_all.empty and pid in parametros_all['idParametro'].values:
            row = parametros_all[parametros_all['idParametro'] == pid].iloc[0]
            limite_inf = row['limiteInferior'] if not pd.isna(row.get('limiteInferior')) else None
            limite_sup = row['limiteSuperior'] if not pd.isna(row.get('limiteSuperior')) else None

        # titulo
        param_name = sel_df['nombreParametro'].iloc[0] if 'nombreParametro' in sel_df.columns else (param_map.get(pid, f"Parametro {pid}"))
        linea_name = sel_df['nombreLinea'].iloc[0] if 'nombreLinea' in sel_df.columns else line_map.get(lid, f"Línea {lid}" if lid else "Todas")
        pres_name = None
        if not pres_prod.empty and pres in pres_prod['idPresentacion'].values:
            pres_name = pres_prod[pres_prod['idPresentacion'] == pres]['nombrePresentacion'].iloc[0]
        else:
            pres_name = str(pres) if pres else "Todas presentaciones"
        titulo = f"{param_name} — {linea_name} — {pres_name}"

        st.markdown(f"### {titulo}")
        st.write(f"Registros: {len(sel_df)} · Lotes: {', '.join(map(str, sel_df['lote'].dropna().unique()[:6]))}{'...' if len(sel_df['lote'].dropna().unique())>6 else ''}")

        fig_i, fig_mr, ooc_indices, stats, spec_indices = plot_I_MR(sel_df[['fechaControl','resultado']].copy(), titulo, limite_inf, limite_sup)

        # unique key
        def safe(v): return str(v).replace(" ", "_").replace("/", "_").replace(":", "_")
        unique_base = f"{safe(pid)}_{safe(pres)}_{safe(lid)}_{idx}"

        if fig_i is not None:
            st.plotly_chart(fig_i, use_container_width=True, key=f"fig_i_{unique_base}")
            # download png
            try:
                png_i = fig_i.to_image(format="png")
                st.download_button(label="Descargar I-Chart (PNG)", data=png_i, file_name=f"IChart_{unique_base}.png", mime="image/png", key=f"dl_i_{unique_base}")
            except Exception:
                st.info("Para descargar PNG instala 'kaleido' (pip install -U kaleido).")

        if fig_mr is not None:
            st.plotly_chart(fig_mr, use_container_width=True, key=f"fig_mr_{unique_base}")
            try:
                png_mr = fig_mr.to_image(format="png")
                st.download_button(label="Descargar MR-Chart (PNG)", data=png_mr, file_name=f"MRChart_{unique_base}.png", mime="image/png", key=f"dl_mr_{unique_base}")
            except Exception:
                st.info("Para descargar PNG instala 'kaleido' (pip install -U kaleido).")

        # descargar excel
        try:
            out = BytesIO()
            sel_df.sort_values('fechaControl').reset_index(drop=True).to_excel(out, index=False)
            st.download_button(label="Descargar Datos (Excel)", data=out.getvalue(), file_name=f"Datos_{unique_base}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_xlsx_{unique_base}")
        except Exception as e:
            st.info("Para descargar Excel instala 'openpyxl' (pip install openpyxl).")

        # detalles
        with st.expander("Detalles / Estadísticos"):
            if stats is None:
                st.info("No hay suficientes datos para calcular estadísticas.")
            else:
                st.write({
                    'Media (Ī)': stats['I_mean'],
                    'Sigma estimado (σ)': stats['sigma'],
                    'MR̄': stats['MRbar'],
                    'UCL I': stats['UCL_I'],
                    'LCL I': stats['LCL_I'],
                    'UCL MR': stats['UCL_MR'],
                    'LCL MR': stats['LCL_MR'],
                })
                if spec_indices:
                    st.error(f"Puntos fuera de ESPECIFICACIÓN: {len(spec_indices)}")
                    for i in spec_indices:
                        fila = sel_df.sort_values('fechaControl').reset_index(drop=True).loc[i]
                        st.write(f"- {fila['fechaControl']} → {fila['resultado']}")
                if ooc_indices:
                    st.error(f"Puntos fuera de CONTROL (I-MR): {len(ooc_indices)}")
                    for i in ooc_indices:
                        fila = sel_df.sort_values('fechaControl').reset_index(drop=True).loc[i]
                        st.write(f"- {fila['fechaControl']} → {fila['resultado']}")

    st.markdown("---")
    st.caption("Límites de especificación (verde punteado). Puntos fuera de especificación: diamantes rojos. Fuera de control (I-MR): cruz roja.")

if __name__ == "__main__":
    app_graficos_control()