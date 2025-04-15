import os 
import random
import time
import logging
import psycopg2
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from datetime import datetime

# === CONFIGURAR LOGGING ===
logging.basicConfig(
    filename="/home/ubuntu/robot.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.debug("Iniciando script robot0500.py")
print(f"🚀 Iniciando script robot0500.py em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# === Função para conexão com o banco ===
def conectar_banco():
    try:
        conn = psycopg2.connect("postgresql://postgres:hoqTncYzOHdQShgdVDdEPqJIOJluwpKZ@yamabiko.proxy.rlwy.net:56223/railway")
        logging.info("✅ Conexão com o banco de dados estabelecida com sucesso.")
        return conn
    except Exception as e:
        logging.error(f"❌ Erro ao conectar ao banco de dados: {e}")
        raise

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

def registrar_processo(processo, encontrado, url=None):
    conn = conectar_banco()
    cursor = conn.cursor()
    if encontrado:
        cursor.execute(""" 
            INSERT INTO processos_encontrados (processo, link, data_encontrado) 
            VALUES (%s, %s, %s)
            ON CONFLICT (processo) DO NOTHING
        """, (processo, url, datetime.now()))
        logging.info(f"📥 Processo registrado em 'processos_encontrados': {processo}")
    else:
        cursor.execute(""" 
            INSERT INTO processos_nao_encontrados (processo) 
            VALUES (%s)
            ON CONFLICT DO NOTHING
        """, (processo,))
        logging.info(f"📥 Processo registrado em 'processos_nao_encontrados': {processo}")
    conn.commit()
    cursor.close()
    conn.close()

def gerar_numero_processo():
    prefixos = ["00", "01", "04", "10"]
    pesos = [0.8, 0.07, 0.07, 0.06]
    prefixo_fixo = random.choices(prefixos, weights=pesos, k=1)[0]
    numeros_aleatorios = f"{random.randint(0, 9999999):07d}"
    ano_fixo = random.choice([2024, 2025])
    return f"{prefixo_fixo}{numeros_aleatorios}.{ano_fixo}.8.26.0500"

def gerar_processos_unicos(quantidade):
    processos_unicos = set()
    tentativas = 0
    while len(processos_unicos) < quantidade and tentativas < quantidade * 10:
        processo = gerar_numero_processo()
        if processo not in processos_unicos and not processo_ja_registrado(processo):
            processos_unicos.add(processo)
        tentativas += 1
    return list(processos_unicos)

def dentro_do_horario():
    agora = datetime.now()
    return 7 <= agora.hour < 21 and agora.weekday() < 5

def iniciar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service()
    return webdriver.Chrome(service=service, options=options)

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
                msg = f"❌ Processo não encontrado: {processo}"
                print(msg)
                logging.info(msg)
                registrar_processo(processo, False)
            elif url_depois != url_antes and "DW" in url_depois:
                msg = f"✅ Processo encontrado: {processo} - {url_depois}"
                print(msg)
                logging.info(msg)
                registrar_processo(processo, True, url_depois)
            elif url_depois != url_antes:
                msg = f"⚠️ URL mudou sem 'DW': {processo} - {url_depois}"
                print(msg)
                logging.warning(msg)
                registrar_processo(processo, False)

        except Exception as e:
            msg = f"❗ Erro ao buscar precatórios para {processo}: {e}"
            print(msg)
            logging.error(msg)
            registrar_processo(processo, False)

# === LOOP PRINCIPAL ===
while True:
    if dentro_do_horario():
        inicio_msg = f"🔄 Iniciando busca de processos às {datetime.now().strftime('%H:%M:%S')}..."
        print(inicio_msg)
        logging.info(inicio_msg)

        # Gera processos únicos e verifica se já estão registrados
        processos = gerar_processos_unicos(300)  # << ALTERAÇÃO AQUI

        # Verifica os processos não registrados antes de começar a busca
        processos_nao_registrados = [p for p in processos if not processo_ja_registrado(p)]

        try:
            driver = iniciar_driver()
            buscar_precatorios_tjsp(driver, processos_nao_registrados)  # Somente processos não registrados
            driver.quit()
        except Exception as erro:
            msg = f"❌ Erro geral durante execução: {erro}"
            print(msg)
            logging.error(msg)
        finally:
            if 'driver' in locals():
                driver.quit()

        print("⏳ Aguardando 3 minutos até a próxima execução...\n")
        logging.info("Aguardando 3 minutos para nova execução...\n")
    else:
        msg = f"🕒 Fora do horário de execução. Agora são {datetime.now().strftime('%H:%M:%S')}"
        print(msg)
        logging.info(msg)

    time.sleep(180)  # Aguarda 3 minutos antes da próxima verificação
