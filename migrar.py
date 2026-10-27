import sqlite3
import pandas as pd
from supabase import create_client
import streamlit as st

print("🔄 A conectar ao Supabase e ao SQLite local...")

# Puxa as credenciais que guardou no ficheiro secrets.toml
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

conn = sqlite3.connect("pcp_lavra.db")

def migrar_tabela(nome_tabela):
    df = pd.read_sql_query(f"SELECT * FROM {nome_tabela}", conn)
    if not df.empty:
        registos = df.to_dict(orient="records")
        # Inserir em blocos de 500 para não sobrecarregar a rede
        tamanho_bloco = 500
        for i in range(0, len(registos), tamanho_bloco):
            bloco = registos[i:i+tamanho_bloco]
            supabase.table(nome_tabela).upsert(bloco).execute()
        print(f"✅ {len(registos)} registos migrados para a tabela: {nome_tabela}")
    else:
        print(f"⚠️ A tabela {nome_tabela} está vazia no SQLite.")

migrar_tabela("horaria_carga")
migrar_tabela("horaria_perf")
migrar_tabela("parte_diaria")
migrar_tabela("pcp_planejamento")

print("🚀 Mão de obra concluída! Todos os dados estão agora na nuvem.")
conn.close()