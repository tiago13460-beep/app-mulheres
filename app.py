from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
from conexao import criar_conexao, inicializar_banco

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "elaviva_secret_key_2026")

# Inicializa as tabelas estruturais automaticamente no PostgreSQL do Render
inicializar_banco()

def calcular_fase_e_dica(usuario):
    """Função utilitária para calcular a fase e buscar a dica no banco de dados"""
    conexao = criar_conexao()
    
    from psycopg2.extras import RealDictCursor
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    
    sql_busca = """
        SELECT ultima_menstruacao, duracao_ciclo 
        FROM ciclo_menstrual 
        WHERE usuario_nome = %s 
        ORDER BY id DESC LIMIT 1
    """
    cursor.execute(sql_busca, (usuario,))
    resultado = cursor.fetchone()

    # Retorna None caso o usuário ainda não tenha registrado nenhum ciclo
    if not resultado:
        cursor.close()
        conexao.close()
        return None, None

    val_data = resultado["ultima_menstruacao"]
    if hasattr(val_data, "strftime"):
        data_inicio = datetime.combine(val_data, datetime.min.time()) if not isinstance(val_data, datetime) else val_data
    else:
        data_inicio = datetime.strptime(str(val_data), "%Y-%m-%d")

    duracao_ciclo = resultado["duracao_ciclo"] or 28
    hoje = datetime.now()
    
    dias_decorridos = (hoje.date() - data_inicio.date()).days
    dia_do_ciclo = (dias_decorridos % duracao_ciclo) + 1

    if dia_do_ciclo <= 5:
        fase_slug = "Menstrual"
    elif dia_do_ciclo <= 13:
        fase_slug = "Folicular"
    elif dia_do_ciclo <= 16:
        fase_slug = "Ovulatória"
    else:
        fase_slug = "Lútea"

    cursor.execute("SELECT exercicio, alimentacao FROM dicas_ciclo WHERE fase = %s LIMIT 1", (fase_slug,))
    dica = cursor.fetchone()

    cursor.close()
    conexao.close()
    
    return fase_slug, dica

@app.route("/")
def index():
    if "usuario" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login_page():
    if request.method == "POST":
        usuario_input = request.form["usuario"].strip()
        senha_input = request.form["senha"].strip()

        conexao = criar_conexao()
        cursor = conexao.cursor()
        
        cursor.execute("SELECT nome, senha FROM usuarios WHERE nome = %s LIMIT 1", (usuario_input,))
        resultado = cursor.fetchone()
        
        cursor.close()
        conexao.close()

        if resultado and check_password_hash(resultado[1], senha_input):
            session["usuario"] = resultado[0]
            return redirect(url_for("dashboard"))
        else:
            flash("Usuário ou senha incorretos!", "danger")
            return redirect(url_for("index"))
            
    return redirect(url_for("index"))

