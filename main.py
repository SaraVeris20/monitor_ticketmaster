import time
import requests
import os
import re
from playwright.sync_api import sync_playwright

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

def verificar_bloqueio(texto, url_atual):
    if URL not in url_atual:
        return f"Redirecionado para: {url_atual}"

    for palavra in PALAVRAS_BLOQUEIO:
        if palavra in texto:
            return f"Bloqueio detectado: '{palavra}'"

    if len(texto.strip()) < 200:
        return f"Página suspeita (muito curta: {len(texto)} caracteres)"

    return None

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
# LOOP PRINCIPAL
# =========================

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )

        page = context.new_page()

        # Disfarça o playwright
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("🌐 Abrindo página...")
        page.goto(URL, timeout=30000)
        page.wait_for_timeout(12000)

        texto_inicial = re.sub(r'\s+', ' ', page.inner_text("body").lower()).strip()
        status_anterior = checar_disponibilidade(texto_inicial)

        print(f"✅ Monitor iniciado | Status inicial: {status_anterior.upper()}")
        enviar(
            f"🤖 Monitor iniciado!\n"
            f"Status atual: {status_anterior.upper()}\n"
            f"🔗 {URL}"
        )

        while True:
            try:
                page.reload(timeout=30000)
                page.wait_for_timeout(10000)

                texto_atual = re.sub(r'\s+', ' ', page.inner_text("body").lower()).strip()
                url_atual = page.url

                # --- Checa bloqueio ---
                bloqueio = verificar_bloqueio(texto_atual, url_atual)
                if bloqueio:
                    print(f"🚫 [{time.strftime('%H:%M:%S')}] {bloqueio}")
                    enviar(
                        f"🚫 MONITOR BLOQUEADO!\n"
                        f"Motivo: {bloqueio}\n"
                        f"Aguardando 5 minutos antes de tentar novamente..."
                    )
                    time.sleep(300)
                    page.goto(URL, timeout=30000)
                    page.wait_for_timeout(15000)
                    continue

                # --- Analisa disponibilidade ---
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

main()
