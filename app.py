from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "elaviva_secret_key_2026"

# Configuração de conexão com o MySQL (Pronto para XAMPP e preparado para Nuvem/Render)
def obter_conexao():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "app_mulheres"),
        port=int(os.getenv("DB_PORT", 3306))
    )

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

        conexao = obter_conexao()
        cursor = conexao.cursor()
        
        # Busca o usuário no banco de dados
        cursor.execute("SELECT nome, senha FROM usuarios WHERE nome = %s LIMIT 1", (usuario_input,))
        resultado = cursor.fetchone()
        
        cursor.close()
        conexao.close()

        # Verifica se o usuário existe e se a senha criptografada bate
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

        # Criptografa a senha antes de salvar no banco de dados
        senha_criptografada = generate_password_hash(nova_senha)

        try:
            conexao = obter_conexao()
            cursor = conexao.cursor()
            
            # Insere o novo usuário na tabela
            sql = "INSERT INTO usuarios (nome, senha) VALUES (%s, %s)"
            cursor.execute(sql, (novo_usuario, senha_criptografada))
            conexao.commit()
            
            cursor.close()
            conexao.close()
            
            # Loga automaticamente após o cadastro bem-sucedido
            session["usuario"] = novo_usuario
            return redirect(url_for("dashboard"))
            
        except mysql.connector.Error as err:
            flash("Este nome de usuário já está cadastrado!", "warning")
            return redirect(url_for("index"))
            
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("index"))
    
    usuario = session["usuario"]
    conexao = obter_conexao()
    cursor = conexao.cursor(dictionary=True)
    
    # 1. Busca os dados do ciclo da usuária
    sql_busca = """
        SELECT ultima_menstruacao, duracao_ciclo 
        FROM ciclo_menstrual 
        WHERE usuario_nome = %s 
        ORDER BY id DESC LIMIT 1
    """
    cursor.execute(sql_busca, (usuario,))
    resultado = cursor.fetchone()

    fase_slug = "Folicular" # Padrão caso não haja dados
    dica = None

    if resultado:
        val_data = resultado["ultima_menstruacao"]
        if hasattr(val_data, "strftime"):
            if not isinstance(val_data, datetime):
                data_inicio = datetime.combine(val_data, datetime.min.time())
            else:
                data_inicio = val_data
        else:
            data_inicio = datetime.strptime(str(val_data), "%Y-%m-%d")

        duracao_ciclo = resultado["duracao_ciclo"] or 28
        hoje = datetime.now()
        
        # Calcula o dia do ciclo atual
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

    # 2. Busca a dica base no banco de dados para a fase identificada
    cursor.execute("SELECT exercicio, alimentacao FROM dicas_ciclo WHERE fase = %s LIMIT 1", (fase_slug,))
    dica = cursor.fetchone()

    cursor.close()
    conexao.close()

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

# CENTRAL DE EMERGÊNCIA E CONTATOS (Disparada pelo gesto oculto do Front-end)
@app.route("/denuncia", methods=["GET", "POST"])
def denuncia():
    if "usuario" not in session:
        return redirect(url_for("index"))

    usuario = session["usuario"]
    conexao = obter_conexao()
    cursor = conexao.cursor(dictionary=True)

    if request.method == "POST":
        nome_video = request.form.get("nome_video", "").strip()
        tel_video = request.form.get("tel_video", "").strip()
        nome_msg = request.form.get("nome_msg", "").strip()
        tel_msg = request.form.get("tel_msg", "").strip()
        nome_ligar = request.form.get("nome_ligar", "Polícia Militar").strip()
        tel_ligar = request.form.get("tel_ligar", "190").strip()

        # Verifica se já existem contatos gravados para a usuária
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

    # Busca os contatos cadastrados para carregar na página
    cursor.execute("SELECT * FROM contatos_emergencia WHERE usuario_nome = %s LIMIT 1", (usuario,))
    contatos = cursor.fetchone()

    cursor.close()
    conexao.close()

    return render_template("denuncia.html", contatos=contatos)

@app.route("/disparar_emergencia", methods=["POST"])
def disparar_emergencia():
    if "usuario" in session:
        try:
            conexao = obter_conexao()
            cursor = conexao.cursor()
            
            cursor.execute("SELECT id FROM usuarios WHERE nome = %s LIMIT 1", (session["usuario"],))
            user_data = cursor.fetchone()
            usuario_id = user_data[0] if user_data else 1
            
            sql = "INSERT INTO alertas_emergencia (usuario_id, data_hora) VALUES (%s, %s)"
            cursor.execute(sql, (usuario_id, datetime.now()))
            conexao.commit()
            
            cursor.close()
            conexao.close()
            return {"status": "sucesso"}, 200
        except Exception as e:
            return {"status": "erro", "detalhes": str(e)}, 500
    return {"status": "nao_autorizado"}, 401

@app.route("/caminhada")
def caminhada():
    if "usuario" not in session:
        return redirect(url_for("index"))
    return render_template("caminhada.html")

