# frontend/login.py
import streamlit as st
import mysql.connector
from mysql.connector import Error

# --- Función para conectar con la base de datos MySQL ---
def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='castro',      
            password='tu_password', 
            database='control_calidad'
        )
        if connection.is_connected():
            return connection
    except Error as e:
        st.error(f"Error de conexión a la BD: {e}")
    return None

# --- Función para verificar credenciales ---
def verificar_credenciales(usuario, contraseña):
    conn = create_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, usuario, rol FROM usuarios WHERE usuario=%s AND contraseña=%s"
        cursor.execute(query, (usuario, contraseña))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result
    return None

# --- Interfaz de Login ---
def mostrar_login():
    st.title("Sistema de Control de Calidad - Gustossi")
    st.subheader("Inicio de sesión")

    usuario = st.text_input("Usuario")
    contraseña = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        user = verificar_credenciales(usuario, contraseña)
        if user:
            st.success(f"Bienvenido, {user['usuario']} (Rol: {user['rol']})")
            st.session_state['usuario'] = user['usuario']
            st.session_state['rol'] = user['rol']
            # Aquí puedes redirigir a la página principal según rol
        else:
            st.error("Usuario o contraseña incorrectos")

# Llamar a la función para mostrar la pantalla
if __name__ == "__main__":
    mostrar_login()
