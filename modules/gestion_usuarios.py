import streamlit as st
from database.db_connection import get_connection
import hashlib

# GESTIÓN DE USUARIOS Y ROLES

def gestion_usuarios():
    st.title("Gestión de Usuarios y Roles - Gustossi S.R.L.")
    st.markdown("---")

    # MENÚ PRINCIPAL EN TABS
    tabs = st.tabs([
        "Ver Usuarios",
        "Agregar Usuario",
        "Editar Usuario",
        "Activar / Desactivar"
    ])

    # TAB 1 - VER USUARIOS
    with tabs[0]:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT U.idUsuario, U.nombre, U.apellido, U.usuario, R.nombreRol AS rol, 
                U.correo, IF(U.activo=1, 'Activo', 'Inactivo') AS estado
            FROM Usuario U
            INNER JOIN Rol R ON U.idRol = R.idRol
            ORDER BY U.idUsuario
        """)
        data = cursor.fetchall()
        cursor.close()
        conn.close()

        if data:
            st.dataframe(data, use_container_width=True)
        else:
            st.info("No hay usuarios registrados aún.")

    # TAB 2 - AGREGAR USUARIO
    with tabs[1]:
        with st.form("form_agregar_usuario", clear_on_submit=True):
            st.subheader("Registrar Nuevo Usuario")

            col1, col2 = st.columns(2)

            with col1:
                nombre = st.text_input("Nombre")
                apellido = st.text_input("Apellido")
                correo = st.text_input("Correo electrónico")

            with col2:
                usuario = st.text_input("Nombre de usuario")
                rol = st.selectbox(
                    "Rol",
                    ["— Seleccionar Rol —", "Operario", "Supervisor", "Gerente de Planta"]
                )
                contraseña = st.text_input("Contraseña", type="password")

            guardar = st.form_submit_button("Guardar Usuario")

            if guardar:
                if not (nombre and usuario and contraseña) or rol == "— Seleccionar Rol —":
                    st.warning("Complete todos los campos obligatorios.")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()
                    hashed = hashlib.sha256(contraseña.encode()).hexdigest()

                    cursor.execute("""
                        INSERT INTO Usuario (nombre, apellido, correo, usuario, passwordHash, activo, idRol)
                        VALUES (%s, %s, %s, %s, %s, 1,
                                (SELECT idRol FROM Rol WHERE nombreRol=%s))
                    """, (nombre, apellido, correo, usuario, hashed, rol))

                    conn.commit()
                    conn.close()

                    st.success(f"Usuario **{usuario}** registrado correctamente.")

    # TAB 3 - EDITAR USUARIO
    with tabs[2]:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT idUsuario, usuario FROM Usuario ORDER BY usuario;")
        lista = cursor.fetchall()
        cursor.close()
        conn.close()

        if lista:
            usuario_sel = st.selectbox(
                "Seleccione el usuario:",
                ["— Seleccionar —"] + [u["usuario"] for u in lista]
            )

            if usuario_sel != "— Seleccionar —":
                idUsuario = next(u["idUsuario"] for u in lista if u["usuario"] == usuario_sel)

                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT U.*, R.nombreRol 
                    FROM Usuario U INNER JOIN Rol R ON U.idRol = R.idRol
                    WHERE U.idUsuario=%s
                """, (idUsuario,))
                data = cursor.fetchone()
                cursor.close()
                conn.close()

                with st.form("editar_usuario"):
                    col1, col2 = st.columns(2)

                    with col1:
                        nombre = st.text_input("Nombre", value=data["nombre"])
                        apellido = st.text_input("Apellido", value=data["apellido"])
                        correo = st.text_input("Correo", value=data["correo"])

                    with col2:
                        rol = st.selectbox(
                            "Rol",
                            ["Operario", "Supervisor", "Gerente de Planta"],
                            index=["Operario", "Supervisor", "Gerente de Planta"].index(data["nombreRol"])
                        )
                        nueva_contra = st.text_input("Nueva contraseña", type="password")

                    guardar = st.form_submit_button("Guardar Cambios")

                    if guardar:
                        conn2 = get_connection()
                        cursor2 = conn2.cursor()

                        if nueva_contra:
                            hashed = hashlib.sha256(nueva_contra.encode()).hexdigest()
                            cursor2.execute("""
                                UPDATE Usuario
                                SET nombre=%s, apellido=%s, correo=%s,
                                    passwordHash=%s, idRol=(SELECT idRol FROM Rol WHERE nombreRol=%s)
                                WHERE idUsuario=%s
                            """, (nombre, apellido, correo, hashed, rol, idUsuario))
                        else:
                            cursor2.execute("""
                                UPDATE Usuario
                                SET nombre=%s, apellido=%s, correo=%s,
                                    idRol=(SELECT idRol FROM Rol WHERE nombreRol=%s)
                                WHERE idUsuario=%s
                            """, (nombre, apellido, correo, rol, idUsuario))

                        conn2.commit()
                        conn2.close()

                        st.success("Usuario actualizado correctamente.")
                        st.rerun()
        else:
            st.info("No hay usuarios registrados.")

    # TAB 4 - ACTIVAR / DESACTIVAR
    with tabs[3]:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT idUsuario, usuario, activo FROM Usuario ORDER BY usuario;")
        usuarios = cursor.fetchall()

        if usuarios:
            usuario_sel = st.selectbox(
                "Seleccione Usuario",
                ["— Seleccionar —"] + [u["usuario"] for u in usuarios]
            )

            if usuario_sel != "— Seleccionar —":
                estado = next(u["activo"] for u in usuarios if u["usuario"] == usuario_sel)
                nuevo_estado = 0 if estado == 1 else 1
                etiqueta = "Desactivar" if estado == 1 else "Activar"

                if st.button(f"{etiqueta} Usuario", use_container_width=True):
                    cursor.execute("""
                        UPDATE Usuario
                        SET activo=%s
                        WHERE usuario=%s
                    """, (nuevo_estado, usuario_sel))

                    conn.commit()
                    st.success(f"El usuario fue {'activado' if nuevo_estado == 1 else 'desactivado'}.")
                    st.rerun()
        else:
            st.info("No hay usuarios para modificar.")

        cursor.close()
        conn.close()


if __name__ == "__main__":
    gestion_usuarios()
