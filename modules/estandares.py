import streamlit as st

def configurar_parametros():
    st.title("⚙️ Configuración de Parámetros de Calidad")
    st.markdown("---")
    st.write("El gerente puede definir o modificar los estándares de control de calidad.")

    parametro = st.text_input("Nombre del parámetro")
    unidad = st.text_input("Unidad de medida (ej. g, %)")
    valor_min = st.number_input("Valor mínimo permitido", step=0.1)
    valor_max = st.number_input("Valor máximo permitido", step=0.1)

    if st.button("Guardar Parámetro", use_container_width=True):
        st.success(f"✅ Parámetro '{parametro}' guardado correctamente.")

def historial_cambios():
    st.title("🕓 Historial de Cambios en Parámetros")
    st.markdown("---")
    st.info("Aquí se mostrarán las modificaciones realizadas por los usuarios autorizados.")