@app.route("/cadastro", methods=["POST"])
def cadastro_page():
    if request.method == "POST":
        novo_usuario = request.form["usuario_cadastro"].strip()
        nova_senha = request.form["senha_cadastro"].strip()
        senha_criptografada = generate_password_hash(nova_senha)

        try:
            conexao = criar_conexao()
            cursor = conexao.cursor()
            
            cursor.execute("INSERT INTO usuarios (nome, senha) VALUES (%s, %s)", (novo_usuario, senha_criptografada))
            conexao.commit()
            
            cursor.close()
            conexao.close()
            
            session["usuario"] = novo_usuario
            return redirect(url_for("dashboard"))
            
        except Exception:
            flash("Este nome de usuário já está cadastrado!", "warning")
            return redirect(url_for("index"))
            
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("index"))
    
    usuario = session["usuario"]
    fase_slug, dica = calcular_fase_e_dica(usuario)

    return render_template(
        "dashboard.html", 
        usuario=usuario, 
        fase_atual=fase_slug, 
        dica=dica
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/seguranca")
def seguranca():
    if "usuario" not in session:
        return redirect(url_for("index"))
    return render_template("seguranca.html")

@app.route("/ciclo", methods=["GET", "POST"])
def ciclo():
    if "usuario" not in session:
        return redirect(url_for("index"))
        
    usuario = session["usuario"]

    if request.method == "POST":
        ultima_menstruacao = request.form.get("ultima_menstruacao")
        duracao_ciclo = request.form.get("duracao_ciclo", 28)

        if not ultima_menstruacao:
            flash("Por favor, selecione a data da sua última menstruação.", "warning")
            return redirect(url_for("ciclo"))

        try:
            conexao = criar_conexao()
            cursor = conexao.cursor()
            
            sql = "INSERT INTO ciclo_menstrual (usuario_nome, ultima_menstruacao, duracao_ciclo) VALUES (%s, %s, %s)"
            cursor.execute(sql, (usuario, ultima_menstruacao, int(duracao_ciclo)))
            conexao.commit()
            
            cursor.close()
            conexao.close()
            
            flash("Ciclo menstrual atualizado com sucesso!", "success")
            # Redireciona para permanecer na tela do ciclo e ver as recomendações atualizadas
            return redirect(url_for("ciclo"))
            
        except Exception as e:
            print(f"Erro ao salvar ciclo: {e}")
            flash("Ocorreu um erro ao salvar o seu ciclo. Tente novamente.", "danger")
            return redirect(url_for("ciclo"))

    fase_slug, dica = calcular_fase_e_dica(usuario)
    return render_template("ciclo.html", fase_atual=fase_slug, dica=dica)

@app.route("/denuncia", methods=["GET", "POST"])
def denuncia():
    if "usuario" not in session:
        return redirect(url_for("index"))

    usuario = session["usuario"]
    conexao = criar_conexao()
    
    from psycopg2.extras import RealDictCursor
    cursor = conexao.cursor(cursor_factory=RealDictCursor)

    if request.method == "POST":
        nome_video = request.form.get("nome_video", "").strip()
        tel_video = request.form.get("tel_video", "").strip()
        nome_msg = request.form.get("nome_msg", "").strip()
        tel_msg = request.form.get("tel_msg", "").strip()
        nome_ligar = request.form.get("nome_ligar", "Polícia Militar").strip()
        tel_ligar = request.form.get("tel_ligar", "190").strip()

        cursor.execute("SELECT id FROM contatos_emergencia WHERE usuario_nome = %s LIMIT 1", (usuario,))
        existe = cursor.fetchone()

        if existe:
            sql = """
                UPDATE contatos_emergencia 
                SET nome_video=%s, tel_video=%s, nome_msg=%s, tel_msg=%s, nome_ligar=%s, tel_ligar=%s 
                WHERE usuario_nome=%s
            """
            cursor.execute(sql, (nome_video, tel_video, nome_msg, tel_msg, nome_ligar, tel_ligar, usuario))
        else:
            sql = """
                INSERT INTO contatos_emergencia (usuario_nome, nome_video, tel_video, nome_msg, tel_msg, nome_ligar, tel_ligar)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (usuario, nome_video, tel_video, nome_msg, tel_msg, nome_ligar, tel_ligar))

        conexao.commit()
        flash("Contatos de emergência atualizados com sucesso!", "success")

    cursor.execute("SELECT * FROM contatos_emergencia WHERE usuario_nome = %s LIMIT 1", (usuario,))
    contatos = cursor.fetchone()

    cursor.close()
    conexao.close()
    return render_template("denuncia.html", contatos=contatos)

@app.route("/disparar_emergencia", methods=["POST"])
def disparar_emergencia():
    if "usuario" in session:
        try:
            conexao = criar_conexao()
            cursor = conexao.cursor()
            
            cursor.execute("SELECT id FROM usuarios WHERE nome = %s LIMIT 1", (session["usuario"],))
            user_data = cursor.fetchone()
            usuario_id = user_data if user_data else 1
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alertas_emergencia (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER,
                    data_hora TIMESTAMP
                );
            """)
            
            sql = "INSERT INTO alertas_emergencia (usuario_id, data_hora) VALUES (%s, %s)"
            cursor.execute(sql, (usuario_id, datetime.now()))
            conexao.commit()
            
            cursor.close()
            conexao.close()
            return jsonify({"status": "sucesso"}), 200
        except Exception:
            return jsonify({"status": "erro"}), 500
    return jsonify({"status": "nao_autorizado"}), 401

@app.route("/saude")
def saude():
    if "usuario" not in session:
        return redirect(url_for("index"))
    return render_template("saude.html")

@app.route("/exercicios")
def exercicios():
    if "usuario" not in session:
        return redirect(url_for("index"))
    return render_template("exercicios.html")

@app.route("/caminhada")
def caminhada():
    if "usuario" not in session:
        return redirect(url_for("index"))
    return render_template("caminhada.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
