import os
import requests
from datetime import datetime
import pytz
from supabase import create_client

# 1. Credenciais (Injetadas pelo GitHub de forma segura)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
fuso_br = pytz.timezone('America/Sao_Paulo')
agora = datetime.now(fuso_br)
data_hoje = agora.strftime('%Y-%m-%d')
hora_atual = agora.hour

# 2. Lógica para descobrir qual a hora que acabou de fechar
def obter_slot_analise(hora_execucao):
    # O script roda aos 5 minutos de cada hora. 
    # Se roda às 10:05, analisa o slot das 09:00.
    mapa_slots = {
        8: "07:15", 9: "08:00", 10: "09:00", 11: "10:00",
        12: "11:00", 14: "13:00", 15: "14:00", 16: "15:00", 17: "16:00"
    }
    return mapa_slots.get(hora_execucao)

slot = obter_slot_analise(hora_atual)

if not slot:
    print(f"Hora atual ({hora_atual}h) fora da janela de notificação. Fim do script.")
    exit()

# 3. Puxar Dados da Nuvem
res_carga = supabase.table("horaria_carga").select("*").eq("data_id", data_hoje).eq("hora", slot).execute()
res_perf = supabase.table("horaria_perf").select("*").eq("data_id", data_hoje).eq("hora", slot).execute()
res_paradas = supabase.table("registros_parciais").select("*").eq("data", data_hoje).eq("hora", slot).eq("tipo_registro", "Parada").execute()

# 4. Formatar os Valores
v_carga_real = 0
v_carga_meta = 0
v_perf_real = 0.0
v_perf_meta = 0.0

if res_carga.data:
    linha_c = res_carga.data[0]
    v_carga_meta = linha_c.get('meta', 0)
    cols_ut = [c for c in linha_c.keys() if 'ut' in c.lower()]
    v_carga_real = sum([linha_c[c] for c in cols_ut if isinstance(linha_c[c], (int, float))])

if res_perf.data:
    linha_p = res_perf.data[0]
    v_perf_meta = linha_p.get('meta', 0)
    v_perf_real = linha_p.get('realizado', 0.0)

alcance_carga = (v_carga_real / v_carga_meta * 100) if v_carga_meta > 0 else 0
alcance_perf = (v_perf_real / v_perf_meta * 100) if v_perf_meta > 0 else 0

def semaforo(pct):
    if pct >= 100: return "🟢"
    elif pct >= 80: return "🟡"
    return "🔴"

# 5. Construir o Boletim Visual
msg = f"📊 <b>BOLETIM PCP PETRA | HORA: {slot}</b>\n"
msg += f"📅 {agora.strftime('%d/%m/%Y')}\n\n"

msg += f"🚜 <b>CARGA (Caminhões)</b>\n"
msg += f"• Meta: {int(v_carga_meta)} viag.\n"
msg += f"• Realizado: {int(v_carga_real)} viag.\n"
msg += f"• Alcance: {alcance_carga:.0f}% {semaforo(alcance_carga)}\n\n"

msg += f"🎯 <b>PERFURAÇÃO</b>\n"
msg += f"• Meta: {v_perf_meta:.1f} m\n"
msg += f"• Realizado: {v_perf_real:.1f} m\n"
msg += f"• Alcance: {alcance_perf:.0f}% {semaforo(alcance_perf)}\n\n"

msg += f"🛑 <b>OCORRÊNCIAS / PARADAS</b>\n"
if res_paradas.data:
    for p in res_paradas.data:
        eq = p.get('equipamento', 'Desconhecido')
        d = p.get('detalhes', {})
        motivo = d.get('motivo', 'Sem motivo')
        h_ini = d.get('inicio', '--:--')
        h_fim = d.get('fim', '--:--')
        msg += f"• {eq}: {motivo} ({h_ini} - {h_fim})\n"
else:
    msg += "• Nenhuma parada registada nesta hora.\n"

# 6. Disparar para o Telegram
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
resposta = requests.post(url, json=payload)
print("Enviado com sucesso:", resposta.status_code)
