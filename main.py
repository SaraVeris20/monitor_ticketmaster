import time
import requests
import re
import random
from bs4 import BeautifulSoup

# =========================
# CONFIGURAÇÕES
# =========================

URL = "https://www.ticketmaster.com.br/event/venda-geral-bts-world-tour-arirang-31-10"

TELEGRAM_TOKEN = "8789223090:AAEcikuI7VWkIWIAj8VzqRDz8iTwQx-U1TY"
CHAT_ID = "1473082339"

INTERVALO_MIN = 40
INTERVALO_MAX = 70

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]

# =========================
# PALAVRAS-CHAVE
# =========================

PALAVRAS_ESGOTADO = [
    "esgotado",
    "sold out",
    "encerrado",
    "indisponível",
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
# BUSCAR PÁGINA
# =========================

def buscar_pagina():
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "Referer": "https://www.google.com/",
        }

        session = requests.Session()
        session.get("https://www.ticketmaster.com.br", headers=headers, timeout=20)
        time.sleep(random.uniform(3, 7))

        response = session.get(URL, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, "html.parser")
        texto = soup.get_text(separator=" ").lower()
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto, response.status_code

    except Exception as e:
        print(f"Erro ao buscar página: {e}")
        return None, None

# =========================
# CHECAR DISPONIBILIDADE
# =========================

def checar_disponibilidade(texto):
    # Se tiver qualquer palavra de esgotado → esgotado
    if any(p in texto for p in PALAVRAS_ESGOTADO):
        return "esgotado"

    # Se tiver "ingressos" sem nenhuma palavra de esgotado → disponível
    if "ingressos" in texto:
        return "disponivel"

    # Não foi possível determinar
    return "incerto"

# =========================
# INICIAR
# =========================

print("🌐 Iniciando monitor...")
enviar(f"🤖 Monitor iniciado! Monitorando a cada {INTERVALO_MIN}~{INTERVALO_MAX}s\n🔗 {URL}")

status_anterior = None
bloqueios_consecutivos = 0

# =========================
# LOOP PRINCIPAL
# =========================

while True:
    try:
        espera = random.uniform(INTERVALO_MIN, INTERVALO_MAX)
        time.sleep(espera)

        texto_atual, status_code = buscar_pagina()

        # Falha na requisição
        if texto_atual is None:
            print(f"[{time.strftime('%H:%M:%S')}] Falha ao buscar, tentando novamente...")
            continue

        # --- Checa bloqueio 403/429 ---
        if status_code in [403, 429, 503]:
            bloqueios_consecutivos += 1
            espera_bloqueio = min(300 * bloqueios_consecutivos, 1800)  # máx 30 min
            print(f"🚫 [{time.strftime('%H:%M:%S')}] HTTP {status_code} — aguardando {espera_bloqueio//60} min...")
            if bloqueios_consecutivos == 1:
                enviar(f"🚫 IP bloqueado (HTTP {status_code}). Aguardando {espera_bloqueio//60} min...")
            time.sleep(espera_bloqueio)
            continue

        # Reset contador de bloqueios se a requisição passou
        bloqueios_consecutivos = 0

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
            enviar("😔 Ingressos esgotaram. Continuando monitoramento...")

        # Atualiza status anterior apenas se não for incerto
        # (não substitui o último status válido)
        if status_atual != "incerto":
            status_anterior = status_atual

    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Erro: {e}")
        time.sleep(30)
