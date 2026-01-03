@app.post("/webhook")
def webhook():
    from twilio.twiml.messaging_response import MessagingResponse

    incoming_msg = request.values.get('Body', '').strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    # 1️⃣ PRIMEIRO: Verifica comandos
    if incoming_msg in ["menu", "menü"]:
        msg.body("""📋 *MENU DE COMANDOS*

1️⃣ Registrar gasto:
   "Gastei [valor] reais em [descrição]"
   Exemplo: Gastei 50 reais no mercado

2️⃣ Ver total gasto:
   "Quanto gastei?"

3️⃣ Ver este menu:
   "Menu"
        """)
        return str(resp)

    elif "quanto gastei" in incoming_msg:
        # Aqui você busca o total (use sua função atual)
        total = buscar_total_gastos()
        msg.body(f"💰 Você gastou R$ {total:.2f} até agora.")
        return str(resp)

    # 2️⃣ DEPOIS: Tenta detectar gasto
    elif detectar_gasto(incoming_msg):
        registrar_gasto(incoming_msg)
        msg.body("✅ Gasto registrado com sucesso!")
        return str(resp)

    # 3️⃣ Se nada funcionar
    else:
        msg.body("❓ Comando não reconhecido. Digite 'menu' para ver as opções.")
        return str(resp)