@app.route("/registrar_alerta", methods=["POST"])
def registrar_alerta():
    if "usuario" not in session:
        return redirect(url_for("index"))
        
    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")
    tipo_alerta = request.form.get("tipo_alerta")
    descricao = request.form.get("descricao", "").strip()
    
    if not latitude or not longitude or not tipo_alerta:
        flash("Dados de localização ou categoria ausentes. Tente novamente.", "danger")
        return redirect(url_for("caminhada"))
        
    try:
        conexao = obter_conexao()
        cursor = conexao.cursor()
        
        cursor.execute("SELECT id FROM usuarios WHERE nome = %s LIMIT 1", (session["usuario"],))
        user_data = cursor.fetchone()
        usuario_id = user_data[0] if user_data else None
        
        sql = """
            INSERT INTO alertas_caminhada (usuario_id, latitude, longitude, tipo_alerta, descricao) 
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (usuario_id, latitude, longitude, tipo_alerta, descricao))
        conexao.commit()
        
        cursor.close()
        conexao.close()
        
        flash("Alerta registrado com sucesso! Continue seu trajeto com atenção.", "success")
    except Exception as e:
        flash(f"Erro ao salvar alerta no sistema: {str(e)}", "danger")
        
    return redirect(url_for("caminhada"))

@app.route("/ciclo", methods=["GET", "POST"])
def ciclo():
    if "usuario" not in session:
        return redirect(url_for("index"))

    fase_atual, previsao = "", ""
    treino_hoje = []
    cronograma_mes = []

    usuario = session["usuario"]
    conexao = obter_conexao()
    cursor = conexao.cursor()

    if request.method == "POST":
        data_input = request.form["ultima_menstruacao"]
        duracao = int(request.form["duracao_ciclo"])

        sql = "INSERT INTO ciclo_menstrual (usuario_nome, ultima_menstruacao, duracao_ciclo) VALUES(%s, %s, %s)"
        cursor.execute(sql, (usuario, data_input, duracao))
        conexao.commit()
    
    sql_busca = """
        SELECT ultima_menstruacao, duracao_ciclo 
        FROM ciclo_menstrual 
        WHERE usuario_nome = %s 
        ORDER BY id DESC LIMIT 1
    """
    cursor.execute(sql_busca, (usuario,))
    resultado = cursor.fetchone()
    
    cursor.close()
    conexao.close()

    if resultado:
        if hasattr(resultado[0], "strftime"):
            if not isinstance(resultado[0], datetime):
                data_inicio_ciclo = datetime.combine(resultado[0], datetime.min.time())
            else:
                data_inicio_ciclo = resultado[0]
        else:
            data_inicio_ciclo = datetime.strptime(str(resultado[0]), "%Y-%m-%d")
            
        duracao_ciclo = resultado[1]
        hoje = datetime.now()
        
        for i in range(duracao_ciclo):
            data_dia = data_inicio_ciclo + timedelta(days=i)
            dia_do_ciclo = i + 1
            
            if dia_do_ciclo <= 5:
                fase_nome = "🔴 Menstrual"
                foco_treino = "Treino Regenerativo (Yoga, Alongamento ou Caminhada Leve)"
                dica = "Foque no descanso e no alívio de cólicas."
            elif dia_do_ciclo <= 13:
                fase_nome = "🌸 Folicular"
                foco_treino = "Força e Hipertrofia (Musculação, Funcional ou Dança)"
                dica = "Sua energia está subindo! Bom momento para progredir cargas."
            elif dia_do_ciclo <= 16:
                fase_nome = "🚀 Ovulatória"
                foco_treino = "Alta Intensidade (HIIT, Corrida ou Crossfit)"
                dica = "Pico de força e energia. Dê o seu máximo!"
            else:
                fase_nome = "🌙 Lútea"
                foco_treino = "Resistência Moderada (Pilates, Bike ou Localizada)"
                dica = "A energia começa a cair. Reduza o ritmo se necessário."

            dados_dia = {
                "data": data_dia.strftime("%d/%m (%a)"),
                "dia_ciclo": dia_do_ciclo,
                "fase": fase_nome,
                "treino": foco_treino,
                "dica": dica,
                "eh_hoje": data_dia.date() == hoje.date()
            }
            cronograma_mes.append(dados_dia)

            if data_dia.date() == hoje.date():
                fase_atual = fase_nome
                previsao = f"Você está no dia {dia_do_ciclo} do seu ciclo de {duracao_ciclo} dias."
                if dia_do_ciclo <= 5:
                    treino_hoje = ["Yoga focada em alívio pélvico", "Caminhada leve na esteira", "Alongamento passivo"]
                elif dia_do_ciclo <= 13:
                    treino_hoje = ["Musculação (Foco em Inferiores)", "Treino Funcional de Força", "Aula de Dança / Ritmos"]
                elif dia_do_ciclo <= 16:
                    treino_hoje = ["Treino HIIT de Alta Intensidade", "Corrida de Velocidade", "Circuito de Explosão Cárdiomuscular"]
                else:
                    treino_hoje = ["Pilates de Solo", "Ciclismo / Bike Indoor", "Musculação Moderada (Membros Superiores)"]

    return render_template(
        "ciclo.html", 
        fase=fase_atual, 
        previsao=previsao, 
        treino_hoje=treino_hoje, 
        cronograma=cronograma_mes
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)