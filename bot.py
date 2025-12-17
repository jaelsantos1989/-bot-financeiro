from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import os
from datetime import datetime, timedelta
import requests
import time

app = Flask(__name__)

# Configurações AssemblyAI
ASSEMBLYAI_API_KEY = "SUA_CHAVE_ASSEMBLYAI_AQUI"

# Banco de dados
DB_FILE = "gastos.db"

# Categorias (regras simples)
CATEGORIAS = {
    "alimentacao": ["mercado", "padaria", "supermercado", "restaurante", "lanche", "pizza", "burger", "comida", "almoço", "jantar", "café", "açaí", "ifood", "delivery"],
    "transporte": ["ônibus", "uber", "gasolina", "táxi", "passagem", "metrô", "carro", "combustível", "posto", "99", "cabify"],
    "moradia": ["aluguel", "condomínio", "água", "luz", "energia", "gás", "internet", "telefone", "celular"],
    "saude": ["farmácia", "médico", "dentista", "hospital", "remédio", "medicamento", "consulta", "exame"],
    "lazer": ["cinema", "bar", "show", "jogo", "diversão", "festa", "viagem", "passeio"],
    "outros": []
}

# Inicializar banco de dados
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            valor REAL,
            categoria TEXT,
            descricao TEXT,
            telefone TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Transcrever áudio com AssemblyAI
def transcrever_audio(url_audio):
    try:
        # 1. Upload do áudio
        headers = {"authorization": ASSEMBLYAI_API_KEY}

        # Baixar o áudio da Twilio
        audio_data = requests.get(url_audio).content

        # Upload para AssemblyAI
        upload_response = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers=headers,
            data=audio_data
        )
        audio_url = upload_response.json()["upload_url"]

        # 2. Solicitar transcrição
        transcript_request = {
            "audio_url": audio_url,
            "language_code": "pt"
        }
        transcript_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            json=transcript_request,
            headers=headers
        )
        transcript_id = transcript_response.json()["id"]

        # 3. Aguardar conclusão
        while True:
            transcript_result = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers=headers
            )
            status = transcript_result.json()["status"]

            if status == "completed":
                return transcript_result.json()["text"]
            elif status == "error":
                return "Erro na transcrição"

            time.sleep(2)

    except Exception as e:
        return f"Erro: {str(e)}"

# Categorizar automaticamente
def categorizar(descricao):
    descricao_lower = descricao.lower()
    for categoria, palavras in CATEGORIAS.items():
        for palavra in palavras:
            if palavra in descricao_lower:
                return categoria
    return "outros"

# Extrair valor do texto
def extrair_valor(texto):
    import re
    # Procura padrões: "45", "45,50", "R$ 45", "45 reais"
    match = re.search(r'R?\$?\s*(\d+[.,]?\d*)\s*(?:reais?)?', texto, re.IGNORECASE)
    if match:
        valor_str = match.group(1).replace(',', '.')
        return float(valor_str)
    return None

# Salvar gasto
def salvar_gasto(valor, categoria, descricao, telefone):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    data = datetime.now().strftime("%Y-%m-%d")
    c.execute('''
        INSERT INTO gastos (data, valor, categoria, descricao, telefone)
        VALUES (?, ?, ?, ?, ?)
    ''', (data, valor, categoria, descricao, telefone))
    conn.commit()
    conn.close()

