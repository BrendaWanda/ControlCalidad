import streamlit as st

def gestionar_ordenes():
    st.title("Órdenes de Trabajo")
    st.markdown("---")
    st.write("El gerente puede crear, editar o vincular órdenes de trabajo con controles de calidad.")

    codigo = st.text_input("Código de orden")
    linea = st.selectbox("Línea de producción", ["Coco", "Chocolate", "Avena"])
    fecha = st.date_input("Fecha programada")

    if st.button("Guardar Orden", use_container_width=True):
        st.success(f"Orden {codigo} registrada para la línea {linea} el {fecha}.")

def relacionar_controles():
    st.title("Relacionar Controles con Órdenes de Trabajo")
    st.markdown("---")
    st.info("Permite vincular controles de calidad con las órdenes programadas.")
