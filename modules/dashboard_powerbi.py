"""
dashboard_powerbi.py
Componente para incrustar (embed) un dashboard Power BI dentro de Streamlit sin redireccionar.
- Intenta usar st.secrets['powerbi'] para obtener 'embed_url' y 'access_token' (si aplica).
- También permite pasar la URL (y token) por st.session_state o por inputs en modo administrador.
- Usa st.components.v1.html para renderizar el iframe y el script de incrustación.
IMPORTANTE:
- El mecanismo exacto de incrustación (EmbedUrl vs EmbedToken vs permisos) depende de la configuración de Power BI (service principal / embed token).
- Aquí se deja una plantilla segura para incrustar cuando ya tienes la URL pública o el html embed.
"""

import streamlit as st
import streamlit.components.v1 as components

def dashboard_powerbi_module():
    st.title("Dashboards Power BI")
    st.markdown("---")
    st.write("Incrusta dashboards de Power BI dentro del sistema. Proporcione el Embed URL y (si aplica) el token de acceso.")

    # Preferir st.secrets (más seguro)
    pbi = st.secrets.get("powerbi", {}) if isinstance(st.secrets, dict) else {}
    embed_url = pbi.get("embed_url") or st.session_state.get("powerbi_embed_url") or ""
    embed_token = pbi.get("embed_token") or st.session_state.get("powerbi_embed_token") or ""

    st.markdown("**Opciones de carga**")
    use_secrets = st.checkbox("Usar configuración desde st.secrets (si existe)", value=bool(embed_url))

    if not use_secrets:
        embed_url = st.text_input("Embed URL (Power BI)", value=embed_url, placeholder="https://app.powerbi.com/reportEmbed?reportId=...")
        embed_token = st.text_area("Embed Token (opcional)", value=embed_token, placeholder="Token si usas autenticación embed (opcional)")
        if st.button("Guardar en sesión"):
            st.session_state["powerbi_embed_url"] = embed_url
            st.session_state["powerbi_embed_token"] = embed_token
            st.success("Embed URL guardado en sesión.")

    if not embed_url:
        st.info("Proporcione la Embed URL de Power BI para incrustar el dashboard.")
        return

    st.markdown("### Vista previa del Dashboard")
    # La forma más simple es un iframe con la URL. Si requiere token en cabeceras, la solución completa necesita un proxy o script de JavaScript
    # que añada el token al header; muchos embed tokens se usan directamente en la URL o en la librería de Power BI JS (powerbi-client).
    # A continuación tenemos dos alternativas:
    # 1) iframe directo (si la URL es embeddable)
    # 2) Incrustación con powerbi-client (si se necesita token y la política CORS lo permite)
    use_powerbi_js = st.checkbox("Usar powerbi-client (si necesita token)", value=False)

    if use_powerbi_js and embed_token:
        # Template que usa powerbi-client. NOTA: requiere que el navegador permita cargar la librería desde CDN.
        html = f"""
        <div id="reportContainer" style="height:800px;border:1px solid #ddd"></div>
        <script src="https://cdn.jsdelivr.net/npm/powerbi-client/dist/powerbi-client.min.js"></script>
        <script>
        const models = window['powerbi-client'].models;
        const embedConfig = {{
            type: 'report',
            tokenType: models.TokenType.Embed,
            accessToken: '{embed_token}',
            embedUrl: '{embed_url}',
            settings: {{
                filterPaneEnabled: false,
                navContentPaneEnabled: true
            }}
        }};
        const reportContainer = document.getElementById('reportContainer');
        // remove existing embeds
        if (window.powerbi) {{
            window.powerbi.reset(reportContainer);
        }}
        const report = powerbi.embed(reportContainer, embedConfig);
        </script>
        """
        components.html(html, height=820, scrolling=True)
        st.success("Si el token/URL son válidos debería visualizarse el reporte.")
    else:
        # Iframe directo (mejor compatibilidad si la URL ya es pública embeddable)
        iframe_html = f"""
        <iframe title="Power BI" width="100%" height="820px" src="{embed_url}" frameborder="0" allowFullScreen="true"></iframe>
        """
        components.html(iframe_html, height=820, scrolling=True)
        st.success("Se intentó incrustar el dashboard mediante iframe. Si no se ve, use la opción 'Usar powerbi-client' y proporcione un Embed Token válido.")

    st.markdown("---")
    st.info("Si tu tenant usa tokens con cabeceras o autenticación más compleja, la integración segura requiere un backend que solicite el EmbedToken y lo entregue al front-end. Puedo ayudarte a agregar ese backend (endpoint) si lo deseas; dime cómo gestionas tus credenciales.")
