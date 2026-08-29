from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
import requests
from conexao import criar_conexao, inicializar_banco

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "elaviva_secret_key_2026")

# Garante a criação das tabelas na inicialização
inicializar_banco()

# Configurações da API de WhatsApp
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "https://sua-instancia-evolution.com")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "sua_instancia")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "sua_api_key_aqui")

def enviar_whatsapp_emergencia(numero_destino, lat, lng):
    if not numero_destino:
        return False
    numero_limpo = ''.join(filter(str.isdigit, str(numero_destino)))
    if not numero_limpo.startswith('55') and len(numero_limpo) <= 11:
        numero_limpo = f"55{numero_limpo}"

    if lat and lng:
        link_maps = f"https://google.com{lat},{lng}"
        texto_mensagem = f"🚨 *ALERTA DE EMERGÊNCIA - ELA VIVA* 🚨\n\nPreciso de ajuda urgente!\n\n📍 *Minha localização em tempo real:*\n{link_maps}"
    else:
        texto_mensagem = "🚨 *ALERTA DE EMERGÊNCIA - ELA VIVA* 🚨\n\nPreciso de ajuda urgente!\n(Localização GPS indisponível no momento)."

    endpoint = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    headers = {"Content-Type": "application/json", "apikey": EVOLUTION_API_KEY}
    payload = {
        "number": numero_limpo,
        "options": {"delay": 0, "presence": "composing", "linkPreview": True},
        "textMessage": {"text": texto_mensagem}
    }
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=8)
        return response.status_code in [200, 201]
    except Exception:
        return False

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

        # Ajustado para tuplas do psycopg2 de forma segura
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

    fase_slug = "Folicular"
    dica = None

    if resultado:
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

@app.route("/denuncia", methods=["GET", "POST"])
def denuncia():
    if "usuario" not in session:
        if request.is_json:
            return jsonify({"status": "nao_autorizado"}), 401
        return redirect(url_for("index"))

    usuario = session["usuario"]
    conexao = criar_conexao()
    
    from psycopg2.extras import RealDictCursor
    cursor = conexao.cursor(cursor_factory=RealDictCursor)

    if request.method == "POST" and (request.is_json or request.headers.get("Content-Type") == "application/json"):
        dados = request.get_json() or {}
        lat = dados.get("latitude")
        lng = dados.get("longitude")

        cursor.execute("SELECT tel_msg, tel_video, tel_ligar FROM contatos_emergencia WHERE usuario_nome = %s LIMIT 1", (usuario,))
        contato = cursor.fetchone()

        if contato:
            numero_alvo = contato.get("tel_msg") or contato.get("tel_video") or contato.get("tel_ligar")
            if numero_alvo:
                enviar_whatsapp_emergencia(numero_alvo, lat, lng)

        cursor.close()
        conexao.close()
        return jsonify({"status": "sucesso", "mensagem": "Alerta disparado!"}), 200
        
    return redirect(url_for("index"))
