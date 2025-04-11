from flask import Flask, render_template, request, redirect, session, url_for
from flask_cors import CORS  # 👈 Adicionado aqui
import psycopg2
import pandas as pd
from datetime import datetime

app = Flask(__name__)
CORS(app)  # 👈 Habilita CORS para todas as rotas
app.secret_key = 'sua_chave_secreta'  # Altere para algo seguro

# --- Conexão com o banco de forma otimizada ---
def get_db_connection(user, password):
    return psycopg2.connect(
        host="localhost",
        database="robo_prex",
        user=user,
        password=password
    )

# --- Funções auxiliares ---
def autenticar_usuario(email, senha):
    conn = get_db_connection("robo_admin", "cursirenan79")
    cur = conn.cursor()
    cur.execute("SELECT nome FROM usuarios WHERE email = %s AND senha = %s", (email, senha))
    result = cur.fetchone()
    cur.close()
    return result[0] if result else None

def carregar_processos():
    conn = get_db_connection("robo_prex", "cursirenan79")
    df = pd.read_sql("SELECT numero_processo, link FROM processos_encontrados ORDER BY data_encontrado DESC LIMIT 100", conn)
    return df

@app.route('/')
def index():
    if 'primeiro_login' not in session:
        session['primeiro_login'] = True
    if 'usuario_logado' not in session:
        session['usuario_logado'] = None

    if session['primeiro_login']:
        return render_template('boas_vindas.html')

    if not session['usuario_logado']:
        return redirect(url_for('login'))

    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.is_json:  # 👈 Isso permite aceitar JSON vindo do React
            dados = request.get_json()
            email = dados.get('email')
            senha = dados.get('senha')
        else:
            email = request.form['email']
            senha = request.form['senha']

        usuario = autenticar_usuario(email, senha)
        if usuario:
            session['usuario_logado'] = usuario
            if request.is_json:
                return {'nome': usuario}, 200  # 👈 Retorna JSON para o React
            return redirect(url_for('dashboard'))
        else:
            if request.is_json:
                return {'message': 'Credenciais inválidas'}, 401
            return render_template('login.html', erro='Credenciais inválidas.')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('usuario_logado'):
        return redirect(url_for('login'))

    processos_df = carregar_processos()
    processos = processos_df.to_dict(orient='records')
    return render_template('dashboard.html', usuario=session['usuario_logado'], processos=processos)

@app.route('/ir_login', methods=['POST'])
def ir_login():
    session['primeiro_login'] = False
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

