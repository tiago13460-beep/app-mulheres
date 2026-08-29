import os
import psycopg2

def criar_conexao():
    # O Render vai ler a URL do banco que vamos configurar nas variáveis de ambiente
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não foi configurada no Render.")
        
    # Abre a conexão com o PostgreSQL do Render
    conexao = psycopg2.connect(DATABASE_URL)
    return conexao
