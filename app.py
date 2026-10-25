import os
import json
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

import db
import anthropic_fetcher as fetcher
import telegram_notifier as tg

app = Flask(__name__)

TOKEN_LIMIT        = int(os.getenv("TOKEN_LIMIT", "0"))
ALERT_THRESHOLDS   = [int(x) for x in os.getenv("ALERT_THRESHOLDS", "50,75,90,95").split(",")]
FETCH_INTERVAL_MIN = int(os.getenv("FETCH_INTERVAL_MIN", "30"))
DAILY_REPORT_TIME  = os.getenv("DAILY_REPORT_TIME", "08:00")
PORT               = int(os.getenv("PORT", "5000"))


# ── JOBS ──────────────────────────────────────────────────────────

def job_fetch():
    try:
        usage = fetcher.fetch_usage()
        db.save_snapshot(usage)
        _check_alerts(usage)
        print(f"[monitor] {datetime.utcnow().isoformat()} — {usage['total_tokens']:,} tokens | US$ {usage['cost_usd']:.4f}")
    except Exception as e:
        print(f"[monitor] erro no fetch: {e}")


def job_daily_report():
    snap = db.get_latest_snapshot()
    if snap:
        tg.send_daily_report(snap)


def _check_alerts(usage: dict):
    if TOKEN_LIMIT <= 0:
        return
    pct = usage["total_tokens"] / TOKEN_LIMIT * 100
    period = usage.get("period_start", "?")
    for threshold in sorted(ALERT_THRESHOLDS):
        if pct >= threshold and not db.alert_already_fired(period, threshold):
            tg.send_alert(usage, threshold)
            db.mark_alert_fired(period, threshold)


# ── DASHBOARD HTML ─────────────────────────────────────────────────

