import streamlit as st
from database.db_connection import get_connection
import hashlib

# =============================================================
# GESTIÓN DE USUARIOS Y ROLES
# =============================================================

def gestion_usuarios():
    st.title("👤 Gestión de Usuarios y Roles")
    st.markdown("---")
    st.write("El **Gerente de Planta** puede administrar las cuentas de usuario del sistema Gustossi S.R.L.")

    # Opciones principales
    opcion = st.radio("Seleccione una acción:", [
        "Ver usuarios",
        "Agregar nuevo usuario",
        "Editar usuario existente",
        "Activar / Desactivar usuario"
    ])

    # =============================================================
    # VER USUARIOS
    # =============================================================
    if opcion == "Ver usuarios":
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
            st.info("No hay usuarios registrados en el sistema.")

    # =============================================================
    # AGREGAR NUEVO USUARIO
    # =============================================================
    elif opcion == "Agregar nuevo usuario":
        with st.form("form_agregar_usuario", clear_on_submit=True):
            st.subheader("➕ Registrar nuevo usuario")

            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre")
                apellido = st.text_input("Apellido")
                correo = st.text_input("Correo electrónico")
            with col2:
                usuario = st.text_input("Nombre de usuario")
                opciones_roles = ["— Seleccionar Rol —", "Operario", "Supervisor", "Gerente de Planta"]
                rol = st.selectbox("Rol asignado", opciones_roles)
                contraseña = st.text_input("Contraseña", type="password")

            enviar = st.form_submit_button("💾 Guardar Usuario")

            if enviar:
                if not (nombre and usuario and contraseña) or rol == "— Seleccionar Rol —":
                    st.warning("⚠️ Complete los campos obligatorios y seleccione un rol válido.")
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
                    st.success(f"✅ Usuario **'{usuario}'** agregado correctamente como **{rol}**.")

    # =============================================================
    # EDITAR USUARIO EXISTENTE
    # =============================================================
    elif opcion == "Editar usuario existente":
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT idUsuario, usuario FROM Usuario ORDER BY usuario;")
        lista = cursor.fetchall()
        cursor.close()
        conn.close()

        if lista:
            opciones_usuarios = ["— Seleccionar Usuario —"] + [u['usuario'] for u in lista]
            seleccionado = st.selectbox("Seleccione el usuario a editar:", opciones_usuarios)

            if seleccionado != "— Seleccionar Usuario —":
                idUsuario = next(u['idUsuario'] for u in lista if u['usuario'] == seleccionado)
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT U.*, R.nombreRol 
                    FROM Usuario U INNER JOIN Rol R ON U.idRol=R.idRol 
                    WHERE U.idUsuario=%s
                """, (idUsuario,))
                data = cursor.fetchone()
                cursor.close()
                conn.close()

                if data:
                    with st.form("editar_usuario", clear_on_submit=True):
                        st.subheader(f"✏️ Editar Usuario: {seleccionado}")
                        nombre = st.text_input("Nombre", value=data["nombre"])
                        apellido = st.text_input("Apellido", value=data["apellido"])
                        correo = st.text_input("Correo", value=data["correo"])
                        roles_posibles = ["— Seleccionar Rol —", "Operario", "Supervisor", "Gerente de Planta"]
                        rol = st.selectbox("Rol", roles_posibles,
                            index=roles_posibles.index(data["nombreRol"]) if data["nombreRol"] in roles_posibles else 0)
                        nueva_contra = st.text_input("Nueva contraseña (opcional)", type="password")
                        guardar = st.form_submit_button("💾 Guardar cambios")

                        if guardar:
                            if rol == "— Seleccionar Rol —":
                                st.warning("⚠️ Seleccione un rol válido antes de continuar.")
                            else:
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
                                st.success(f"✅ Usuario **'{seleccionado}'** actualizado correctamente.")
                else:
                    st.error("❌ No se encontró la información del usuario seleccionado.")
        else:
            st.info("ℹ️ No hay usuarios registrados para editar.")

    # =============================================================
    # ACTIVAR / DESACTIVAR USUARIO
    # =============================================================
    elif opcion == "Activar / Desactivar usuario":
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT idUsuario, usuario, activo FROM Usuario ORDER BY usuario;")
        usuarios = cursor.fetchall()

        if usuarios:
            opciones_usuarios = ["— Seleccionar Usuario —"] + [u["usuario"] for u in usuarios]
            seleccionado = st.selectbox("Seleccione el usuario:", opciones_usuarios)

            if seleccionado != "— Seleccionar Usuario —":
                estado_actual = next((u["activo"] for u in usuarios if u["usuario"] == seleccionado), 1)
                nuevo_estado = 0 if estado_actual == 1 else 1
                etiqueta = "Desactivar" if estado_actual == 1 else "Activar"

                if st.button(f"{etiqueta} usuario", use_container_width=True):
                    cursor.execute("UPDATE Usuario SET activo=%s WHERE usuario=%s", (nuevo_estado, seleccionado))
                    conn.commit()
                    st.success(f"✅ Usuario **'{seleccionado}'** ahora está {'activo' if nuevo_estado == 1 else 'inactivo'}.")
        else:
            st.info("ℹ️ No hay usuarios para modificar estado.")
        cursor.close()
        conn.close()


# =============================================================
# EJECUCIÓN DIRECTA
# =============================================================
if __name__ == "__main__":
    gestion_usuarios()