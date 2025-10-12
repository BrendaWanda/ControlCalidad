
import streamlit as st
import hashlib
from database.db_connection import get_connection
from PIL import Image

# 🎨 Colores corporativos Gustossi
PRIMARY_COLOR = "#F4F8FC"
ACCENT_COLOR = "#F22828"
BACKGROUND_COLOR = "#110237C5"

# ==============================================
# FUNCIÓN DE LOGIN
# ==============================================
def login():
    st.set_page_config(
        page_title="Sistema de Control de Calidad - Gustossi",
        page_icon="🍪",
        layout="centered"
    )

    # --- Encabezado con título y logo ---
    st.markdown(f"""
        <div style="text-align:center; background-color:{BACKGROUND_COLOR};
                    padding:20px; border-radius:12px; box-shadow: 0px 2px 8px rgba(0,0,0,0.1);">
            <h1 style="color:{PRIMARY_COLOR}; margin-bottom:5px;">
                SISTEMA DE CONTROL DE CALIDAD
            </h1>
            <h3 style="color:{PRIMARY_COLOR}; margin-top:0;">
                Industrias Alimenticias Gustossi S.R.L.
            </h3>
        </div>
    """, unsafe_allow_html=True)

    # --- Logo debajo del título ---
    try:
        logo = Image.open("assets/logo_gustossi.jpg")
        st.image(logo, width=180)
    except Exception:
        st.info("⚠️ Coloca tu logo en la carpeta: assets/logo_gustossi.png")

    # --- Formulario de inicio de sesión ---
    st.markdown("---")
    st.subheader("🔐 Iniciar Sesión")

    usuario = st.text_input("Usuario", placeholder="Ingrese su usuario")
    contraseña = st.text_input("Contraseña", type="password", placeholder="Ingrese su contraseña")

    if st.button("Iniciar sesión", use_container_width=True):
        if usuario and contraseña:
            hashed = hashlib.sha256(contraseña.encode()).hexdigest()
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT U.*, R.nombreRol 
                FROM Usuario U
                INNER JOIN Rol R ON U.idRol = R.idRol
                WHERE U.usuario=%s AND U.passwordHash=%s AND U.activo=1
            """, (usuario, hashed))
            data = cursor.fetchone()

            if data:
                st.session_state["usuario"] = data
                st.success(f"✅ Bienvenido {data['nombre']} ({data['nombreRol']})")

                # --- Redirección según el rol ---
                rol = data["nombreRol"].lower()
                if "operario" in rol:
                    st.session_state["menu_actual"] = "operario"
                elif "supervisor" in rol:
                    st.session_state["menu_actual"] = "supervisor"
                elif "gerente" in rol or "administrador" in rol:
                    st.session_state["menu_actual"] = "gerente"

                # 🔁 Redirigir a la vista correspondiente
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos o cuenta inactiva.")
        else:
            st.warning("⚠️ Complete ambos campos antes de continuar.")
