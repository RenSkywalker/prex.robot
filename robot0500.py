import os
import random
import time
import psycopg2
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# Função para conexão com o banco
def conectar_banco():
    return psycopg2.connect(
        dbname="robo_prex",
        user="robo_admin",
        password="cursirenan79",
        host="localhost",
        port="5432"
    )

# Função para verificar se o processo já foi registrado
def processo_ja_registrado(processo):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM processos_encontrados WHERE numero_processo = %s
        UNION
        SELECT 1 FROM processos_nao_encontrados WHERE numero_processo = %s
    """, (numero_processo, processo))
    resultado = cursor.fetchone()
    cursor.close()
    conn.close()
    return resultado is not None

# Função para registrar processo no banco
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

# Configuração do WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")  # Usar o modo headless mais recente
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")

try:
    service = Service()  # chromedriver deve estar em /usr/local/bin ou no PATH
    driver = webdriver.Chrome(service=service, options=options)
except Exception as e:
    print(f"Erro ao iniciar o WebDriver: {e}")
    exit(1)

# URL base
url_tjsp = "https://esaj.tjsp.jus.br/cpopg/abrirConsultaDeRequisitorios.do"

# Função principal de busca
def buscar_precatorios_tjsp(processos):
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

            elif url_depois != url_antes and "DW" not in url_depois:
                print(f"⚠️ URL mudou sem 'DW': {processo} - {url_depois}")
                registrar_processo(processo, False)

        except Exception as e:
            print(f"❗ Erro ao buscar precatórios para {processo}: {e}")
            registrar_processo(processo, False)

# Gera e filtra processos
processos = [gerar_numero_processo() for _ in range(700)]

# Inicia busca
buscar_precatorios_tjsp(processos)

# Encerra driver
driver.quit()


