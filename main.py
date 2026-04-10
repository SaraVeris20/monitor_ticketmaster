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

INTERVALO_MIN = 25  # segundos mínimos entre verificações
INTERVALO_MAX = 45  # segundos máximos entre verificações (variação aleatória)

# Lista de User-Agents para rotacionar
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

PALAVRAS_DISPONIVEL = [
    "ingressos",
]

PALAVRAS_ESGOTADO = [
    "esgotado",
    "sold out",
    "encerrado",
    "indisponível",
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
# BUSCAR PÁGINA
# =========================

def buscar_pagina():
    try:
        # Rotaciona User-Agent a cada requisição
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
        # Primeira visita à home para pegar cookies (simula navegação humana)
        session.get("https://www.ticketmaster.com.br", headers=headers, timeout=20)
        time.sleep(random.uniform(2, 5))

        # Agora acessa a página do evento
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
    tem_esgotado = any(p in texto for p in PALAVRAS_ESGOTADO)

    if tem_esgotado:
        return "esgotado"

    tem_disponivel = any(p in texto for p in PALAVRAS_DISPONIVEL)
    if tem_disponivel:
        return "disponivel"

    return "incerto"

def verificar_bloqueio(texto, status_code):
    if status_code in [403, 429, 503]:
        return f"HTTP {status_code} — acesso bloqueado"
    if texto:
        for palavra in PALAVRAS_BLOQUEIO:
            if palavra in texto:
                return f"Bloqueio detectado: '{palavra}'"
        if len(texto.strip()) < 200:
            return f"Página suspeita (muito curta: {len(texto)} caracteres)"
    return None

# =========================
# INICIAR
# =========================

print("🌐 Iniciando monitor...")
enviar(f"🤖 Monitor iniciado!\n🔗 {URL}")

texto_inicial, status = buscar_pagina()

if texto_inicial:
    status_anterior = checar_disponibilidade(texto_inicial)
else:
    status_anterior = "incerto"

print(f"✅ Status inicial: {status_anterior.upper()}")
enviar(f"Status atual: {status_anterior.upper()}")

# =========================
# LOOP PRINCIPAL
# =========================

while True:
    try:
        # Intervalo aleatório para parecer mais humano
        espera = random.uniform(INTERVALO_MIN, INTERVALO_MAX)
        print(f"⏳ Aguardando {espera:.0f}s...")
        time.sleep(espera)

        texto_atual, status_code = buscar_pagina()

        if texto_atual is None:
            print(f"[{time.strftime('%H:%M:%S')}] Falha ao buscar página, tentando novamente...")
            continue

        # --- Checa bloqueio ---
        bloqueio = verificar_bloqueio(texto_atual, status_code)
        if bloqueio:
            print(f"🚫 [{time.strftime('%H:%M:%S')}] {bloqueio}")
            espera_bloqueio = random.uniform(300, 600)  # 5 a 10 min aleatório
            enviar(
                f"🚫 MONITOR BLOQUEADO!\n"
                f"Motivo: {bloqueio}\n"
                f"Aguardando {espera_bloqueio/60:.0f} minutos antes de tentar novamente..."
            )
            time.sleep(espera_bloqueio)
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
            print("⚠️  Status incerto — verificando na próxima rodada.")

        status_anterior = status_atual

    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Erro: {e}")
        enviar(f"⚠️ Erro no monitor: {e}\nTentando continuar...")
        time.sleep(30)
