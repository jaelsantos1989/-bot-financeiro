from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import json
from datetime import datetime

app = Flask(__name__)

# Simulando um banco de dados simples em memória
usuario_dados = {
    "nome": "Jael",
    "saldo": 0,
    "despesas": [],
    "receitas": [],
    "metas": []
}

@app.route("/webhook", methods=["POST", "GET"])
def webhook():
    if request.method == "GET":
        return "Bot Financeiro está online! 💰"

    # Pega a mensagem que veio do WhatsApp
    mensagem = request.values.get('Body', '').strip().lower()

    resp = MessagingResponse()
    msg = resp.message()

    # MENU PRINCIPAL
    if mensagem == "menu":
        resposta = """
🤖 *BEM-VINDO AO BOT FINANCEIRO* 💰

Escolha uma opção:

1️⃣ *saldo* - Ver seu saldo atual
2️⃣ *receita [valor]* - Registrar uma receita
3️⃣ *despesa [valor]* - Registrar uma despesa
4️⃣ *extrato* - Ver histórico
5️⃣ *meta [valor]* - Definir uma meta
6️⃣ *ajuda* - Ver comandos

Exemplo: "receita 1000" ou "despesa 150"
        """
        msg.body(resposta)

    # VER SALDO
    elif mensagem == "saldo":
        saldo = usuario_dados["saldo"]
        resposta = f"💵 Seu saldo atual: R$ {saldo:.2f}"
        msg.body(resposta)

    # REGISTRAR RECEITA
    elif mensagem.startswith("receita"):
        try:
            valor = float(mensagem.split()[1])
            usuario_dados["saldo"] += valor
            usuario_dados["receitas"].append({
                "valor": valor,
                "data": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            resposta = f"✅ Receita de R$ {valor:.2f} registrada!\n💰 Novo saldo: R$ {usuario_dados['saldo']:.2f}"
            msg.body(resposta)
        except:
            msg.body("❌ Formato inválido. Use: receita 1000")

    # REGISTRAR DESPESA
    elif mensagem.startswith("despesa"):
        try:
            valor = float(mensagem.split()[1])
            usuario_dados["saldo"] -= valor
            usuario_dados["despesas"].append({
                "valor": valor,
                "data": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            resposta = f"✅ Despesa de R$ {valor:.2f} registrada!\n💰 Novo saldo: R$ {usuario_dados['saldo']:.2f}"
            msg.body(resposta)
        except:
            msg.body("❌ Formato inválido. Use: despesa 150")

    # VER EXTRATO
    elif mensagem == "extrato":
        receitas_total = sum([r["valor"] for r in usuario_dados["receitas"]])
        despesas_total = sum([d["valor"] for d in usuario_dados["despesas"]])

        resposta = f"""
📊 *EXTRATO FINANCEIRO*

📈 Total de Receitas: R$ {receitas_total:.2f}
📉 Total de Despesas: R$ {despesas_total:.2f}
💰 Saldo: R$ {usuario_dados['saldo']:.2f}

Últimas transações:
"""

        # Últimas 5 transações
        todas = []
        for r in usuario_dados["receitas"][-3:]:
            todas.append(f"✅ +R$ {r['valor']:.2f} ({r['data']})")
        for d in usuario_dados["despesas"][-3:]:
            todas.append(f"❌ -R$ {d['valor']:.2f} ({d['data']})")

        resposta += "\n".join(todas) if todas else "Nenhuma transação registrada"
        msg.body(resposta)

    # DEFINIR META
    elif mensagem.startswith("meta"):
        try:
            valor = float(mensagem.split()[1])
            usuario_dados["metas"].append(valor)
            resposta = f"🎯 Meta de R$ {valor:.2f} definida!\nVocê tem {len(usuario_dados['metas'])} meta(s) ativa(s)."
            msg.body(resposta)
        except:
            msg.body("❌ Formato inválido. Use: meta 5000")

    # AJUDA
    elif mensagem == "ajuda":
        resposta = """
📚 *COMANDOS DISPONÍVEIS*

menu - Mostrar este menu
saldo - Ver saldo atual
receita [valor] - Adicionar receita
despesa [valor] - Adicionar despesa
extrato - Ver histórico
meta [valor] - Definir meta financeira
ajuda - Ver esta mensagem

Exemplo: "receita 2000" ou "despesa 500"
        """
        msg.body(resposta)

    # MENSAGEM NÃO RECONHECIDA
    else:
        msg.body("❌ Comando não reconhecido. Digite *menu* para ver as opções.")

    return str(resp)

if __name__ == "__main__":
    print("✅ Bot Financeiro COMPLETO rodando em http://127.0.0.1:5000")
    print("📱 Aguardando mensagens do WhatsApp...")
    app.run(host="0.0.0.0", port=5000, debug=True)
