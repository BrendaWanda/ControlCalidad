import streamlit as st

def dashboard_powerbi():
    st.title("Dashboard Power BI - Indicadores de Calidad")
    st.markdown("---")
    st.write("Visualización de los indicadores de desempeño y defectos más frecuentes.")

    st.info("Puedes integrar aquí un dashboard publicado desde Power BI Online.")

    # --- Ejemplo de iframe de Power BI ---
    st.markdown("""
        <iframe title="Dashboard de Calidad Gustossi"
                width="100%" height="550"
                src="https://app.powerbi.com/view?r=TU_URL_PUBLICA_AQUI"
                frameborder="0" allowFullScreen="true"></iframe>
    """, unsafe_allow_html=True)

    st.markdown("Si prefieres, también puedes abrirlo en una nueva pestaña:")
    st.link_button("Abrir Dashboard en Power BI", "https://app.powerbi.com/groups/me/reports")
