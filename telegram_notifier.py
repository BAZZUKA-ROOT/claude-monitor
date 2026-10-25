import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
TOKEN_LIMIT        = int(os.getenv("TOKEN_LIMIT", "0"))

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _send(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[telegram] token ou chat_id não configurados — pulando envio")
        return
    resp = requests.post(f"{API_BASE}/sendMessage", json={
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": "HTML",
    }, timeout=15)
    resp.raise_for_status()


def send_alert(usage: dict, threshold: int):
    pct = _pct(usage["total_tokens"])
    emoji = "🟢" if threshold < 75 else ("🟡" if threshold < 90 else "🔴")
    _send(
        f"{emoji} <b>Claude API — Alerta {threshold}%</b>\n\n"
        f"📊 Usado: <b>{pct:.1f}%</b>\n"
        f"🔢 Tokens: <code>{usage['total_tokens']:,}</code> / <code>{TOKEN_LIMIT:,}</code>\n"
        f"💵 Custo estimado: <b>US$ {usage['cost_usd']:.4f}</b>\n"
        f"📅 Período: {usage['period_start']} → {usage['period_end']}"
    )


def send_daily_report(usage: dict):
    from datetime import date
    _send(
        f"📅 <b>Relatório diário — {date.today()}</b>\n\n"
        f"📥 Input tokens:  <code>{usage['input_tokens']:,}</code>\n"
        f"📤 Output tokens: <code>{usage['output_tokens']:,}</code>\n"
        f"💵 Custo hoje:    <b>US$ {usage['cost_usd']:.4f}</b>"
    )


def send_period_reset():
    _send("🔄 <b>Novo período de cobrança iniciado.</b>\nContadores zerados.")


def test_connection():
    _send("✅ <b>Claude Monitor</b> conectado com sucesso!")
    print("[telegram] mensagem de teste enviada")


def _pct(tokens: int) -> float:
    if TOKEN_LIMIT <= 0:
        return 0.0
    return tokens / TOKEN_LIMIT * 100
