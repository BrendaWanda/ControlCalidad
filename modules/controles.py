import streamlit as st

def registrar_control():
    st.title("📋 Registro de Controles de Calidad")
    st.markdown("---")
    st.write("Aquí el **operario** puede ingresar los datos de control de calidad en planta.")

    linea = st.selectbox("Línea de producción", ["Galletas de Coco", "Chispas de Chocolate", "Avena"])
    parametro = st.text_input("Parámetro de control (ej. Peso, Humedad, Textura)")
    valor = st.number_input("Valor medido", min_value=0.0, step=0.1)
    observacion = st.text_area("Observaciones")

    if st.button("Guardar Registro", use_container_width=True):
        st.success(f"✅ Registro guardado correctamente para {linea}.")
        # Aquí podrías agregar la inserción SQL hacia tu tabla ControlCalidad

def ver_alertas():
    st.title("🔔 Alertas Automáticas")
    st.markdown("---")
    st.info("Aquí se mostrarán alertas cuando un parámetro salga del rango de calidad establecido.")

def confirmar_registros():
    st.title("✅ Confirmación de Registros")
    st.markdown("---")
    st.write("El operario puede confirmar los controles realizados durante el turno.")
