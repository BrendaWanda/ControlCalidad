import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def reportes_basicos():
    st.title("Reportes Básicos de Calidad")
    st.markdown("---")
    st.write("Visualización general de los controles realizados por línea de producción.")

    # Ejemplo de datos
    data = {
        "Línea": ["Coco", "Chocolate", "Avena"],
        "Controles": [50, 45, 60],
        "Conformes": [48, 43, 58]
    }
    df = pd.DataFrame(data)
    df["% Conformidad"] = round((df["Conformes"] / df["Controles"]) * 100, 2)
    st.dataframe(df)

    st.subheader("Gráfico de Conformidad por Línea")
    fig, ax = plt.subplots()
    ax.bar(df["Línea"], df["% Conformidad"])
    ax.set_ylabel("% Conformidad")
    st.pyplot(fig)

def dashboard_powerbi():
    st.title("Dashboards Power BI")
    st.markdown("---")
    st.info("Aquí se integrarán los dashboards de Power BI (vinculación externa).")
