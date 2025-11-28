# modules/graficos_control.py
"""
Módulo para generar gráficos de control (I-MR) automáticamente
por parámetro/presentación/línea usando tus tablas:
- controlcalidad
- parametrocalidad
- lineaproduccion
- detalleordentrabajo
- tipocontrol
- usuario
(Requiere get_connection() en database.db_connection)
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database.db_connection import get_connection
import plotly.graph_objects as go
import math

# ----------------------------------------------------------
# Constantes para gráficos I-MR (subgroup size = 1 -> MR of consecutive pairs)
# d2 for n=2 is 1.128, D4 for n=2 = 3.267, D3 for n=2 = 0
D2_N2 = 1.128
D4_N2 = 3.267
D3_N2 = 0.0
# ----------------------------------------------------------

@st.cache_data(ttl=300)
def obtener_controles_join():
    """
    Realiza un JOIN de las tablas relevantes y devuelve un DataFrame.
    Ajusta nombres de columnas si tu DB usa otros nombres.
    """
    conn = get_connection()
    query = """
    SELECT
        cc.idControl,
        cc.fechaControl,
        cc.idOrdenTrabajo,
        cc.resultado,
        cc.observaciones,
        cc.idUsuario,
        cc.idParametro,
        cc.idPresentacion,
        cc.idTipoControl,
        cc.idLinea,
        cc.idDetalle,
        cc.sabor,
        p.nombreParametro,
        p.unidadMedida,
        p.limiteInferior,
        p.limiteSuperior,
        tp.nombreTipo AS nombreTipoControl,
        l.nombreLinea,
        d.lote,
        d.idPresentacion AS detallePresentacion
    FROM controlcalidad cc
    LEFT JOIN parametrocalidad p ON cc.idParametro = p.idParametro
    LEFT JOIN tipocontrol tp ON cc.idTipoControl = tp.idTipoControl
    LEFT JOIN lineaproduccion l ON cc.idLinea = l.idLinea
    LEFT JOIN detalleordentrabajo d ON cc.idDetalle = d.idDetalle
    ;
    """
    df = pd.read_sql(query, conn)
    # ensure datetime
    if 'fechaControl' in df.columns:
        df['fechaControl'] = pd.to_datetime(df['fechaControl'])
    return df

def calcular_limits_I_MR(series):
    """
    Calcula estadísticos para I-MR:
    - I_mean, sigma (estimado por MRbar / d2)
    - UCL_I, LCL_I
    - MR series, MRbar, UCL_MR, LCL_MR
    """
    x = np.array(series.dropna(), dtype=float)
    if x.size == 0:
        return None

    I_mean = np.mean(x)

    # moving ranges (absolute difference between consecutive measurements)
    MR = np.abs(np.diff(x))
    MRbar = MR.mean() if MR.size > 0 else 0.0

    sigma = MRbar / D2_N2 if D2_N2 else 0.0

    UCL_I = I_mean + 3 * sigma
    LCL_I = I_mean - 3 * sigma

    UCL_MR = D4_N2 * MRbar
    LCL_MR = max(0.0, D3_N2 * MRbar)

    stats = {
        'I_mean': I_mean,
        'sigma': sigma,
        'UCL_I': UCL_I,
        'LCL_I': LCL_I,
        'MR': MR,
        'MRbar': MRbar,
        'UCL_MR': UCL_MR,
        'LCL_MR': LCL_MR
    }
    return stats

def detectar_fuera_de_control(x_series, stats):
    """
    Detecta puntos fuera de control según Regla1:
    punto > UCL_I o punto < LCL_I
    Devuelve indice booleano y lista de indices.
    """
    if stats is None:
        return np.array([False]*len(x_series)), []
    x = np.array(x_series, dtype=float)
    mask = (x > stats['UCL_I']) | (x < stats['LCL_I'])
    indices = list(np.where(mask)[0])
    return mask, indices

def plot_I_MR(df_subset, titulo):
    """
    Dibuja los gráficos I y MR con plotly.
    df_subset debe tener columnas: fechaControl, resultado
    """
    if df_subset.empty:
        st.info("No hay datos para esta combinación.")
        return

    # ordenar por fecha
    df_subset = df_subset.sort_values('fechaControl').reset_index(drop=True)
    x_vals = df_subset['fechaControl']
    y_vals = df_subset['resultado'].astype(float)

    stats = calcular_limits_I_MR(y_vals)
    if stats is None:
        st.info("No hay suficientes datos para calcular Rangos móviles.")
        return

    # detectar fuera de control
    ooc_mask, ooc_indices = detectar_fuera_de_control(y_vals, stats)

    # ----------------- FIGURA I (Individual) -----------------
    fig_i = go.Figure()
    fig_i.add_trace(go.Scatter(
        x=x_vals, y=y_vals, mode='markers+lines', name='Mediciones',
        marker=dict(size=8),
        hovertemplate='%{x}<br>Valor: %{y}'
    ))

    # mean
    fig_i.add_hline(y=stats['I_mean'], line=dict(dash='dash'), 
                    annotation_text=f"Media (Ī) = {stats['I_mean']:.3f}", 
                    annotation_position="top left")

    # UCL / LCL
    fig_i.add_hline(y=stats['UCL_I'], line=dict(color='red'), 
                    annotation_text=f"UCL = {stats['UCL_I']:.3f}", annotation_position="top right")
    fig_i.add_hline(y=stats['LCL_I'], line=dict(color='red'), 
                    annotation_text=f"LCL = {stats['LCL_I']:.3f}", annotation_position="bottom right")

    # resaltar puntos fuera de control
    if any(ooc_mask):
        fig_i.add_trace(go.Scatter(
            x=x_vals[ooc_mask], y=y_vals[ooc_mask],
            mode='markers', marker=dict(color='red', size=10, symbol='x'),
            name='Fuera de control'
        ))

    fig_i.update_layout(
        title=f"I Chart — {titulo}",
        xaxis_title="Fecha",
        yaxis_title="Valor",
        height=420,
        margin=dict(l=50, r=20, t=60, b=60)
    )

    # ----------------- FIGURA MR (Moving Range) -----------------
    # MR values correspond to gaps between consecutive samples; align at midpoint or second sample
    MR = stats['MR']
    if MR.size == 0:
        fig_mr = go.Figure()
        fig_mr.add_annotation(text="No hay suficientes pares consecutivos para MR (se requieren al menos 2 mediciones).",
                              showarrow=False)
    else:
        # x positions for MR: use the midpoint between consecutive times or use the second measurement time
        x_mr = x_vals.iloc[1:].reset_index(drop=True)
        fig_mr = go.Figure()
        fig_mr.add_trace(go.Bar(x=x_mr, y=MR, name='MR', marker=dict()))
        # MR centerline and limits
        fig_mr.add_hline(y=stats['MRbar'], line=dict(dash='dash'),
                         annotation_text=f"MR̄ = {stats['MRbar']:.3f}", annotation_position="top left")
        fig_mr.add_hline(y=stats['UCL_MR'], line=dict(color='red'),
                         annotation_text=f"UCL_MR = {stats['UCL_MR']:.3f}", annotation_position="top right")
        fig_mr.add_hline(y=stats['LCL_MR'], line=dict(color='red'),
                         annotation_text=f"LCL_MR = {stats['LCL_MR']:.3f}", annotation_position="bottom right")
        fig_mr.update_layout(title=f"MR Chart — {titulo}", xaxis_title="Fecha", yaxis_title="MR",
                             height=300, margin=dict(l=50, r=20, t=50, b=50))

    return fig_i, fig_mr, ooc_indices, stats

# ---------------- STREAMLIT APP ----------------
def app_graficos_control():
    st.title("📊 Gráficos de Control — I-MR (Automático por parámetro)")

    df = obtener_controles_join()

    if df.empty:
        st.warning("No se encontraron registros en la tabla controlcalidad.")
        return

    # --- Filtros laterales ---
    with st.sidebar:
        st.header("Filtros")
        # líneas
        lineas = df[['idLinea', 'nombreLinea']].drop_duplicates().sort_values('nombreLinea')
        linea_map = {int(r.idLinea): r.nombreLinea for r in lineas.itertuples()} if not lineas.empty else {}
        linea_sel = st.selectbox("Línea de producción", options=[None] + list(linea_map.keys()),
                                 format_func=lambda x: "Todas" if x is None else linea_map.get(x, str(x)))
        # presentaciones (desde detalleordentrabajo - idPresentacion or detallePresentacion)
        presentaciones = df[['idPresentacion']].drop_duplicates().dropna().sort_values('idPresentacion')
        present_sel = st.selectbox("Presentación (id)", options=[None] + presentaciones['idPresentacion'].astype(int).tolist()
                                  if not presentaciones.empty else [None],
                                  format_func=lambda x: "Todas" if x is None else str(x))
        # parametros
        parametros = df[['idParametro', 'nombreParametro']].drop_duplicates().sort_values('nombreParametro')
        param_map = {int(r.idParametro): r.nombreParametro for r in parametros.itertuples()} if not parametros.empty else {}
        param_sel = st.multiselect("Parámetro(s)", options=list(param_map.keys()), format_func=lambda x: param_map.get(x, str(x)),
                                   default=list(param_map.keys())[:3] if len(param_map)>0 else [])
        # lotes
        lotes = df[['lote']].drop_duplicates().dropna().sort_values('lote')
        lote_sel = st.selectbox("Lote", options=[None] + lotes['lote'].tolist() if not lotes.empty else [None],
                                format_func=lambda x: "Todos" if x is None else str(x))
        # rango de fecha
        min_date = df['fechaControl'].min().date()
        max_date = df['fechaControl'].max().date()
        date_range = st.date_input("Rango de fechas", value=(min_date, max_date), min_value=min_date, max_value=max_date)

        st.markdown("---")
        st.write("Opciones de gráficas:")
        agrupar = st.checkbox("Generar gráfico por presentación+línea automáticamente (si no, solo para parámetros seleccionados)", value=True)
        mostrar_todo = st.checkbox("Mostrar tabla de datos filtrada", value=False)
        download_csv = st.checkbox("Añadir botón para descargar CSV", value=True)

    # --- Aplicar filtros ---
    df_f = df.copy()
    # fecha
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df_f = df_f[(df_f['fechaControl'] >= start_date) & (df_f['fechaControl'] <= end_date)]
    # linea
    if linea_sel is not None:
        df_f = df_f[df_f['idLinea'] == int(linea_sel)]
    # presentacion
    if present_sel is not None:
        df_f = df_f[df_f['idPresentacion'] == int(present_sel)]
    # lote
    if lote_sel is not None:
        df_f = df_f[df_f['lote'] == lote_sel]
    # parametros
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
        st.download_button("📥 Descargar CSV (datos filtrados)", data=csv, file_name="controles_filtrados.csv", mime="text/csv")

    # --- Agrupar y generar gráficos ---
    # Si agrupar=True: generar por cada combo (idParametro, idPresentacion, idLinea)
    combos = []
    if agrupar:
        combos = df_f[['idParametro', 'idPresentacion', 'idLinea']].drop_duplicates().to_dict('records')
    else:
        # generar por cada idParametro seleccionado (manteniendo otros filtros)
        combos = [{'idParametro': pid, 'idPresentacion': None, 'idLinea': None} for pid in (param_sel or [])]

    # límite de combos para evitar renders gigantes (puedes ajustar)
    MAX_COMBOS = 50
    if len(combos) > MAX_COMBOS:
        st.warning(f"Se detectaron {len(combos)} combinaciones; se generarán las primeras {MAX_COMBOS}. Ajusta filtros para reducir.")
        combos = combos[:MAX_COMBOS]

    # loop y render
    for combo in combos:
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

        # título descriptivo
        param_name = sel_df['nombreParametro'].iloc[0] if 'nombreParametro' in sel_df.columns else f"Parametro {pid}"
        linea_name = sel_df['nombreLinea'].iloc[0] if 'nombreLinea' in sel_df.columns else f"Línea {lid}" if lid else "Todas las líneas"
        pres_name = str(pres) if pres else "Todas presentaciones"
        lote_here = sel_df['lote'].dropna().unique()
        titulo = f"{param_name} — {linea_name} — Presentación {pres_name}"

        st.markdown(f"### {titulo}")
        st.write(f"Filas: {len(sel_df)} · Lotes: {', '.join(map(str, lote_here[:6]))}{'...' if len(lote_here)>6 else ''}")

        fig_i, fig_mr, ooc_indices, stats = plot_I_MR(sel_df[['fechaControl', 'resultado']].copy(), titulo)

        if fig_i:
            st.plotly_chart(fig_i, use_container_width=True)
        if fig_mr:
            st.plotly_chart(fig_mr, use_container_width=True)

        # información adicional y recomendaciones
        with st.expander("Detalles / Estadísticos"):
            st.write({
                'Media (Ī)': stats['I_mean'],
                'Sigma estimado (σ)': stats['sigma'],
                'MR̄': stats['MRbar'],
                'UCL I': stats['UCL_I'],
                'LCL I': stats['LCL_I'],
                'UCL MR': stats['UCL_MR'],
                'LCL MR': stats['LCL_MR'],
                'Puntos fuera de control (índices)': ooc_indices
            })
            if len(ooc_indices) > 0:
                st.error(f"Se encontraron {len(ooc_indices)} punto(s) fuera de control (Regla: fuera de 3σ). Revisa las fechas correspondientes:")
                for i in ooc_indices:
                    fecha = sel_df.sort_values('fechaControl').reset_index(drop=True).loc[i, 'fechaControl']
                    valor = sel_df.sort_values('fechaControl').reset_index(drop=True).loc[i, 'resultado']
                    st.write(f"- Índice {i}: {fecha} → {valor}")
            else:
                st.success("No se detectaron puntos fuera de control por la Regla 1 (3σ).")

    st.markdown("---")
    st.caption("Nota: este módulo usa la regla básica (puntos fuera de ±3σ). Si quieres añadir reglas adicionales (Western Electric, Nelson), lo integro.")


# Permite ejecutar directamente desde `streamlit run modules/graficos_control.py` (opcional)
if __name__ == "__main__":
    # Si corres este archivo de forma independiente
    st.set_page_config(page_title="Gráficos de Control", layout="wide")
    app_graficos_control()