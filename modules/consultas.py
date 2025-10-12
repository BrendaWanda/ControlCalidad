import streamlit as st

def ver_registros():
    st.title("🔎 Consultas de Registro de Control")
    st.markdown("---")

    st.write("Filtrar registros por:")
    col1, col2, col3 = st.columns(3)
    with col1:
        fecha = st.date_input("Fecha")
    with col2:
        linea = st.selectbox("Línea", ["Todas", "Coco", "Chocolate", "Avena"])
    with col3:
        turno = st.selectbox("Turno", ["Todos", "Mañana", "Tarde", "Noche"])

    if st.button("Buscar", use_container_width=True):
        st.success("Resultados filtrados (ejemplo).")
        st.dataframe({
            "Fecha": ["2025-10-11"],
            "Línea": ["Coco"],
            "Parámetro": ["Peso"],
            "Valor": [12.3],
            "Conforme": ["Sí"]
        })
