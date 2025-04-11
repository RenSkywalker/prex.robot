import streamlit as st
# import pandas as pd
# import psycopg2
# from datetime import datetime

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
        # usuario = autenticar_usuario(email, senha)
        usuario = "Usuário Teste"  # Simula login bem-sucedido
        st.session_state.usuario_logado = usuario
        st.success(f"Bem-vindo, {usuario}!")
    st.stop()

# --- Tela principal (dados simulados) ---
st.title("📄 Processos Encontrados")
st.write(f"Usuário: {st.session_state.usuario_logado}")

# Simula dados
st.markdown("**0071381-52.2025.8.26.0500** — [Acessar processo](https://esaj.tjsp.jus.br/cpopg/show.do?processo.codigo=DW002GS800000&processo.foro=500&processo.numero=0071381-52.2025.8.26.0500)")
st.markdown("**0009876-53.2024.8.26.0053** — [Acessar processo](https://esaj.tjsp.jus.br/cpopg/show.do?processo.codigo=ZX001PTO400000&processo.foro=53&processo.numero=0009876-53.2024.8.26.0053)")
