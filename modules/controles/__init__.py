from .registrar import registrar_control
from .buscar import ver_registros_guardados
from .alertas import ver_alertas
import streamlit as st

def app_controles():
    menu = st.sidebar.radio(
        "Control de Calidad",
        [
            "Registrar Control",
            "Ver Registros Guardados",
            "Ver Alertas Automáticas"
        ]
    )

    if menu == "Registrar Control":
        registrar_control()
    elif menu == "Ver Registros Guardados":
        ver_registros_guardados()
    else:
        ver_alertas()

if __name__ == "__main__":
    app_controles()
