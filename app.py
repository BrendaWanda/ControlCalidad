import streamlit as st
import mysql.connector
import pandas as pd

# --- Conexión con MySQL ---
conexion = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # si pusiste contraseña en XAMPP, cámbiala aquí
    database="control_calidad_db"
)

# --- Título de la app ---
st.title("Sistema de Control de Calidad - Gustossi")

# --- Ejemplo de consulta ---
cursor = conexion.cursor()
cursor.execute("SELECT * FROM usuarios")
datos = cursor.fetchall()

st.subheader("Usuarios registrados:")
for fila in datos:
    st.write(fila)
