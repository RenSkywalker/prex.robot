import os
import random
import time
import psycopg2
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from datetime import datetime

# Função para conexão com o banco
def conectar_banco():
    return psycopg2.connect(
        dbname="robo_prex",
        user="robo_admin",
        password="cursirenan79",
        host="localhost",
        port="5432"
    )

# Verifica se o processo já foi registrado
def processo_ja_registrado(processo):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM processos_encontrados WHERE processo = %s
        UNION
        SELECT 1 FROM processos_nao_encontrados WHERE processo = %s
    """, (processo, processo))
    resultado = cursor.fetchone()
    cursor.close()
    conn.close()
    return resultado is not None

# Registra processo no banco
def registrar_processo(processo, encontrado):
    tabela = "processos_encontrados" if encontrado else "processos_nao_encontrados"
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO {tabela} (processo) VALUES (%s)
        ON CONFLICT DO NOTHING
    """, (processo,))
    conn.commit()
    cursor.close()
    conn.close()

# Geração dos números de processo
def gerar_numero_processo():
    prefixos = ["00", "01", "04", "10"]
    pesos = [0.8, 0.07, 0.07, 0.06]
    prefixo_fixo = random.choices(prefixos, weights=pesos, k=1)[0]
    numeros_aleatorios = f"{random.randint(0, 9999999):07d}"
    ano_fixo = random.choice([2024, 2025])
    return f"{prefixo_fixo}{numeros_aleatorios}.{ano_fixo}.8.26.0500"

# Verifica se estamos no horário válido
def dentro_do_horario():
    agora = datetime.now()
    return 7 <= agora.hour < 21 and agora.weekday() < 5

# Configura WebDriver fora do loop
def iniciar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service()
    return webdriver.Chrome(service=service, options=options)

# Função principal de busca
def buscar_precatorios_tjsp(driver, processos):
    url_tjsp = "https://esaj.tjsp.jus.br/cpopg/abrirConsultaDeRequisitorios.do"
    for processo in processos:
        if processo_ja_registrado(processo):
            continue

        driver.get(url_tjsp)
        time.sleep(10)

        try:
            campo_processo = driver.find_element(By.ID, "numeroDigitoAnoUnificado")
            campo_processo.clear()
            campo_processo.send_keys(processo)

            campo_foro = driver.find_element(By.ID, "foroNumeroUnificado")
            campo_foro.clear()
            campo_foro.send_keys("0500")

            url_antes = driver.current_url
            botao_consultar = driver.find_element(By.ID, "botaoConsultarProcessos")
            botao_consultar.click()
            time.sleep(15)
            url_depois = driver.current_url

            if "<li>Não existem informações disponíveis para os parâmetros informados.</li>" in driver.page_source:
                print(f"❌ Processo não encontrado: {processo}")
                registrar_processo(processo, False)
            elif url_depois != url_antes and "DW" in url_depois:
                print(f"✅ Processo encontrado: {processo} - {url_depois}")
                registrar_processo(processo, True)
            elif url_depois != url_antes:
                print(f"⚠️ URL mudou sem 'DW': {processo} - {url_depois}")
                registrar_processo(processo, False)

        except Exception as e:
            print(f"❗ Erro ao buscar precatórios para {processo}: {e}")
            registrar_processo(processo, False)

# Loop principal do robô
while True:
    if dentro_do_horario():
        print(f"🔄 Iniciando busca de processos às {datetime.now().strftime('%H:%M:%S')}...")
        processos = [gerar_numero_processo() for _ in range(300)]
        try:
            driver = iniciar_driver()
            buscar_precatorios_tjsp(driver, processos)
            driver.quit()
        except Exception as erro:
            print(f"Erro geral: {erro}")
        print("⏳ Aguardando 5 minutos até a próxima execução...\n")
    else:
        print(f"🕒 Fora do horário de execução. Agora são {datetime.now().strftime('%H:%M:%S')}")
    time.sleep(300)  # Aguarda 5 minutos antes da próxima verificação


# Encerra driver
driver.quit()


