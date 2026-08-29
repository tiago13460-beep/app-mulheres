import os
import psycopg2
from psycopg2.extras import RealDictCursor

def criar_conexao():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não foi configurada no Render.")
    
    # Conecta ao PostgreSQL
    return psycopg2.connect(DATABASE_URL)

def inicializar_banco():
    """Cria as tabelas estruturais caso elas não existam"""
    conexao = criar_conexao()
    cursor = conexao.cursor()
    
    # 1. Tabela de usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) UNIQUE NOT NULL,
            senha VARCHAR(255) NOT NULL
        );
    """)
    
    # 2. Tabela de ciclos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ciclo_menstrual (
            id SERIAL PRIMARY KEY,
            usuario_nome VARCHAR(100) NOT NULL,
            ultima_menstruacao DATE NOT NULL,
            duracao_ciclo INTEGER DEFAULT 28
        );
    """)
    
    # 3. Tabela de contatos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contatos_emergencia (
            id SERIAL PRIMARY KEY,
            usuario_nome VARCHAR(100) NOT NULL,
            tel_msg VARCHAR(20),
            tel_video VARCHAR(20),
            tel_ligar VARCHAR(20)
        );
    """)
    
    # 4. Tabela de dicas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dicas_ciclo (
            id SERIAL PRIMARY KEY,
            fase VARCHAR(50) UNIQUE NOT NULL,
            exercicio TEXT,
            alimentacao TEXT
        );
    """)
    
    # Inserir dicas padrão se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM dicas_ciclo;")
    if cursor.fetchone()[0] == 0:
        dicas = [
            ("Menstrual", "Alongamentos leves e ioga.", "Alimentos ricos em ferro e chás mornos."),
            ("Folicular", "Exercícios de força e cardio moderado.", "Carboidratos complexos e vegetais verdes."),
            ("Ovulatória", "Treinos de alta intensidade (HIIT).", "Antioxidantes e gorduras saudáveis."),
            ("Lútea", "Pilates ou caminhadas leves.", "Magnésio (chocolate amargo) e reduzir sal.")
        ]
        for fase, ex, al in dicas:
            cursor.execute("INSERT INTO dicas_ciclo (fase, exercicio, alimentacao) VALUES (%s, %s, %s);", (fase, ex, al))

    conexao.commit()
    cursor.close()
    conexao.close()
    print("✅ Banco de dados inicializado e atualizado com sucesso!")
