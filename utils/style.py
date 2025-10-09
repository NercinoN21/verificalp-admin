import base64
from pathlib import Path

import streamlit as st


def load_image_as_base64(image_path: str):
    """Carrega uma imagem e a converte para base64."""
    try:
        with open(image_path, 'rb') as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None


def load_css():
    """Carrega um CSS customizado para a aplicação."""
    st.markdown(
        """
        <style>
            /* Cor de fundo principal */
            .stApp {
                background-color: #f5f5f5;
            }

            /* Estilo da barra lateral */
            [data-testid="stSidebar"] {
                background-color: #ffffff;
            }

            /* Logo na barra lateral */
            .sidebar-logo {
                display: block;
                margin-left: auto;
                margin-right: auto;
                width: 100px;
                margin-bottom: 20px;
            }

            /* Botão primário */
            .stButton>button[kind="primary"] {
                background-color: #3498db;
                color: white;
                border-radius: 8px;
                border: none;
            }
            .stButton>button[kind="primary"]:hover {
                background-color: #2980b9;
            }

            /* Métricas no Dashboard */
            [data-testid="stMetric"] {
                background-color: #ffffff;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            }

            .login-logo {
                display: block;
                margin-left: auto;
                margin-right: auto;
                width: 240px;
                margin-bottom: 25px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def display_logo(container, class_name='sidebar-logo'):
    """Exibe a logo em um container específico com uma classe CSS."""
    logo_base64 = load_image_as_base64('logo.png')
    if logo_base64:
        container.markdown(
            f'<img src="data:image/png;base64,{logo_base64}" class="{class_name}">',
            unsafe_allow_html=True,
        )
