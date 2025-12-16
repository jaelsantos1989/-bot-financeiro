from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import os
from datetime import datetime, timedelta
import requests

app = Flask(__name__)

# Configurações Twilio
ACCOUNT_SID = "seu_account_sid_aqui"
AUTH_TOKEN = "seu_auth_token_aqui"
client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Banco de dados
DB_FILE = "gastos.db"

# Categorias (regras simples)
CATEGORIAS = {
    "alimentacao": ["mercado", "padaria", "supermercado", "restaurante", "lanche", "pizza", "burger", "comida", "almoço", "café", "açai"],
    "transporte": ["ônibus", "uber", "gasolina", "táxi", "passagem", "metrô", "carro", "combustível"],
    "moradia": ["aluguel", "condomínio", "água", "luz", "energia", "gás", "internet", "telefone"],
    "saude": ["farmácia", "médico", "dentista", "hospital", "remédio", "medicamento"],
    "lazer": ["cinema", "bar", "show", "jogo", "diversão", "festa", "viagem"],
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
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

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
    match = re.search(r'R?\$?\s*(\d+[.,]?\d*)', texto)
    if match:
        valor_str = match.group(1).replace(',', '.')
        return float(valor_str)
    return None

# Salvar gasto
def salvar_gasto(valor, categoria, descricao):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    data = datetime.now().strftime("%Y-%m-%d")
    c.execute('''
        INSERT INTO gastos (data, valor, categoria, descricao)
        VALUES (?, ?, ?, ?)
    ''', (data, valor, categoria, descricao))
    conn.commit()
    conn.close()

# Gerar relatório
def gerar_relatorio(tipo="diario"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    hoje = datetime.now().strftime("%Y-%m-%d")

    if tipo == "diario":
        c.execute('''
            SELECT categoria, SUM(valor) FROM gastos 
            WHERE data = ? 
            GROUP BY categoria
        ''', (hoje,))
    elif tipo == "semanal":
        data_inicio = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        c.execute('''
            SELECT categoria, SUM(valor) FROM gastos 
            WHERE data >= ? 
            GROUP BY categoria
        ''', (data_inicio,))
    elif tipo == "mensal":
        mes_ano = hoje[:7]
        c.execute('''
            SELECT categoria, SUM(valor) FROM gastos 
            WHERE data LIKE ? 
            GROUP BY categoria
        ''', (mes_ano + '%',))

    resultados = c.fetchall()
    conn.close()

    if not resultados:
        return f"Nenhum gasto registrado para este período ({tipo})."

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

    resp = MessagingResponse()

    if incoming_msg.lower() == "menu":
        resp.message("""
📱 MENU FINANCEIRO

1️⃣ Envie um áudio: "Gastei 45 reais no mercado"
2️⃣ Relatório diário: "relatório diário"
3️⃣ Relatório semanal: "relatório semanal"
4️⃣ Relatório mensal: "relatório mensal"
5️⃣ Ajuda: "ajuda"
        """)

    elif "relatório" in incoming_msg.lower():
        if "semanal" in incoming_msg.lower():
            relatorio = gerar_relatorio("semanal")
        elif "mensal" in incoming_msg.lower():
            relatorio = gerar_relatorio("mensal")
        else:
            relatorio = gerar_relatorio("diario")
        resp.message(relatorio)

    elif incoming_msg.lower() == "ajuda":
        resp.message("""
💡 COMO USAR:

📝 Envie mensagens com seus gastos:
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
        # Tentar extrair valor e categoria
        valor = extrair_valor(incoming_msg)
        if valor:
            categoria = categorizar(incoming_msg)
            salvar_gasto(valor, categoria, incoming_msg)
            resp.message(f"✅ Registrado: R$ {valor:.2f} em {categoria.capitalize()}\n📝 {incoming_msg}")
        else:
            resp.message("❓ Comando não reconhecido. Digite 'menu' para ver as opções.")

    return str(resp)

if __name__ == '__main__':
    app.run(debug=False)
