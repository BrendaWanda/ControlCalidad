import streamlit as st

def cargar_estilos():
    st.markdown("""
        <style>

        /* PALETA DE COLORES*/
        :root {
            --azul-oscuro: #0A192F;       /* Fondo principal */
            --azul-card: #112240;         /* Tarjetas y campos */
            --azul-hover: #233554;        /* Hover */
            --borde: #334E68;             /* Bordes suaves */
            --texto: #FFFFFF;             /* Blanco */
            --rojo: #FF4C4C;              /* Botones / Acentos */
        }

        /* FONDO GENERAL*/
        body, .main {
            background-color: var(--azul-oscuro) !important;
            color: var(--texto) !important;
        }

        /* SIDEBAR*/
        section[data-testid="stSidebar"] {
            background-color: #07111F !important;
            border-right: 1px solid var(--borde) !important;
        }

        /* TÍTULOS*/
        h1, h2, h3, h4, h5, h6 {
            color: var(--texto) !important;
            font-weight: 700 !important;
        }

        /* CONTENEDORES*/
        .stContainer, .stTabs [data-baseweb="tab"] {
            background-color: var(--azul-card) !important;
            border-radius: 12px !important;
            padding: 12px !important;
            border: 1px solid var(--borde) !important;
        }

        /* TAB SELECCIONADA*/
        .stTabs [aria-selected="true"] {
            background-color: var(--rojo) !important;
            color: white !important;
            font-weight: 700 !important;
            border-radius: 10px !important;
        }

        /* BOTONES*/
        .stButton>button {
            background: linear-gradient(90deg, var(--rojo), #B30000) !important;
            color: white !important;
            border: none !important;
            padding: 8px 18px !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: 0.2s ease-in-out;
        }

        .stButton>button:hover {
            background: linear-gradient(90deg, #B30000, var(--rojo)) !important;
            transform: scale(1.03);
        }

        /* INPUTS (cajas de texto, select)*/
        .stTextInput>div>div>input,
        .stSelectbox>div>div>div,
        .stNumberInput>div>div>input {
            background-color: var(--azul-card) !important;
            color: var(--texto) !important;
            border-radius: 8px !important;
            border: 1px solid var(--borde) !important;
        }

        /* DATAFRAME*/
        .dataframe {
            background-color: var(--azul-card) !important;
            color: var(--texto) !important;
        }

        /* Hover filas de tabla */
        .dataframe tbody tr:hover {
            background-color: var(--azul-hover) !important;
        }

        </style>
    """, unsafe_allow_html=True)
