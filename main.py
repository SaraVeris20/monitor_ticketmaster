import time
import requests
import os
import re

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =========================
# CONFIGURAÇÕES
# =========================

URL = "https://www.ticketmaster.com.br/event/venda-geral-bts-world-tour-arirang-31-10"

TELEGRAM_TOKEN = "8789223090:AAEcikuI7VWkIWIAj8VzqRDz8iTwQx-U1TY"
CHAT_ID = "1473082339"

INTERVALO = 25  # segundos entre verificações

# =========================
# PALAVRAS-CHAVE
# =========================

PALAVRAS_DISPONIVEL = [
    "comprar",
    "adicionar ao carrinho",
    "selecionar ingresso",
    "buy",
    "add to cart",
    "compre agora",
    "escolha seu ingresso",
]

PALAVRAS_ESGOTADO = [
    "esgotado",
    "sold out",
    "indisponível",
    "unavailable",
    "em breve",
    "coming soon",
    "lista de espera",
]

PALAVRAS_BLOQUEIO = [
    "access denied",
    "403",
    "429",
    "too many requests",
    "captcha",
    "bot detected",
    "are you human",
    "blocked",
    "unusual traffic",
    "verify you are human",
    "cloudflare",
    "ray id",
]

# =========================
# TELEGRAM
# =========================

def enviar(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")

# =========================
# DETECTAR BLOQUEIO
# =========================

def verificar_bloqueio(driver):
    url_atual = driver.current_url
    texto = driver.find_element(By.TAG_NAME, "body").text.lower()

    if URL not in url_atual:
        return f"Redirecionado para: {url_atual}"

    for palavra in PALAVRAS_BLOQUEIO:
        if palavra in texto:
            return f"Bloqueio detectado: '{palavra}'"

    if len(texto.strip()) < 200:
        return f"Página suspeita (muito curta: {len(texto)} caracteres)"

    return None

# =========================
# EXTRAIR ESTADO REAL DA PÁGINA
# =========================

def extrair_estado(driver):
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except Exception:
        pass

    texto_visivel = driver.find_element(By.TAG_NAME, "body").text.lower()
    texto_visivel = re.sub(r'\s+', ' ', texto_visivel).strip()
    return texto_visivel

# =========================
# CHECAR DISPONIBILIDADE
# =========================

def checar_disponibilidade(texto):
    tem_disponivel = any(p in texto for p in PALAVRAS_DISPONIVEL)
    tem_esgotado   = any(p in texto for p in PALAVRAS_ESGOTADO)

    if tem_disponivel and not tem_esgotado:
        return "disponivel"
    elif tem_esgotado:
        return "esgotado"
    else:
        return "incerto"

# =========================
# SELENIUM CONFIG
# =========================

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument(
    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.binary_location = "/usr/bin/chromium"

# ✅ Usa o chromedriver instalado pelo Docker
driver = webdriver.Chrome(
    service=Service("/usr/bin/chromedriver"),
    options=options
)

# Disfarça o Selenium para não ser detectado
driver.execute_cdp_cmd(
    "Page.addScriptToEvaluateOnNewDocument",
    {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
)

# =========================
# INICIAR
# =========================

driver.get(URL)
time.sleep(12)

texto_inicial = extrair_estado(driver)
status_anterior = checar_disponibilidade(texto_inicial)

print(f"✅ Monitor iniciado | Status inicial: {status_anterior.upper()}")
enviar(
    f"🤖 Monitor iniciado!\n"
    f"Status atual: {status_anterior.upper()}\n"
    f"🔗 {URL}"
)

# =========================
# LOOP PRINCIPAL
# =========================

while True:
    try:
        driver.refresh()
        time.sleep(10)

        # --- Checa bloqueio antes de tudo ---
        bloqueio = verificar_bloqueio(driver)
        if bloqueio:
            print(f"🚫 [{time.strftime('%H:%M:%S')}] {bloqueio}")
            enviar(
                f"🚫 MONITOR BLOQUEADO!\n"
                f"Motivo: {bloqueio}\n"
                f"Aguardando 5 minutos antes de tentar novamente..."
            )
            time.sleep(300)
            driver.get(URL)
            time.sleep(15)
            continue

        # --- Analisa disponibilidade ---
        texto_atual = extrair_estado(driver)
        status_atual = checar_disponibilidade(texto_atual)

        print(f"[{time.strftime('%H:%M:%S')}] Status: {status_atual.upper()}")

        # 🎟️ Ingressos disponíveis!
        if status_atual == "disponivel" and status_anterior != "disponivel":
            msg = (
                "🎟️🚨 INGRESSOS DISPONÍVEIS!\n"
                f"🔗 Corra: {URL}\n"
                "⚡ Compre agora antes que esgotem!"
            )
            print("🚨 " + msg)
            enviar(msg)
            os.system("echo '\a'")

        # 😔 Voltou a esgotar
        elif status_atual == "esgotado" and status_anterior == "disponivel":
            enviar("😔 Ingressos esgotaram novamente. Continuando monitoramento...")

        # ⚠️ Status incerto
        elif status_atual == "incerto":
            print("⚠️  Status incerto — página pode estar carregando ou com layout diferente.")

        status_anterior = status_atual
        time.sleep(INTERVALO)

    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Erro: {e}")
        enviar(f"⚠️ Erro no monitor: {e}\nTentando continuar...")
        time.sleep(INTERVALO)

    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Erro: {e}")
        enviar(f"⚠️ Erro no monitor: {e}\nTentando continuar...")
        time.sleep(INTERVALO)
