"""
Helper: descobre o chat_id do canal/grupo/chat que seu bot pode acessar.
Execute com:  python get_chat_id.py
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not TOKEN or TOKEN.startswith("123456"):
    print("❌ Configure TELEGRAM_BOT_TOKEN no .env antes de rodar este script.")
    sys.exit(1)

resp = requests.get(
    f"https://api.telegram.org/bot{TOKEN}/getUpdates",
    timeout=10
)

if not resp.ok:
    print(f"❌ Erro na API do Telegram: {resp.text}")
    sys.exit(1)

updates = resp.json().get("result", [])
if not updates:
    print("⚠️  Nenhuma mensagem recebida ainda.")
    print("   1. Adicione o bot ao canal/grupo como administrador")
    print("   2. Envie qualquer mensagem no canal")
    print("   3. Rode este script novamente")
    sys.exit(0)

seen = set()
for u in updates:
    chat = (
        u.get("message", {}).get("chat") or
        u.get("channel_post", {}).get("chat") or
        u.get("my_chat_member", {}).get("chat") or {}
    )
    if not chat or chat["id"] in seen:
        continue
    seen.add(chat["id"])
    print(f"\n✅ chat_id encontrado!")
    print(f"   ID:   {chat['id']}")
    print(f"   Tipo: {chat.get('type', '?')}")
    print(f"   Nome: {chat.get('title') or chat.get('username') or chat.get('first_name', '?')}")
