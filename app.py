import streamlit as st
from modules import usuarios, controles, consultas, reportes, estandares, ordenes

# ======================================================
# FUNCIÓN PRINCIPAL
# ======================================================
def main():
    # Si no hay usuario logueado → mostrar login
    if "usuario" not in st.session_state:
        usuarios.login()
        return

    # Si ya hay usuario en sesión
    usuario = st.session_state["usuario"]
    rol = st.session_state.get("menu_actual", "").lower()

    # --- Barra lateral de sesión ---
    st.sidebar.image("assets/logo_gustossi.jpg", width=120)
    st.sidebar.markdown(f"👋 **{usuario['nombre']} {usuario['apellido']}**")
    st.sidebar.markdown(f"🧩 Rol: **{usuario['nombreRol']}**")
    if st.sidebar.button("Cerrar Sesión 🔒", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    # --- Redirigir al menú correspondiente según rol ---
    if rol == "operario":
        menu_operario()
    elif rol == "supervisor":
        menu_supervisor()
    elif rol == "gerente":
        menu_gerente()
    else:
        st.error("⚠️ Rol no reconocido o sin permisos de acceso.")

# ======================================================
# MENÚ OPERARIO
# ======================================================
def menu_operario():
    st.sidebar.title("👷 Menú Operario")
    opciones = st.sidebar.radio("Seleccione una opción", [
        "Registro de Controles de Calidad",
        "Ver Alertas Automáticas",
        "Confirmar Registros"
    ])

    if opciones == "Registro de Controles de Calidad":
        controles.registrar_control()
    elif opciones == "Ver Alertas Automáticas":
        controles.ver_alertas()
    elif opciones == "Confirmar Registros":
        controles.confirmar_registros()

# ======================================================
# MENÚ SUPERVISOR
# ======================================================
def menu_supervisor():
    st.sidebar.title("🧑‍💼 Menú Supervisor")
    opciones = st.sidebar.radio("Seleccione una opción", [
        "Consultas de Registro",
        "Reportes Básicos",
        "Dashboards Power BI"
    ])

    if opciones == "Consultas de Registro":
        consultas.ver_registros()
    elif opciones == "Reportes Básicos":
        reportes.reportes_basicos()
    elif opciones == "Dashboards Power BI":
        reportes.dashboard_powerbi()

# ======================================================
# MENÚ GERENTE DE PLANTA
# ======================================================
def menu_gerente():
    st.sidebar.title("👨‍🏭 Menú Gerente de Planta")
    opciones = st.sidebar.radio("Seleccione una opción", [
        "Configuración de Parámetros de Calidad",
        "Gestión de Usuarios y Roles",
        "Órdenes de Trabajo",
        "Consultas y Reportes",
        "Dashboards Power BI"
    ])

    if opciones == "Configuración de Parámetros de Calidad":
        estandares.configurar_parametros()
    elif opciones == "Gestión de Usuarios y Roles":
        st.info("👥 Módulo en desarrollo: gestión de usuarios y roles.")
    elif opciones == "Órdenes de Trabajo":
        ordenes.gestionar_ordenes()
    elif opciones == "Consultas y Reportes":
        consultas.ver_registros()
    elif opciones == "Dashboards Power BI":
        reportes.dashboard_powerbi()

# ======================================================
# EJECUCIÓN DEL SISTEMA
# ======================================================
if __name__ == "__main__":
    main()
