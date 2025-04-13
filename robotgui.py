from flask import Flask, render_template, request, redirect, session, url_for, jsonify, send_file
from flask_cors import CORS
import psycopg2
import pandas as pd
from datetime import datetime
import io

app = Flask(__name__)
CORS(app)
app.secret_key = 'nigga'  # Altere para algo seguro

# --- Conexão com o banco ---
def get_db_connection(user, password):
    return psycopg2.connect("postgresql://postgres:hoqTncYzOHdQShgdVDdEPqJIOJluwpKZ@yamabiko.proxy.rlwy.net:56223/railway")

# --- Autenticação ---
def autenticar_usuario(email, senha):
    conn = get_db_connection("robo_admin", "cursirenan79")
    cur = conn.cursor()
    cur.execute("SELECT nome FROM usuarios WHERE email = %s AND senha = %s", (email, senha))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

# --- Carregar processos encontrados ---
def carregar_processos():
    conn = get_db_connection("robo_admin", "cursirenan79")
    df_teste = pd.read_sql(
        "SELECT processo FROM processos_encontrados WHERE data_encontrado IS NULL AND link IS NULL ORDER BY processo",
        conn
    )
    df_futuros = pd.read_sql(
        "SELECT processo, link, data_encontrado FROM processos_encontrados WHERE data_encontrado IS NOT NULL ORDER BY data_encontrado DESC",
        conn
    )
    conn.close()
    return df_teste, df_futuros

# --- Rotas de frontend (HTML) ---
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
        if request.is_json:
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
                return jsonify({'nome': usuario}), 200
            return redirect(url_for('dashboard'))
        else:
            if request.is_json:
                return jsonify({'message': 'Credenciais inválidas'}), 401
            return render_template('login.html', erro='Credenciais inválidas.')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('usuario_logado'):
        return redirect(url_for('login'))

    df_teste, df_futuros = carregar_processos()

    processos_teste = df_teste.to_dict(orient='records')
    processos_futuros = df_futuros.to_dict(orient='records')

    return render_template(
        'dashboard.html',
        usuario=session['usuario_logado'],
        processos_teste=processos_teste,
        processos_futuros=processos_futuros
    )

@app.route('/ir_login', methods=['POST'])
def ir_login():
    session['primeiro_login'] = False
    return redirect(url_for('login'))

# --- Rotas da API (para frontend React) ---
@app.route('/api/login', methods=['POST'])
def api_login():
    dados = request.get_json()
    email = dados.get('email')
    senha = dados.get('senha')

    usuario = autenticar_usuario(email, senha)
    if usuario:
        return jsonify({'nome': usuario}), 200
    return jsonify({'message': 'Credenciais inválidas'}), 401

@app.route('/api/processos', methods=['GET'])
def api_processos():
    df_teste, df_futuros = carregar_processos()
    processos_teste = df_teste.to_dict(orient='records')
    processos_futuros = df_futuros.to_dict(orient='records')
    return jsonify({
        "fase_teste": processos_teste,
        "futuros": processos_futuros
    })

# --- NOVAS ROTAS: Página + Exportação de planilha ---

# Página para gerar as planilhas periódicas
@app.route('/gerar-planilhas-periodicas')
def gerar_planilhas_periodicas():
    if not session.get('usuario_logado'):
        return redirect(url_for('login'))

    return render_template('gerar_planilhas_periodicas.html')

# Rota para Baixar Planilha Diária
@app.route('/baixar-planilha-diaria')
def baixar_planilha_diaria():
    if not session.get('usuario_logado'):
        return redirect(url_for('login'))

    # Carregar processos encontrados
    _, df_futuros = carregar_processos()

    # Filtra os processos pela data de hoje
    hoje = datetime.today().strftime('%Y-%m-%d')
    df_diaria = df_futuros[df_futuros['data_encontrado'].str.startswith(hoje)]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_diaria.to_excel(writer, index=False, sheet_name='Planilha Diária')

    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name=f"Processos_Diarios_{hoje}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# Rota para Baixar Planilha Semanal
@app.route('/baixar-planilha-semanal')
def baixar_planilha_semanal():
    if not session.get('usuario_logado'):
        return redirect(url_for('login'))

    # Carregar processos encontrados
    _, df_futuros = carregar_processos()

    # Filtra os processos pela data da última semana
    hoje = datetime.today()
    semana_inicio = hoje - pd.Timedelta(days=7)
    df_semanal = df_futuros[df_futuros['data_encontrado'] >= semana_inicio.strftime('%Y-%m-%d')]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_semanal.to_excel(writer, index=False, sheet_name='Planilha Semanal')

    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name=f"Processos_Semanais_{hoje.strftime('%Y-%m-%d')}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# Rota para Baixar Planilha Mensal
@app.route('/baixar-planilha-mensal')
def baixar_planilha_mensal():
    if not session.get('usuario_logado'):
        return redirect(url_for('login'))

    # Carregar processos encontrados
    _, df_futuros = carregar_processos()

    # Filtra os processos pela data do mês atual
    hoje = datetime.today()
    inicio_mes = hoje.replace(day=1)
    df_mensal = df_futuros[df_futuros['data_encontrado'] >= inicio_mes.strftime('%Y-%m-%d')]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_mensal.to_excel(writer, index=False, sheet_name='Planilha Mensal')

    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name=f"Processos_Mensais_{hoje.strftime('%Y-%m-%d')}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

if __name__ == '__main__':
    app.run(debug=True)

