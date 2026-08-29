from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os

app = Flask(__name__)
# Certifique-se de configurar a SECRET_KEY para as mensagens flash funcionarem
app.secret_key = os.getenv("SECRET_KEY", "chave_secreta_padrao")

def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

@app.route('/')
def index():
    return redirect(url_for('ciclo'))

@app.route('/ciclo', methods=['GET', 'POST'])
def ciclo():
    # 1. Verificar se o usuário está logado (Ajuste a chave 'usuario_id' conforme o seu sistema de login)
    usuario_id = session.get('usuario_id')
    
    # Se você ainda não implementou login, pode descomentar a linha abaixo para testes:
    # usuario_id = 1 

    if not usuario_id:
        flash("Por favor, faça login para acessar esta página.", "warning")
        return redirect(url_for('login'))

    ciclo_calculado = None

    if request.method == 'POST':
        try:
            data_str = request.form.get('ultima_menstruacao')
            duracao_ciclo = int(request.form.get('duracao_ciclo', 28))
            duracao_menstruacao = int(request.form.get('duracao_menstruacao', 5))

            if data_str:
                data_inicio = datetime.strptime(data_str, '%Y-%m-%d').date()

                # Salva ou atualiza os dados no banco
                conn = get_db_connection()
                cur = conn.cursor()
                
                cur.execute("""
                    INSERT INTO ciclo (usuario_id, ultima_menstruacao, duracao_ciclo, duracao_menstruacao)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (usuario_id) 
                    DO UPDATE SET 
                        ultima_menstruacao = EXCLUDED.ultima_menstruacao,
                        duracao_ciclo = EXCLUDED.duracao_ciclo,
                        duracao_menstruacao = EXCLUDED.duracao_menstruacao;
                """, (usuario_id, data_inicio, duracao_ciclo, duracao_menstruacao))
                
                conn.commit()
                cur.close()
                conn.close()

                flash("Dados do ciclo salvos e calculados com sucesso!", "success")

        except Exception as e:
            print(f"Erro ao salvar ciclo: {e}")
            flash("Ocorreu um erro ao processar o formulário. Verifique os dados digitados.", "danger")

    # Busca os dados no banco de dados para renderizar a página
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM ciclo WHERE usuario_id = %s;", (usuario_id,))
        dados = cur.fetchone()
        cur.close()
        conn.close()

        if dados:
            data_inicio = dados['ultima_menstruacao']
            
            # Converte para objeto date se tiver vindo como string/datetime
            if isinstance(data_inicio, str):
                data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            elif isinstance(data_inicio, datetime):
                data_inicio = data_inicio.date()

            duracao_ciclo = int(dados['duracao_ciclo'])
            duracao_menstruacao = int(dados['duracao_menstruacao'])

            # Cálculos das datas do ciclo
            fim_menstruacao = data_inicio + timedelta(days=duracao_menstruacao - 1)
            proxima_menstruacao = data_inicio + timedelta(days=duracao_ciclo)
            dia_ovulacao = proxima_menstruacao - timedelta(days=14)
            inicio_fertil = dia_ovulacao - timedelta(days=5)
            fim_fertil = dia_ovulacao + timedelta(days=1)

            ciclo_calculado = {
                'ultima_menstruacao': data_inicio.strftime('%d/%m/%Y'),
                'fim_menstruacao': fim_menstruacao.strftime('%d/%m/%Y'),
                'proxima_menstruacao': proxima_menstruacao.strftime('%d/%m/%Y'),
                'inicio_fertil': inicio_fertil.strftime('%d/%m/%Y'),
                'fim_fertil': fim_fertil.strftime('%d/%m/%Y'),
                'dia_ovulacao': dia_ovulacao.strftime('%d/%m/%Y'),
                'duracao_ciclo': duracao_ciclo,
                'duracao_menstruacao': duracao_menstruacao,
                'raw_date': data_inicio.strftime('%Y-%m-%d')
            }

    except Exception as e:
        print(f"Erro ao buscar ciclo: {e}")
        flash("Erro ao carregar os dados do ciclo do banco de dados.", "danger")

    return render_template('ciclo.html', ciclo=ciclo_calculado)

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
