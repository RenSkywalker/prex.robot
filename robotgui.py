from flask import Flask, render_template, request, redirect, session, url_for, jsonify, send_file
from flask_cors import CORS
from collections import Counter
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
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

    # Convertendo a coluna 'data_encontrado' para datetime e removendo valores NaT (não válidos)
    df_futuros['data_encontrado'] = pd.to_datetime(df_futuros['data_encontrado'], errors='coerce')

    # Agrupando os processos por data de encontro (formatada como 'dd/mm/yyyy')
    processos_futuros = df_futuros.dropna(subset=['data_encontrado']) \
                                    .groupby(df_futuros['data_encontrado'].dt.strftime('%d/%m/%Y'))['processo'] \
                                    .apply(list).to_dict()

    return render_template(
        'dashboard.html',
        usuario=session['usuario_logado'],
        processos_por_data=processos_por_data
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
@app.route('/fase-teste')
def fase_teste():
    if not session.get('usuario_logado'):
        return redirect(url_for('login'))

    _, df_futuros = carregar_processos()  # Pegando apenas os processos de teste
    processos = df_futuros.to_dict(orient='records')  # Convertendo os processos para formato adequado

    return render_template('fase_teste.html', usuario=session['usuario_logado'], processos=processos)

@app.route('/fase-teste/baixar')
def baixar_planilha_fase_teste():
    if not session.get('usuario_logado'):
        return redirect(url_for('login'))

    # Alterando a consulta para garantir que pegamos apenas os processos sem link para o download
    _, df_futuros = carregar_processos()  # Pegando apenas os processos de teste (sem link)
    df_teste_sem_link = df_futuros[df_futuros['link'].isnull()]  # Filtrando processos sem link

    output = io.BytesIO()

    # Gerando a planilha apenas com os processos sem link da fase de teste
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_teste_sem_link.to_excel(writer, index=False, sheet_name='FaseTeste')

    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="Processos_em_Fase_de_Teste_Sem_Link.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# Página para gerar as planilhas periódicas
@app.route('/gerar-planilhas-periodicas')
def gerar_planilhas_periodicas():
    if not session.get('usuario_logado'):
        return redirect(url_for('login'))

    return render_template('gerar_planilhas_periodicas.html', usuario=session['usuario_logado'])

# Rota para Baixar Planilha Diária
@app.route('/baixar-planilha-diaria')
def baixar_planilha_diaria():
    if not session.get('usuario_logado'):
        return redirect(url_for('login'))

    df_teste, df_futuros = carregar_processos()

    df_filtros = df_futuros[df_futuros['link'].notnull() & df_futuros['data_encontrado'].notnull()]

    hoje = datetime.today().strftime('%Y-%m-%d')
    df_diaria = df_filtros[df_filtros['data_encontrado'].astype(str).str.startswith(hoje)]

    if df_diaria.empty:
        df_diaria = pd.DataFrame(columns=['processo', 'data_encontrado', 'link'])

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
    
@app.route('/baixar-planilha-semanal')
def baixar_planilha_semanal():
    if not session.get('usuario_logado'):
        return redirect(url_for('login'))

    _, df_futuros = carregar_processos()
    df_filtros = df_futuros[df_futuros['link'].notnull() & df_futuros['data_encontrado'].notnull()]

    hoje = datetime.today()
    sete_dias_atras = hoje - timedelta(days=7)

    df_semanal = df_filtros[ 
        (df_filtros['data_encontrado'] >= sete_dias_atras) & 
        (df_filtros['data_encontrado'] <= hoje)
    ]

    if df_semanal.empty:
        df_semanal = pd.DataFrame(columns=['processo', 'data_encontrado', 'link'])

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

@app.route('/baixar-planilha-mensal')
def baixar_planilha_mensal():
    if not session.get('usuario_logado'):
        return redirect(url_for('login'))

    _, df_futuros = carregar_processos()
    df_filtros = df_futuros[df_futuros['link'].notnull() & df_futuros['data_encontrado'].notnull()]

    hoje = datetime.today()
    trinta_dias_atras = hoje - timedelta(days=30)

    df_mensal = df_filtros[
        (df_filtros['data_encontrado'] >= trinta_dias_atras) & 
        (df_filtros['data_encontrado'] <= hoje)
    ]

    if df_mensal.empty:
        df_mensal = pd.DataFrame(columns=['processo', 'data_encontrado', 'link'])

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
    
@app.route('/graficos')
def graficos():
    # Verifica se o usuário está logado
    if not session.get('usuario_logado'):
        return redirect(url_for('login'))

    # Conecta ao banco de dados
    conn = get_db_connection("postgres", "hoqTncYzOHdQShgdVDdEPqJIOJluwpKZ")
    cursor = conn.cursor()

    # Consulta somente os processos com número, link e data_encontrado preenchidos
    cursor.execute("""
        SELECT processo, link, data_encontrado FROM processos_encontrados 
        WHERE processo IS NOT NULL AND link IS NOT NULL AND data_encontrado IS NOT NULL
    """)
    resultados = cursor.fetchall()
    conn.close()

    # Processa os resultados para datas
    datas = [r[2].strftime('%Y-%m-%d') for r in resultados if r[2]]
    datas_semana = [r[2].strftime('%Y-%W') for r in resultados if r[2]]
    datas_mes = [r[2].strftime('%Y-%m') for r in resultados if r[2]]

    # Função para agrupar e contar as ocorrências
    def agrupar_contagem(datas):
        contagem = Counter(datas)
        return [{'data': k, 'quantidade': v} for k, v in sorted(contagem.items())]

    # Retorna o template com os gráficos de dados agregados
    return render_template(
        'graficos.html',
        dados_diario=agrupar_contagem(datas),
        dados_semanal=agrupar_contagem(datas_semana),
        dados_mensal=agrupar_contagem(datas_mes),
        usuario=session['usuario_logado']
    )

@app.route('/logout')
def logout():
    session.clear()  # Remove todos os dados da sessão
    return redirect(url_for('login'))  # Redireciona para a tela de login
    
if __name__ == '__main__':
    app.run(debug=True)



    
if __name__ == '__main__':
    app.run(debug=True)

