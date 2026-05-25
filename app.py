from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from conexao import criar_conexao
from datetime import datetime, timedelta

app = Flask(__name__)

app.secret_key = 'app_mulheres_secret'


# Página inicial
@app.route('/')
def home():
    return render_template('index.html')


# Página login
@app.route('/login')
def login():
    return render_template('login.html')


# Página cadastro
@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')


# Dashboard
@app.route('/dashboard')
def dashboard():

    if 'usuario' not in session:
        return redirect('/login')

    return render_template('dashboard.html')


# Página exercícios
@app.route('/exercicios')
def exercicios():

    if 'usuario' not in session:
        return redirect('/login')

    conexao = criar_conexao()
    cursor = conexao.cursor()

    sql = "SELECT * FROM exercicios"

    cursor.execute(sql)

    lista_exercicios = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template(
        'exercicios.html',
        exercicios=lista_exercicios
    )


# Página saúde feminina
@app.route('/saude')
def saude():

    if 'usuario' not in session:
        return redirect('/login')

    conexao = criar_conexao()
    cursor = conexao.cursor()

    sql = """
    SELECT data_menstruacao
    FROM saude_feminina
    ORDER BY id DESC
    LIMIT 1
    """

    cursor.execute(sql)

    resultado = cursor.fetchone()

    cursor.close()
    conexao.close()

    proxima_menstruacao = None
    periodo_fertil = None

    if resultado:

        data_ultima = resultado[0]

        # Próxima menstruação
        proxima = data_ultima + timedelta(days=28)

        # Período fértil
        fertil_inicio = data_ultima + timedelta(days=11)
        fertil_fim = data_ultima + timedelta(days=17)

        proxima_menstruacao = proxima.strftime('%d/%m/%Y')

        periodo_fertil = (
            fertil_inicio.strftime('%d/%m/%Y')
            + ' até ' +
            fertil_fim.strftime('%d/%m/%Y')
        )

    return render_template(
        'saude.html',
        proxima_menstruacao=proxima_menstruacao,
        periodo_fertil=periodo_fertil
    )


# Página segurança
@app.route('/seguranca')
def seguranca():

    if 'usuario' not in session:
        return redirect('/login')

    return render_template('seguranca.html')


# Cadastro usuária
@app.route('/salvar_usuario', methods=['POST'])
def salvar_usuario():

    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']

    senha_criptografada = generate_password_hash(senha)

    conexao = criar_conexao()
    cursor = conexao.cursor()

    sql = """
    INSERT INTO usuarios
    (nome, email, senha)
    VALUES (%s, %s, %s)
    """

    valores = (nome, email, senha_criptografada)

    cursor.execute(sql, valores)

    conexao.commit()

    cursor.close()
    conexao.close()

    return "Usuária cadastrada com sucesso 🚀"


# Login
@app.route('/autenticar', methods=['POST'])
def autenticar():

    email = request.form['email']
    senha = request.form['senha']

    conexao = criar_conexao()
    cursor = conexao.cursor()

    sql = """
    SELECT * FROM usuarios
    WHERE email = %s
    """

    valores = (email,)

    cursor.execute(sql, valores)

    usuario = cursor.fetchone()

    cursor.close()
    conexao.close()

    if usuario:

        senha_banco = usuario[3]

        if check_password_hash(senha_banco, senha):

            session['usuario'] = email

            return redirect('/dashboard')

    return "Email ou senha inválidos"


# Logout
@app.route('/logout')
def logout():

    session.pop('usuario', None)

    return redirect('/login')


# Salvar saúde feminina
@app.route('/salvar_saude', methods=['POST'])
def salvar_saude():

    if 'usuario' not in session:
        return redirect('/login')

    data_menstruacao = request.form['data_menstruacao']
    sintomas = request.form['sintomas']

    conexao = criar_conexao()
    cursor = conexao.cursor()

    sql = """
    INSERT INTO saude_feminina
    (data_menstruacao, sintomas)
    VALUES (%s, %s)
    """

    valores = (data_menstruacao, sintomas)

    cursor.execute(sql, valores)

    conexao.commit()

    cursor.close()
    conexao.close()

    return redirect('/saude')


# Salvar exercício
@app.route('/salvar_exercicio', methods=['POST'])
def salvar_exercicio():

    if 'usuario' not in session:
        return redirect('/login')

    nome_exercicio = request.form['nome_exercicio']
    repeticoes = request.form['repeticoes']
    observacoes = request.form['observacoes']

    conexao = criar_conexao()
    cursor = conexao.cursor()

    sql = """
    INSERT INTO exercicios
    (nome_exercicio, repeticoes, observacoes)
    VALUES (%s, %s, %s)
    """

    valores = (
        nome_exercicio,
        repeticoes,
        observacoes
    )

    cursor.execute(sql, valores)

    conexao.commit()

    cursor.close()
    conexao.close()

    return redirect('/exercicios')





    import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)