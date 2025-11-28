# modules/dashboard_powerbi.py
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from database.db_connection import get_connection

# ============================================
#      FUNCIONES DE CONSULTA A BASE DE DATOS
# ============================================

@st.cache_data(ttl=300)
def obtener_tabla(nombre_tabla):
    """
    Devuelve un DataFrame de la tabla solicitada.
    """
    conn = get_connection()
    try:
        df = pd.read_sql(f"SELECT * FROM {nombre_tabla}", conn)
    except Exception as e:
        st.error(f"Error al consultar {nombre_tabla}: {e}")
        df = pd.DataFrame()
    conn.close()
    return df

# ============================================
#        MÓDULO PRINCIPAL
# ============================================

def dashboard_powerbi_module():
    st.set_page_config(page_title="Dashboard Power BI", layout="wide")
    st.title("📊 Dashboards Power BI")
    st.markdown("---")
    
    st.sidebar.header("Opciones del Dashboard")

    # Lista dinámica de dashboards
    dashboards = {
        "Alertas de Calidad": "https://app.powerbi.com/view?r=YOUR_EMBED_URL_ALERTAS",
        "Controles de Calidad": "https://app.powerbi.com/view?r=YOUR_EMBED_URL_CONTROLES",
        "Resumen General": "https://app.powerbi.com/view?r=YOUR_EMBED_URL_GENERAL"
    }

    dash_nombre = st.sidebar.selectbox("Selecciona un dashboard", list(dashboards.keys()))
    url_dashboard = dashboards[dash_nombre]

    # ---------------------------
    # Mostrar el dashboard incrustado
    # ---------------------------
    st.subheader(f"📌 Dashboard seleccionado: {dash_nombre}")
    components.iframe(src=url_dashboard, width=1200, height=700, scrolling=True)

    st.markdown("---")

    # ---------------------------
    # Opcional: Descargar datos de la base de datos
    # ---------------------------
    st.subheader("📥 Exportar datos del sistema")

    tabla_sel = st.selectbox("Selecciona la tabla para exportar", ["alerta", "controlcalidad"])
    
    if st.button("Generar CSV"):
        df_export = obtener_tabla(tabla_sel)
        if df_export.empty:
            st.warning("No hay datos para exportar.")
        else:
            st.success(f"Datos de `{tabla_sel}` listos para descargar.")
            csv_bytes = df_export.to_csv(index=False).encode("utf-8")
            st.download_button(
                label=f"📥 Descargar {tabla_sel}.csv",
                data=csv_bytes,
                file_name=f"{tabla_sel}.csv",
                mime="text/csv"
            )

    st.markdown("---")
    st.caption("Puedes seleccionar distintos dashboards desde la barra lateral. Los datos también pueden exportarse a CSV desde la base de datos del sistema.")

# =============================
# EJECUCIÓN DIRECTA
# =============================
if __name__ == "__main__":
    dashboard_powerbi_module()