DASHBOARD_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claude Monitor</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#0b0f14;--s:#131920;--s2:#1b2330;--b:#253040;--acc:#8b5cf6;--cy:#22d3ee;--gr:#34d399;--ye:#fbbf24;--re:#f87171;--fg:#dde6f0;--mu:#7a8fa6;--mono:'JetBrains Mono',monospace}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--fg);font-family:'Inter',sans-serif;font-size:14px;padding:24px}
h1{font-size:1.4rem;font-weight:700;margin-bottom:4px}
.sub{color:var(--mu);font-size:13px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:24px}
.tile{background:var(--s);border:1px solid var(--b);border-radius:10px;padding:16px}
.tile .v{font-family:var(--mono);font-size:1.6rem;font-weight:700;margin-bottom:4px}
.tile .l{color:var(--mu);font-size:11px}
.bar-wrap{background:var(--s);border:1px solid var(--b);border-radius:10px;padding:16px;margin-bottom:24px}
.bar-label{display:flex;justify-content:space-between;font-size:12px;color:var(--mu);margin-bottom:8px}
.bar{height:10px;background:var(--s2);border-radius:5px;overflow:hidden}
.bar-fill{height:100%;background:linear-gradient(90deg,var(--acc),var(--cy));border-radius:5px;transition:width .5s}
.hist{background:var(--s);border:1px solid var(--b);border-radius:10px;padding:16px;margin-bottom:24px}
.hist h3{font-size:13px;font-weight:600;margin-bottom:12px;color:var(--mu)}
.bars{display:flex;align-items:flex-end;gap:4px;height:60px}
.bar-day{flex:1;background:rgba(139,92,246,.4);border-radius:2px 2px 0 0;min-height:4px;transition:height .4s}
.btn{background:var(--acc);color:#fff;border:none;border-radius:8px;padding:8px 16px;font-size:13px;cursor:pointer;font-family:'Inter',sans-serif}
.btn:hover{opacity:.85}
.ok{color:var(--gr)}
.err{color:var(--re)}
.ts{font-size:11px;color:var(--mu);margin-top:8px}
</style>
</head>
<body>
<h1>🤖 Claude Monitor</h1>
<div class="sub">Monitoramento de consumo da API Anthropic</div>

<div class="grid" id="tiles">
  <div class="tile"><div class="v" style="color:var(--acc)" id="t-total">—</div><div class="l">Tokens no período</div></div>
  <div class="tile"><div class="v" style="color:var(--cy)" id="t-cost">—</div><div class="l">Custo estimado</div></div>
  <div class="tile"><div class="v" style="color:var(--gr)" id="t-days">—</div><div class="l">Dias até reset</div></div>
  <div class="tile"><div class="v" style="color:var(--ye)" id="t-pct">—</div><div class="l">Limite consumido</div></div>
</div>

<div class="bar-wrap" id="bar-wrap" style="display:none">
  <div class="bar-label"><span id="bar-lbl">Uso do limite</span><span id="bar-val">—</span></div>
  <div class="bar"><div class="bar-fill" id="bar-fill" style="width:0%"></div></div>
  <div class="ts" id="bar-period"></div>
</div>

<div class="hist"><div class="bars" id="hist-bars"></div><div class="ts" id="hist-label">Tokens diários (últimos 7 dias)</div></div>

<button class="btn" onclick="testTelegram()">📨 Testar Telegram</button>
<button class="btn" style="background:var(--s2);color:var(--fg);margin-left:8px" onclick="loadData()">🔄 Atualizar</button>
<div class="ts" id="status"></div>

<script>
const FMT = n => n >= 1e6 ? (n/1e6).toFixed(1)+'M' : n >= 1e3 ? (n/1e3).toFixed(0)+'k' : String(n);
async function loadData(){
  const r = await fetch('/api/status');
  const d = await r.json();
  if(!d.snap){ document.getElementById('status').textContent='Nenhum dado ainda — aguardando primeiro fetch...'; return; }
  const s = d.snap;
  document.getElementById('t-total').textContent = FMT(s.total_tokens||0);
  document.getElementById('t-cost').textContent  = 'US$ '+(s.cost_usd||0).toFixed(4);
  document.getElementById('t-days').textContent  = d.days_left ?? '—';
  document.getElementById('t-pct').textContent   = d.pct ? d.pct.toFixed(1)+'%' : '—';
  if(d.limit > 0){
    document.getElementById('bar-wrap').style.display='block';
    document.getElementById('bar-fill').style.width = Math.min(d.pct,100)+'%';
    document.getElementById('bar-val').textContent  = FMT(s.total_tokens)+' / '+FMT(d.limit);
    document.getElementById('bar-period').textContent = 'Período: '+(s.period_start||'?')+' → '+(s.period_end||'?');
  }
  // history chart
  const hist = d.history || [];
  const max = Math.max(...hist.map(h=>h.tokens), 1);
  const container = document.getElementById('hist-bars');
  container.innerHTML = hist.slice().reverse().map(h=>`<div class="bar-day" style="height:${Math.round(h.tokens/max*56)+4}px" title="${h.day}: ${FMT(h.tokens)}"></div>`).join('');
  document.getElementById('status').textContent = 'Atualizado: '+new Date().toLocaleTimeString();
}
async function testTelegram(){
  const r = await fetch('/api/test-telegram', {method:'POST'});
  const d = await r.json();
  document.getElementById('status').textContent = d.ok ? '✅ Mensagem enviada!' : '❌ Erro: '+d.error;
}
loadData();
setInterval(loadData, 60000);
</script>
</body>
</html>"""


# ── ROUTES ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/status")
def api_status():
    snap = db.get_latest_snapshot()
    history = db.get_daily_history(7)
    pct = None
    days_left = None
    if snap and TOKEN_LIMIT > 0:
        pct = snap["total_tokens"] / TOKEN_LIMIT * 100
    if snap and snap.get("period_end"):
        try:
            end = datetime.fromisoformat(snap["period_end"])
            days_left = (end.date() - datetime.utcnow().date()).days
        except Exception:
            pass
    return jsonify(snap=snap, pct=pct, limit=TOKEN_LIMIT, days_left=days_left, history=history)


@app.route("/api/test-telegram", methods=["POST"])
def api_test_telegram():
    try:
        tg.test_connection()
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e))


# ── MAIN ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()

    hour, minute = DAILY_REPORT_TIME.split(":")
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(job_fetch, "interval", minutes=FETCH_INTERVAL_MIN, next_run_time=datetime.now(timezone.utc))
    scheduler.add_job(job_daily_report, "cron", hour=int(hour), minute=int(minute))
    scheduler.start()

    print(f"[monitor] dashboard em http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
