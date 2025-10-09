import os

import streamlit as st
from pymongo import MongoClient
from pymongo.database import Database


@st.cache_resource
def get_db_connection() -> MongoClient:
    """
    Estabelece e retorna a conexão com o MongoDB.
    Utiliza o cache do Streamlit para manter a conexão viva.
    """
    try:
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            st.error('A variável de ambiente MONGO_URI não foi definida.')
            st.stop()
        client = MongoClient(mongo_uri)

        client.admin.command('ping')
        print('Conexão com o MongoDB estabelecida com sucesso.')
        return client
    except Exception as e:
        print(f'Erro ao conectar com o MongoDB: {e}')
        return None


@st.cache_resource
def get_database(_client: MongoClient) -> Database | None:
    """
    Retorna a database específica a partir de uma conexão ativa.
    """
    if _client:
        db_name = os.getenv('DB_NAME', 'DLPL')
        return _client[db_name]
    return None
