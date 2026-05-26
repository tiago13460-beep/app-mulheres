from flask import Flask, render_template, request, redirect, session
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "segredo_app_mulheres"


# =========================================
# CONEXÃO MYSQL
# =========================================
def conectar_bd():
    conexao = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="app_mulheres"
    )
    return conexao


# =========================================
# PÁGINA INICIAL
# =========================================
@app.route("/")
def index():
    return render_template("index.html")


# =========================================
# CADASTRO
# =========================================
@app.route("/cadastro")
def cadastro():
    return render_template("cadastro.html")


@app.route("/salvar_usuario", methods=["POST"])
def salvar_usuario():

    nome = request.form["nome"]
    email = request.form["email"]
    senha = request.form["senha"]

    conexao = conectar_bd()

    cursor = conexao.cursor()

    sql = """
    INSERT INTO usuarios (nome, email, senha)
    VALUES (%s, %s, %s)
    """

    valores = (nome, email, senha)

    cursor.execute(sql, valores)

    conexao.commit()

    cursor.close()
    conexao.close()

    return redirect("/login")


# =========================================
# LOGIN
# =========================================
@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/autenticar", methods=["POST"])
def autenticar():

    email = request.form["email"]
    senha = request.form["senha"]

    conexao = conectar_bd()

    cursor = conexao.cursor(dictionary=True)

    sql = """
    SELECT * FROM usuarios
    WHERE email = %s AND senha = %s
    """

    valores = (email, senha)

    cursor.execute(sql, valores)

    usuario = cursor.fetchone()

    cursor.close()
    conexao.close()

    if usuario:

        session["usuario"] = usuario["nome"]

        return redirect("/dashboard")

    else:
        return "Email ou senha inválidos"


# =========================================
# DASHBOARD
# =========================================
@app.route("/dashboard")
def dashboard():

    if "usuario" not in session:
        return redirect("/login")

    return render_template(
        "dashboard.html",
        usuario=session["usuario"]
    )


# =========================================
# LOGOUT
# =========================================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================================
# EXERCÍCIOS
# =========================================
@app.route("/exercicios")
def exercicios():

    if "usuario" not in session:
        return redirect("/login")

    return render_template("exercicios.html")


# =========================================
# SAÚDE FEMININA
# =========================================
@app.route("/saude")
def saude():

    if "usuario" not in session:
        return redirect("/login")

    return render_template("saude.html")


# =========================================
# SEGURANÇA
# =========================================
@app.route("/seguranca")
def seguranca():

    if "usuario" not in session:
        return redirect("/login")

    return render_template("seguranca.html")


# =========================================
# CICLO MENSTRUAL
# =========================================
@app.route("/ciclo")
def ciclo():

    if "usuario" not in session:
        return redirect("/login")

    return render_template("ciclo.html")


# =========================================
# SALVAR CICLO
# =========================================
@app.route("/salvar_ciclo", methods=["POST"])
def salvar_ciclo():

    data_inicio = request.form["data_inicio"]
    duracao = request.form["duracao"]

    conexao = conectar_bd()

    cursor = conexao.cursor()

    sql = """
    INSERT INTO ciclo_menstrual
    (data_inicio, duracao)
    VALUES (%s, %s)
    """

    valores = (data_inicio, duracao)

    cursor.execute(sql, valores)

    conexao.commit()

    cursor.close()
    conexao.close()

    return redirect("/ciclo")


# =========================================
# INICIAR FLASK
# =========================================
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )