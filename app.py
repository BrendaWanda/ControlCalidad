import streamlit as st
from modules import (
    usuarios, controles, graficos_control, graficos_alertas, reportes, estandares,
    ordenes, gestion_usuarios, dashboard_powerbi, lineas
)
from modules.styles import cargar_estilos  # agregado

# FUNCIÓN PRINCIPAL
def main():
    cargar_estilos()  # agregado

    # Si no hay usuario logueado → mostrar login
    if "usuario" not in st.session_state:
        usuarios.login()
        return

    # Usuario en sesión
    usuario = st.session_state["usuario"]
    rol = st.session_state.get("menu_actual", "").lower()

    # Barra lateral
    st.sidebar.image("assets/logo_gustossi.jpg", width=120)
    st.sidebar.markdown(f"**{usuario['nombre']} {usuario['apellido']}**")
    st.sidebar.markdown(f"Rol: **{usuario['nombreRol']}**")

    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    # Menús por rol
    if rol == "operario":
        menu_operario()
    elif rol == "supervisor":
        menu_supervisor()
    elif rol == "gerente":
        menu_gerente()
    else:
        st.error("Rol no reconocido o sin permisos de acceso.")

# MENÚ OPERARIO
def menu_operario():
    st.sidebar.title("Menú Operario")
    opciones = st.sidebar.radio("Seleccione una opción", [
        "Registrar Control de Calidad",
        "Ver Registros Guardados",
        "Ver Alertas Automáticas"
    ])

    if opciones == "Registrar Control de Calidad":
        controles.registrar_control()

    elif opciones == "Ver Registros Guardados":
        controles.ver_registros_guardados()

    elif opciones == "Ver Alertas Automáticas":
        controles.ver_alertas()

# MENÚ SUPERVISOR
def menu_supervisor():
    st.sidebar.title("Menú Supervisor")
    opciones = st.sidebar.radio("Seleccione una opción", [
        "Consultas de Registro",
        "Reportes Básicos",
        "Gráficos de Alertas",
        "Dashboards Power BI",
        "Órdenes de Trabajo"
    ])

    if opciones == "Consultas de Registro":
        graficos_control.app_graficos_control()

    elif opciones == "Reportes Básicos":
        reportes.reportes_basicos()
        
    elif opciones == "Gráficos de Alertas":
        graficos_alertas.ver_graficos_alertas()

    elif opciones == "Dashboards Power BI":
        dashboard_powerbi.dashboard_powerbi_module()

    elif opciones == "Órdenes de Trabajo":
        ordenes.gestionar_ordenes()

# MENÚ GERENTE DE PLANTA
def menu_gerente():
    st.sidebar.title("Menú Gerente de Planta")

    opciones = st.sidebar.radio("Seleccione una opción", [
        "Configuración de Parámetros de Calidad",
        "Gestión de Usuarios y Roles",
        "Órdenes de Trabajo",
        "Líneas de Producción",
        "Consultas y Reportes",
        "Gráficos de Alertas",
        "Dashboards Power BI"
    ])

    if opciones == "Configuración de Parámetros de Calidad":
        estandares.configurar_parametros()

    elif opciones == "Gestión de Usuarios y Roles":
        gestion_usuarios.gestion_usuarios()

    elif opciones == "Órdenes de Trabajo":
        ordenes.gestionar_ordenes()

    elif opciones == "Líneas de Producción":
        lineas.gestionar_lineas()

    elif opciones == "Consultas y Reportes":
        graficos_control.app_graficos_control()
        
    elif opciones == "Gráficos de Alertas":
        graficos_alertas.ver_graficos_alertas()

    elif opciones == "Dashboards Power BI":
        dashboard_powerbi.dashboard_powerbi_module()

# EJECUCIÓN
if __name__ == "__main__":
    main()
