import streamlit as st
import hashlib
from database.db_connection import get_connection
from PIL import Image

# Colores y estilo base
PRIMARY_COLOR = "#FFFFFF"
SECONDARY_COLOR = "#A9A9A9"
ACCENT_COLOR = "#F22828"
BACKGROUND_COLOR = "#0E0E10"

# --- FUNCIÓN DE LOGIN ---
def login():
    st.set_page_config(
        page_title="Sistema de Control de Calidad - Gustossi",
        page_icon="🍪",
        layout="centered"
    )

    # CSS personalizado
    st.markdown(f"""
        <style>
            .stApp {{
                background-color: {BACKGROUND_COLOR};
                color: {PRIMARY_COLOR};
                font-family: 'Inter', sans-serif;
            }}
            .login-container {{
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 3rem;
                padding: 2rem;
            }}
            .login-box {{
                background-color: #1A1A1D;
                padding: 2rem;
                border-radius: 16px;
                width: 350px;
                box-shadow: 0 0 10px rgba(0,0,0,0.4);
            }}
            .login-box input {{
                background-color: #2A2A2D !important;
                color: white !important;
                border: none !important;
                border-radius: 8px;
            }}
            .login-box button {{
                background-color: {ACCENT_COLOR} !important;
                color: white !important;
                border-radius: 8px;
                font-weight: bold;
            }}
            .illustration {{
                text-align: center;
            }}
            .illustration img {{
                width: 380px;
                border-radius: 12px;
            }}
            h1, h3 {{
                text-align: center;
                color: {PRIMARY_COLOR};
            }}
        </style>
    """, unsafe_allow_html=True)

    # Encabezado
    st.markdown("<h1>SISTEMA DE CONTROL DE CALIDAD</h1>", unsafe_allow_html=True)
    st.markdown("<h3>Industrias Alimenticias Gustossi S.R.L.</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Contenedor principal (Formulario + Imagen)
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
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
                    st.success(f"Bienvenido {data['nombre']} ({data['nombreRol']})")

                    rol = data["nombreRol"].lower()
                    if "operario" in rol:
                        st.session_state["menu_actual"] = "operario"
                    elif "supervisor" in rol:
                        st.session_state["menu_actual"] = "supervisor"
                    elif "gerente" in rol or "administrador" in rol:
                        st.session_state["menu_actual"] = "gerente"

                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos o cuenta inactiva.")
            else:
                st.warning("Complete ambos campos antes de continuar.")

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="illustration">', unsafe_allow_html=True)
        try:
            logo = Image.open("assets/logo_gustossi.jpg")
            st.image(logo)
        except Exception:
            st.info("Coloca tu imagen en la carpeta: assets/logo_gustossi.jpg")
        st.markdown('</div>', unsafe_allow_html=True)