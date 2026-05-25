import mysql.connector

def criar_conexao():

    conexao = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='app_mulheres'
    )

    return conexao