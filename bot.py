import requests
import time
import os

ASSEMBLYAI_API_KEY = os.environ.get("ASSEMBLYAI_API_KEY")

def transcrever_audio(url_audio):
    headers = {"authorization": ASSEMBLYAI_API_KEY}

    # Baixar áudio da Twilio com autenticação
    from requests.auth import HTTPBasicAuth
    twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")

    audio_resp = requests.get(url_audio, auth=HTTPBasicAuth(twilio_sid, twilio_token))
    if audio_resp.status_code != 200:
        return f"Erro ao baixar áudio: {audio_resp.status_code}"

    # Upload para AssemblyAI
    up = requests.post(
        "https://api.assemblyai.com/v2/upload",
        headers=headers,
        data=audio_resp.content
    )
    if up.status_code != 200:
        return f"Erro no upload: {up.text}"

    audio_url = up.json()["upload_url"]

    # Criar transcrição
    tr = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        headers=headers,
        json={"audio_url": audio_url, "language_code": "pt"}
    )
    if tr.status_code != 200:
        return f"Erro ao criar transcrição: {tr.text}"

    tid = tr.json()["id"]

    # Polling até completar (máx ~40s)
    for _ in range(20):
        res = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{tid}",
            headers=headers
        )
        data = res.json()
        if data["status"] == "completed":
            return data["text"]
        if data["status"] == "error":
            return f"Erro na transcrição: {data.get('error')}"
        time.sleep(2)

    return "Transcrição demorou demais"