# Gerar relatório
def gerar_relatorio(tipo="diario", telefone=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    hoje = datetime.now().strftime("%Y-%m-%d")

    if tipo == "diario":
        c.execute('''
            SELECT categoria, SUM(valor) FROM gastos 
            WHERE data = ? AND telefone = ?
            GROUP BY categoria
        ''', (hoje, telefone))
    elif tipo == "semanal":
        data_inicio = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        c.execute('''
            SELECT categoria, SUM(valor) FROM gastos 
            WHERE data >= ? AND telefone = ?
            GROUP BY categoria
        ''', (data_inicio, telefone))
    elif tipo == "mensal":
        mes_ano = hoje[:7]
        c.execute('''
            SELECT categoria, SUM(valor) FROM gastos 
            WHERE data LIKE ? AND telefone = ?
            GROUP BY categoria
        ''', (mes_ano + '%', telefone))

    resultados = c.fetchall()
    conn.close()

    if not resultados:
        return f"📊 Nenhum gasto registrado para este período ({tipo})."

    total = sum(r[1] for r in resultados)

    relatorio = f"📊 Relatório {tipo.upper()}\n\n"
    for categoria, valor in resultados:
        emoji_cat = {
            "alimentacao": "🍔",
            "transporte": "🚗",
            "moradia": "🏠",
            "saude": "⚕️",
            "lazer": "🎬",
            "outros": "📦"
        }
        emoji = emoji_cat.get(categoria, "💰")
        relatorio += f"{emoji} {categoria.capitalize()}: R$ {valor:.2f}\n"

    relatorio += f"\n💰 Total: R$ {total:.2f}"
    return relatorio

# Webhook do WhatsApp
@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From')
    num_media = int(request.values.get('NumMedia', 0))

    resp = MessagingResponse()

    # Se for áudio
    if num_media > 0:
        media_url = request.values.get('MediaUrl0')
        media_type = request.values.get('MediaContentType0')

        if 'audio' in media_type or 'ogg' in media_type:
            resp.message("🎤 Áudio recebido! Processando...")

            # Transcrever
            texto_transcrito = transcrever_audio(media_url)

            # Extrair valor
            valor = extrair_valor(texto_transcrito)

            if valor:
                categoria = categorizar(texto_transcrito)
                salvar_gasto(valor, categoria, texto_transcrito, sender)
                resp.message(f"✅ Registrado: R$ {valor:.2f} em {categoria.capitalize()}\n📝 \"{texto_transcrito}\"")
            else:
                resp.message(f"❌ Não consegui identificar o valor.\n\n📝 Transcrição: \"{texto_transcrito}\"\n\nTente falar mais claro: 'Gastei 45 reais no mercado'")
        else:
            resp.message("❌ Por favor, envie um áudio.")

    # Se for texto
    elif incoming_msg.lower() == "menu":
        resp.message("""
📱 MENU FINANCEIRO

🎤 Envie um áudio: "Gastei 45 reais no mercado"
📊 Relatório diário: "relatório diário"
📊 Relatório semanal: "relatório semanal"
📊 Relatório mensal: "relatório mensal"
💡 Ajuda: "ajuda"
        """)

    elif "relatório" in incoming_msg.lower() or "relatorio" in incoming_msg.lower():
        if "semanal" in incoming_msg.lower():
            relatorio = gerar_relatorio("semanal", sender)
        elif "mensal" in incoming_msg.lower():
            relatorio = gerar_relatorio("mensal", sender)
        else:
            relatorio = gerar_relatorio("diario", sender)
        resp.message(relatorio)

    elif incoming_msg.lower() == "ajuda":
        resp.message("""
💡 COMO USAR:

🎤 Envie áudios com seus gastos:
"Gastei 45 reais no mercado"
"Paguei 150 na passagem"
"Gastei 80 na farmácia"

📊 Peça relatórios:
"relatório diário"
"relatório semanal"
"relatório mensal"

🏷️ Categorias automáticas:
🍔 Alimentação
🚗 Transporte
🏠 Moradia
⚕️ Saúde
🎬 Lazer
📦 Outros
        """)

    else:
        # Tentar extrair valor do texto
        valor = extrair_valor(incoming_msg)
        if valor:
            categoria = categorizar(incoming_msg)
            salvar_gasto(valor, categoria, incoming_msg, sender)
            resp.message(f"✅ Registrado: R$ {valor:.2f} em {categoria.capitalize()}\n📝 {incoming_msg}")
        else:
            resp.message("❓ Comando não reconhecido. Digite 'menu' para ver as opções.")

    return str(resp)

if __name__ == '__main__':
    app.run(debug=False)
