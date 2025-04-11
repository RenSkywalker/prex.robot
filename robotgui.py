import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

# --- Conexão com o banco de forma otimizada ---
@st.cache_resource
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

# --- Controle de sessão ---
if 'primeiro_login' not in st.session_state:
    st.session_state.primeiro_login = True
if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None

# --- Tela de boas-vindas ---
if st.session_state.primeiro_login:
    st.title("🤖 Bem-vindo ao Robô de Precatórios!")
    st.info("Este robô automatiza a busca por processos com cálculos homologados. Faça login para continuar.")
    if st.button("Ir para o login"):
        st.session_state.primeiro_login = False
    st.stop()

# --- Tela de login ---
if not st.session_state.usuario_logado:
    st.title("🔐 Login")
    email = st.text_input("Email")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        usuario = autenticar_usuario(email, senha)
        if usuario:
            st.session_state.usuario_logado = usuario
            st.success(f"Bem-vindo, {usuario}!")
        else:
            st.error("Credenciais inválidas.")
    st.stop()

# --- Tela principal ---
st.title("📄 Processos Encontrados")
st.write(f"Usuário: {st.session_state.usuario_logado}")

processos_df = carregar_processos()
if not processos_df.empty:
    for index, row in processos_df.iterrows():
        st.markdown(f"**{row['numero_processo']}** — [Acessar processo]({row['link']})")
else:
    st.warning("Nenhum processo encontrado no momento.")
