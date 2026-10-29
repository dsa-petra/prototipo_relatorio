import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import calendar
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from supabase import create_client

# ==========================================
# 1. CONFIGURAÇÃO GLOBAL E ESTILOS
# ==========================================
st.set_page_config(page_title="Sistema PCP Petra", layout="wide", page_icon="⚙️")
st_autorefresh(interval=15000, limit=None, key="atualizacao_continua")

COR_AZUL = "#54728c"
COR_AMARELA = "#ffc107"
COR_FUNDO = "rgba(0,0,0,0)"

st.markdown(f"""
    <style>
    .kpi-card {{ background-color: {COR_AZUL}; color: white; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid {COR_AMARELA}; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }}
    .kpi-title {{ font-size: 1.1rem; margin-bottom: 5px; opacity: 0.9; }}
    .kpi-value {{ font-size: 2.5rem; font-weight: bold; color: {COR_AMARELA}; margin: 0; }}
    
    .login-box {{ background: linear-gradient(135deg, #ffffff 0%, #f4f6f9 100%); padding: 50px 30px; border-radius: 20px; box-shadow: 0px 20px 40px rgba(0,0,0,0.08); border-top: 8px solid {COR_AZUL}; margin-top: 50px; }}
    .login-title {{ text-align: center; color: {COR_AZUL}; font-weight: 800; font-size: 32px; margin-bottom: 5px; letter-spacing: -1px; }}
    
    .meta-box {{ background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid {COR_AZUL}; margin-bottom: 20px; box-shadow: inset 0px 2px 5px rgba(0,0,0,0.05); display: flex; justify-content: space-around; text-align: center; }}
    .meta-titulo {{ font-size: 16px; color: #7f8c8d; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }}
    .meta-destaque {{ font-size: 28px; font-weight: bold; color: {COR_AZUL}; display: block; margin-top: 5px;}}
    
    button:has(p:contains("➕")) {{ background: linear-gradient(180deg, #00e676 0%, #00c853 100%) !important; color: white !important; height: 100px !important; border-radius: 25px !important; border: 2px solid #00a042 !important; box-shadow: 0px 8px 15px rgba(0,200,83,0.3) !important; transition: all 0.2s !important; }}
    button:has(p:contains("➕")):active {{ transform: translateY(4px) !important; box-shadow: 0px 4px 10px rgba(0,200,83,0.3) !important; }}
    button:has(p:contains("➕")) p {{ font-size: 50px !important; font-weight: bold; margin: 0; }}
    
    button:has(p:contains("➖")) {{ background: linear-gradient(180deg, #ff5252 0%, #ff1744 100%) !important; color: white !important; height: 100px !important; border-radius: 25px !important; border: 2px solid #d50000 !important; box-shadow: 0px 8px 15px rgba(255,23,68,0.3) !important; transition: all 0.2s !important; }}
    button:has(p:contains("➖")):active {{ transform: translateY(4px) !important; box-shadow: 0px 4px 10px rgba(255,23,68,0.3) !important; }}
    button:has(p:contains("➖")) p {{ font-size: 50px !important; font-weight: bold; margin: 0; line-height: 50px; }}
    
    .dir-card {{ background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 4px solid {COR_AZUL}; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    .dir-titulo {{ font-size: 14px; color: #6c757d; font-weight: bold; text-transform: uppercase; }}
    .dir-valor {{ font-size: 24px; font-weight: 900; color: {COR_AZUL}; margin-top: 5px; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXÃO E ESTADO
# ==========================================
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase = init_connection()
except Exception:
    st.error("Erro ao conectar com o banco de dados.")
    st.stop()

if "usuario" not in st.session_state: st.session_state.usuario = None
if "perfil" not in st.session_state: st.session_state.perfil = None
if "tela_atual" not in st.session_state: st.session_state.tela_atual = "login"
if "tag_equipamento" not in st.session_state: st.session_state.tag_equipamento = None
if "tipo_equipamento" not in st.session_state: st.session_state.tipo_equipamento = None
if "slot_selecionado_estado" not in st.session_state: st.session_state.slot_selecionado_estado = None
if "incremento_val" not in st.session_state: st.session_state.incremento_val = 0

HORARIOS_TURNO = ["06:15", "07:00", "08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00"]
INTERVALOS = {
    "06:15": "06:15 - 07:00", "07:00": "07:00 - 08:00", "08:00": "08:00 - 09:00", 
    "09:00": "09:00 - 10:00", "10:00": "10:00 - 11:00", "11:00": "11:00 - 12:00", 
    "13:00": "13:00 - 14:00", "14:00": "14:00 - 15:00", "15:00": "15:00 - 16:00"
}

def obter_horario_sugerido():
    agora = datetime.now()
    hora = agora.hour
    if 6 <= hora < 7: return "06:15"
    elif 7 <= hora < 8: return "07:00"
    elif 8 <= hora < 9: return "08:00"
    elif 9 <= hora < 10: return "09:00"
    elif 10 <= hora < 11: return "10:00"
    elif 11 <= hora < 12: return "11:00"
    elif 13 <= hora < 14: return "13:00"
    elif 14 <= hora < 15: return "14:00"
    elif 15 <= hora < 16: return "15:00"
    else: return "06:15"

def carregar_dados_gestor():
    df_c = pd.DataFrame(supabase.table("horaria_carga").select("*").execute().data)
    df_p = pd.DataFrame(supabase.table("horaria_perf").select("*").execute().data)
    df_pt = pd.DataFrame(supabase.table("parte_diaria").select("*").execute().data)
    df_pcp = pd.DataFrame(supabase.table("pcp_planejamento").select("*").execute().data)
    df_rp = pd.DataFrame(supabase.table("registros_parciais").select("*").execute().data)
    return df_c, df_p, df_pt, df_pcp, df_rp

def destacar_linha_total(row):
    if row['HORA'] == 'TOTAL':
        return ['background-color: #334155; font-weight: bold; color: #ffc107'] * len(row)
    return [''] * len(row)

# ==========================================
# 3. TELAS DO SISTEMA
# ==========================================

def tela_login():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.image("https://via.placeholder.com/600x150.png?text=PETRA+AGREGADOS", use_container_width=True)
        st.markdown("<div class='login-title'>FMS Petra</div>", unsafe_allow_html=True)
        
        with st.form("form_login"):
            usuario = st.text_input("👤 Nome de Usuário:")
            senha = st.text_input("🔑 Senha de Acesso:", type="password")
            st.write("")
            if st.form_submit_button("Acessar o Sistema", use_container_width=True):
                user_limpo = usuario.lower().strip()
                res = supabase.table("usuarios").select("*").eq("login", user_limpo).eq("senha", senha).eq("ativo", True).execute()
                if res.data:
                    user_data = res.data[0]
                    st.session_state.usuario = user_data["nome"]
                    st.session_state.perfil = user_data["perfil"]
                    st.session_state.tela_atual = "gestor" if user_data["perfil"] == "gestor" else "selecao_maquina"
                    st.rerun()
                else:
                    st.error("⚠️ Credenciais inválidas.")
        st.markdown("</div>", unsafe_allow_html=True)

def tela_selecao_maquina():
    st.markdown(f"<h3 style='text-align:center; color:{COR_AZUL};'>Olá, {st.session_state.usuario}</h3>", unsafe_allow_html=True)
    res_eq = supabase.table("equipamentos").select("*").eq("ativo", True).execute()
    df_eq = pd.DataFrame(res_eq.data) if res_eq.data else pd.DataFrame()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_maquina"):
            if not df_eq.empty:
                tag_selecionada = st.selectbox("Em qual máquina você vai operar?", df_eq["tag"].tolist())
                if st.form_submit_button("Iniciar Operação 🚜", use_container_width=True):
                    st.session_state.tag_equipamento = tag_selecionada
                    st.session_state.tipo_equipamento = df_eq[df_eq["tag"] == tag_selecionada].iloc[0]["tipo"]
                    st.session_state.tela_atual = "operacao"
                    st.session_state.slot_selecionado_estado = obter_horario_sugerido()
                    st.session_state.incremento_val = 0 
                    st.rerun()
            else:
                st.warning("Nenhum equipamento cadastrado.")

def tela_operacao():
    data_hoje = datetime.now().strftime('%Y-%m-%d')
    e_caminhao = (st.session_state.tipo_equipamento == "carga")
    
    st.markdown(f"**👤 {st.session_state.usuario}** | **🚜 {st.session_state.tag_equipamento}**")
    
    if st.session_state.slot_selecionado_estado not in HORARIOS_TURNO:
        st.session_state.slot_selecionado_estado = obter_horario_sugerido()
    
    st.markdown("### ⏰ Selecione o Período do Apontamento")
    
    opcoes_intervalos = [INTERVALOS[h] for h in HORARIOS_TURNO]
    idx_atual = HORARIOS_TURNO.index(st.session_state.slot_selecionado_estado)
    
    intervalo_selecionado = st.selectbox("Período:", opcoes_intervalos, index=idx_atual)
    slot_atual = HORARIOS_TURNO[opcoes_intervalos.index(intervalo_selecionado)]
    
    if slot_atual != st.session_state.slot_selecionado_estado:
        st.session_state.slot_selecionado_estado = slot_atual
        st.session_state.incremento_val = 0
        st.rerun()

    # Botoes Superiores
    c_check, c_parada, c_abastecimento = st.columns(3)
    with c_check:
        with st.popover("📋 Checklist", use_container_width=True):
            res_chk = supabase.table("itens_checklist").select("item").in_("tipo_equipamento", [st.session_state.tipo_equipamento, 'ambos']).execute()
            respostas_chk = {linha['item']: st.selectbox(f"{linha['item']}:", ["OK", "Atenção", "Crítico"], key=f"chk_{i}") for i, linha in enumerate(res_chk.data or [])}
            if st.button("Enviar ao PCP", use_container_width=True):
                supabase.table("registros_parciais").insert({"data": data_hoje, "hora": slot_atual, "equipamento": st.session_state.tag_equipamento, "operador": st.session_state.usuario, "tipo_registro": "Checklist", "detalhes": respostas_chk}).execute()
                st.success("Enviado!")

    with c_parada:
        with st.popover("🛑 Parada", use_container_width=True):
            res_par = supabase.table("motivos_parada").select("motivo").in_("tipo_equipamento", [st.session_state.tipo_equipamento, 'ambos']).execute()
            opcoes_parada = [m['motivo'] for m in res_par.data] if res_par.data else ["Nenhuma"]
            motivo_sel = st.selectbox("Motivo:", opcoes_parada)
            c_h1, c_h2 = st.columns(2)
            hora_inicio = c_h1.time_input("Início")
            hora_fim = c_h2.time_input("Fim")
            if st.button("Avisar PCP", use_container_width=True):
                h_ini_str = hora_inicio.strftime("%H:%M")
                h_fim_str = hora_fim.strftime("%H:%M")
                detalhes_parada = {"motivo": motivo_sel, "inicio": h_ini_str, "fim": h_fim_str}
                supabase.table("registros_parciais").insert({"data": data_hoje, "hora": slot_atual, "equipamento": st.session_state.tag_equipamento, "operador": st.session_state.usuario, "tipo_registro": "Parada", "detalhes": detalhes_parada}).execute()
                tabela_gestor = "horaria_carga" if e_caminhao else "horaria_perf"
                supabase.table(tabela_gestor).update({"causa": f"{motivo_sel} ({h_ini_str}-{h_fim_str})"}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                st.success("Parada registrada!")

    with c_abastecimento:
        with st.popover("⛽ Abastecimento", use_container_width=True):
            litros = st.number_input("Litros:", min_value=0.0, step=1.0)
            horimetro_abast = st.number_input("Horímetro Atual:", min_value=0.0, step=0.1)
            if st.button("Gravar Abastecimento", use_container_width=True):
                detalhes_abast = {"litros": litros, "horimetro": horimetro_abast}
                supabase.table("registros_parciais").insert({"data": data_hoje, "hora": slot_atual, "equipamento": st.session_state.tag_equipamento, "operador": st.session_state.usuario, "tipo_registro": "Abastecimento", "detalhes": detalhes_abast}).execute()
                st.success("Abastecimento gravado!")

    st.write("---")

    # Tela Apontamento
    res_pcp = supabase.table("pcp_planejamento").select("*").eq("data", data_hoje).execute()
    meta_viagens = res_pcp.data[0]['meta_viagens_equipe_hora'] if res_pcp.data else 0
    meta_metros = res_pcp.data[0]['meta_perf_metros_hora'] if res_pcp.data else 0.0

    if e_caminhao:
        coluna_db = st.session_state.tag_equipamento.lower().replace("-", "")
        res_hora = supabase.table("horaria_carga").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()
        if not res_hora.data:
            supabase.table("horaria_carga").insert({"data_id": data_hoje, "hora": slot_atual, "ut33": 0, "ut34": 0, "meta": meta_viagens, "causa": ""}).execute()
            res_hora = supabase.table("horaria_carga").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()
        
        df_hora = pd.DataFrame(res_hora.data)
        valor_db_atual = int(df_hora.iloc[0][coluna_db]) if coluna_db in df_hora.columns else 0
        valor_equipe_atual = sum([df_hora.iloc[0][col] for col in df_hora.columns if 'ut' in col.lower()])
        
        st.markdown(f"<div class='meta-box'><div><span class='meta-titulo'>META DA HORA (P)</span><span class='meta-destaque'>{meta_viagens if meta_viagens>0 else 'N/A'} viag.</span></div><div><span class='meta-titulo'>REALIZADO EQUIPE (R)</span><span class='meta-destaque'>{valor_equipe_atual} viag.</span></div></div>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#7f8c8d; font-weight:bold; margin-bottom:-5px;'>Lançamento Manual (Viagens):</p>", unsafe_allow_html=True)
        
        c_menos, c_valor, c_mais = st.columns([1, 2, 1])
        with c_menos:
            if st.button("➖", key="sub_v", use_container_width=True):
                st.session_state.incremento_val = max(0, int(st.session_state.incremento_val) - 1)
                st.rerun()
        with c_valor:
            val_input = st.number_input("Lancamento", value=int(st.session_state.incremento_val), step=1, format="%d", label_visibility="collapsed")
            if val_input != st.session_state.incremento_val: st.session_state.incremento_val = val_input
        with c_mais:
            if st.button("➕", key="add_v", use_container_width=True):
                st.session_state.incremento_val = int(st.session_state.incremento_val) + 1
                st.rerun()
                
        st.write("")
        if st.button("🚀 Lançar Apontamento e Zerar", use_container_width=True, type="primary"):
            if st.session_state.incremento_val > 0:
                novo_valor = valor_db_atual + st.session_state.incremento_val
                supabase.table("horaria_carga").update({coluna_db: novo_valor}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                st.session_state.incremento_val = 0 
                st.success("✔️ Salvo!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("O valor deve ser maior que zero.")
            
    else: 
        res_hora = supabase.table("horaria_perf").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()
        if not res_hora.data:
            supabase.table("horaria_perf").insert({"data_id": data_hoje, "hora": slot_atual, "realizado": 0.0, "meta": meta_metros, "causa": ""}).execute()
            res_hora = supabase.table("horaria_perf").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()

        valor_db_atual = float(res_hora.data[0]['realizado'])
            
        st.markdown(f"<div class='meta-box'><div><span class='meta-titulo'>META DA HORA (P)</span><span class='meta-destaque'>{meta_metros if meta_metros>0 else 'N/A'} m</span></div><div><span class='meta-titulo'>REALIZADO ACUMULADO (R)</span><span class='meta-destaque'>{valor_db_atual:.1f} m</span></div></div>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#7f8c8d; font-weight:bold; margin-bottom:-5px;'>Lançamento Manual (Metros):</p>", unsafe_allow_html=True)

        c_menos, c_valor, c_mais = st.columns([1, 2, 1])
        with c_menos:
            if st.button("➖", key="sub_p", use_container_width=True):
                st.session_state.incremento_val = max(0.0, float(st.session_state.incremento_val) - 1.0)
                st.rerun()
        with c_valor:
            val_input = st.number_input("Lancamento", value=float(st.session_state.incremento_val), step=1.0, format="%.1f", label_visibility="collapsed")
            if val_input != st.session_state.incremento_val: st.session_state.incremento_val = val_input
        with c_mais:
            if st.button("➕", key="add_p", use_container_width=True):
                st.session_state.incremento_val = float(st.session_state.incremento_val) + 1.0
                st.rerun()
                
        st.write("")
        if st.button("🚀 Lançar Apontamento e Zerar", use_container_width=True, type="primary"):
            if st.session_state.incremento_val > 0:
                novo_valor = valor_db_atual + st.session_state.incremento_val
                supabase.table("horaria_perf").update({"realizado": novo_valor}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                st.session_state.incremento_val = 0 
                st.success("✔️ Salvo!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("O valor deve ser maior que zero.")

    st.write("---")
    
    with st.expander("📝 Preencher Relatório Diário (Fechamento)", expanded=False):
        with st.form("form_parte_diaria"):
            col_hm1, col_hm2 = st.columns(2)
            h_inicial = col_hm1.number_input("Horímetro Motor (Inicial):", min_value=0.0, step=0.1)
            h_final = col_hm2.number_input("Horímetro Motor (Final):", min_value=0.0, step=0.1)
            
            hm_inicial, hm_final = 0.0, 0.0
            if not e_caminhao:
                st.markdown("---")
                col_hmt1, col_hmt2 = st.columns(2)
                hm_inicial = col_hmt1.number_input("Horímetro Martelo (Inicial):", min_value=0.0, step=0.1)
                hm_final = col_hmt2.number_input("Horímetro Martelo (Final):", min_value=0.0, step=0.1)
                
            obs = st.text_area("Observações Gerais (Opcional):")
            
            if st.form_submit_button("✅ Enviar e Fechar Parte Diária", use_container_width=True):
                if h_final >= h_inicial:
                    dados = {
                        "data": data_hoje, "equipamento": st.session_state.tag_equipamento, "operador": st.session_state.usuario,
                        "horimetro_inicial": h_inicial, "horimetro_final": h_final, "observacoes": obs
                    }
                    if not e_caminhao:
                        dados["horimetro_martelo_inicial"] = hm_inicial
                        dados["horimetro_martelo_final"] = hm_final
                    supabase.table("parte_diaria").insert(dados).execute()
                    st.success("Relatório de Turno enviado com sucesso!")
                else:
                    st.error("Erro: O Horímetro Final é menor que o Inicial.")

def tela_gestor():
    col_logo, col_titulo = st.columns([1, 4])
    with col_titulo:
        st.markdown(f"<h1 style='color: {COR_AZUL};'>📊 Painel de Controle - Operação</h1>", unsafe_allow_html=True)
    st.divider()

    df_carga, df_perf, df_parte, df_pcp, df_rp = carregar_dados_gestor()
    data_hoje_str = datetime.today().strftime('%Y-%m-%d')
    
    # Cálculos KPI Hoje
    df_carga_hoje = df_carga[df_carga['data_id'] == data_hoje_str] if not df_carga.empty else pd.DataFrame()
    df_perf_hoje = df_perf[df_perf['data_id'] == data_hoje_str] if not df_perf.empty else pd.DataFrame()
    
    cols_ut = [c for c in df_carga_hoje.columns if 'ut' in c.lower()] if not df_carga_hoje.empty else []
    total_viagens = df_carga_hoje[cols_ut].sum().sum() if not df_carga_hoje.empty else 0
    meta_viagens = df_carga_hoje['meta'].sum() if not df_carga_hoje.empty else 0
    
    total_metros = df_perf_hoje['realizado'].sum() if not df_perf_hoje.empty else 0
    meta_metros = df_perf_hoje['meta'].sum() if not df_perf_hoje.empty else 0

    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='kpi-card'><p class='kpi-title'>Viagens (Realizado / Planejado)</p><p class='kpi-value'>🚛 {int(total_viagens)} / {int(meta_viagens)}</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-card'><p class='kpi-title'>Metros (Realizado / Planejado)</p><p class='kpi-value'>🎯 {total_metros:.1f} / {meta_metros:.1f}</p></div>", unsafe_allow_html=True)
    st.write("") 

    aba_pcp, aba_diretoria, aba_dados, aba_config = st.tabs(["📋 Acompanhamento Diário", "📊 Visão Diretoria", "🗄️ Dados Brutos", "🛠️ Cadastros"])

    with aba_pcp:
        # Formato de Data Brasileiro (DD/MM/YYYY)
        dia_alvo = st.date_input("📅 Selecionar Data:", datetime.today(), format="DD/MM/YYYY")
        dia_alvo_str = dia_alvo.strftime("%Y-%m-%d")
        
        # Edição de Horários e Metas
        with st.expander("⚙️ Ajustar Horários e Metas (Planejado)", expanded=False):
            with st.form("form_edit_metas"):
                st.write(f"Atualize o planejamento para uma hora específica do dia **{dia_alvo.strftime('%d/%m/%Y')}**:")
                c_edit1, c_edit2, c_edit3 = st.columns(3)
                
                # Exibir os intervalos no seletor, mas o valor real é a hora base
                opcoes_edit = [INTERVALOS[h] for h in HORARIOS_TURNO]
                intervalo_edit = c_edit1.selectbox("Período:", opcoes_edit)
                hora_edit = HORARIOS_TURNO[opcoes_edit.index(intervalo_edit)]
                
                linha_c_edit = df_carga[(df_carga['data_id'] == dia_alvo_str) & (df_carga['hora'] == hora_edit)] if not df_carga.empty else pd.DataFrame()
                linha_p_edit = df_perf[(df_perf['data_id'] == dia_alvo_str) & (df_perf['hora'] == hora_edit)] if not df_perf.empty else pd.DataFrame()
                
                meta_v_atual = int(linha_c_edit.iloc[0]['meta']) if not linha_c_edit.empty else 0
                meta_m_atual = float(linha_p_edit.iloc[0]['meta']) if not linha_p_edit.empty else 0.0
                
                nova_meta_v = c_edit2.number_input("Meta Carga (Viagens):", value=meta_v_atual, step=1)
                nova_meta_m = c_edit3.number_input("Meta Perfuração (Metros):", value=meta_m_atual, step=1.0)
                
                if st.form_submit_button("💾 Salvar Ajustes"):
                    # Força a inserção da linha caso a hora ainda não exista no banco naquele dia
                    if linha_c_edit.empty:
                        supabase.table("horaria_carga").insert({"data_id": dia_alvo_str, "hora": hora_edit, "meta": nova_meta_v, "ut33": 0, "ut34": 0, "causa": ""}).execute()
                    else:
                        supabase.table("horaria_carga").update({"meta": nova_meta_v}).eq("data_id", dia_alvo_str).eq("hora", hora_edit).execute()
                        
                    if linha_p_edit.empty:
                        supabase.table("horaria_perf").insert({"data_id": dia_alvo_str, "hora": hora_edit, "meta": nova_meta_m, "realizado": 0.0, "causa": ""}).execute()
                    else:
                        supabase.table("horaria_perf").update({"meta": nova_meta_m}).eq("data_id", dia_alvo_str).eq("hora", hora_edit).execute()
                        
                    st.success("Metas atualizadas com sucesso!")
                    time.sleep(1)
                    st.rerun()
        
        st.write("---")

        # Tabela Carga
        st.markdown(f"<h3 style='color:{COR_AZUL}; text-align:center;'>🚜 Operação de Carga - {dia_alvo.strftime('%d/%m/%Y')}</h3>", unsafe_allow_html=True)
        df_carga_alvo = df_carga[df_carga['data_id'] == dia_alvo_str] if not df_carga.empty else pd.DataFrame()
        
        if not df_carga_alvo.empty:
            caminhoes_op = []
            for col in df_carga_alvo.columns:
                if 'ut' in col.lower() and df_carga_alvo[col].sum() > 0:
                    caminhoes_op.append(col.upper())
            
            tabela_excel = []
            totais_dict = {cam: 0 for cam in caminhoes_op}
            totais_dict["REALIZADO"] = 0
            totais_dict["PLANEJADO"] = 0
            
            for hora in HORARIOS_TURNO:
                linha = df_carga_alvo[df_carga_alvo['hora'] == hora]
                linha_dados = {"HORA": INTERVALOS[hora]}
                
                realizado_h = 0
                for cam in caminhoes_op:
                    val_c = linha.iloc[0][cam.lower()] if not linha.empty and cam.lower() in linha.columns else 0
                    linha_dados[cam] = val_c
                    realizado_h += val_c
                    totais_dict[cam] += val_c
                
                meta = linha.iloc[0]['meta'] if not linha.empty else 0
                
                linha_dados["REALIZADO"] = realizado_h
                linha_dados["PLANEJADO"] = meta
                pct = f"{(realizado_h / meta * 100):.0f}%" if meta > 0 else "0%"
                linha_dados["% DESEMPENHO"] = pct
                
                tabela_excel.append(linha_dados)
                totais_dict["REALIZADO"] += realizado_h
                totais_dict["PLANEJADO"] += meta
            
            linha_total = {"HORA": "TOTAL"}
            for cam in caminhoes_op: linha_total[cam] = totais_dict[cam]
            linha_total["REALIZADO"] = totais_dict["REALIZADO"]
            linha_total["PLANEJADO"] = totais_dict["PLANEJADO"]
            pct_total = f"{(totais_dict['REALIZADO'] / totais_dict['PLANEJADO'] * 100):.0f}%" if totais_dict["PLANEJADO"] > 0 else "0%"
            linha_total["% DESEMPENHO"] = pct_total
            
            tabela_excel.append(linha_total)
            
            df_ex = pd.DataFrame(tabela_excel)
            st.dataframe(df_ex.style.apply(destacar_linha_total, axis=1), use_container_width=True, hide_index=True)
        else:
            st.warning("Sem dados de produção (carga) para o dia selecionado.")
            
        st.write("---")
        
        # Tabela Perfuração
        st.markdown(f"<h3 style='color:{COR_AZUL}; text-align:center;'>🎯 Operação de Perfuração - {dia_alvo.strftime('%d/%m/%Y')}</h3>", unsafe_allow_html=True)
        df_perf_alvo = df_perf[df_perf['data_id'] == dia_alvo_str] if not df_perf.empty else pd.DataFrame()
        
        if not df_perf_alvo.empty:
            tabela_perf = []
            totais_p = {"REALIZADO": 0, "PLANEJADO": 0}
            
            for hora in HORARIOS_TURNO:
                linha = df_perf_alvo[df_perf_alvo['hora'] == hora]
                
                realizado_p = float(linha.iloc[0]['realizado']) if not linha.empty else 0.0
                meta_p = float(linha.iloc[0]['meta']) if not linha.empty else 0.0
                pct_p = f"{(realizado_p / meta_p * 100):.0f}%" if meta_p > 0 else "0%"
                
                tabela_perf.append({
                    "HORA": INTERVALOS[hora],
                    "REALIZADO": realizado_p,
                    "PLANEJADO": meta_p,
                    "% DESEMPENHO": pct_p
                })
                totais_p["REALIZADO"] += realizado_p
                totais_p["PLANEJADO"] += meta_p
            
            pct_total_p = f"{(totais_p['REALIZADO'] / totais_p['PLANEJADO'] * 100):.0f}%" if totais_p["PLANEJADO"] > 0 else "0%"
            
            tabela_perf.append({
                "HORA": "TOTAL",
                "REALIZADO": totais_p["REALIZADO"],
                "PLANEJADO": totais_p["PLANEJADO"],
                "% DESEMPENHO": pct_total_p
            })
            
            df_ex_p = pd.DataFrame(tabela_perf)
            # Formatar a coluna Realizado para ter 1 casa decimal no pandas
            df_ex_p['REALIZADO'] = df_ex_p['REALIZADO'].apply(lambda x: f"{x:.1f}" if isinstance(x, float) else x)
            st.dataframe(df_ex_p.style.apply(destacar_linha_total, axis=1), use_container_width=True, hide_index=True)
        else:
            st.warning("Sem dados de perfuração para o dia selecionado.")

    with aba_diretoria:
        st.markdown(f"<h3 style='color:{COR_AZUL};'>Indicadores de Desempenho</h3>", unsafe_allow_html=True)
        filtro_mes = st.selectbox("Mês de Referência:", [datetime.today().strftime('%Y-%m')] + sorted(list(set(pd.to_datetime(df_rp['data']).dt.strftime('%Y-%m')) if not df_rp.empty else []), reverse=True))
        
        df_c_dir = df_carga[df_carga['data_id'].str.startswith(filtro_mes)] if not df_carga.empty else pd.DataFrame()
        df_p_dir = df_perf[df_perf['data_id'].str.startswith(filtro_mes)] if not df_perf.empty else pd.DataFrame()
        df_pt_dir = df_parte[df_parte['data'].str.startswith(filtro_mes)] if not df_parte.empty else pd.DataFrame()
        df_rp_dir = df_rp[df_rp['data'].str.startswith(filtro_mes)] if not df_rp.empty else pd.DataFrame()
        
        t_metros = df_p_dir['realizado'].sum() if not df_p_dir.empty else 0
        h_perf = len(df_p_dir[df_p_dir['realizado'] > 0]) if not df_p_dir.empty else 0
        metros_h = t_metros / h_perf if h_perf > 0 else 0
        
        cols_ut_dir = [c for c in df_c_dir.columns if 'ut' in c.lower()] if not df_c_dir.empty else []
        t_viag = df_c_dir[cols_ut_dir].sum().sum() if not df_c_dir.empty else 0
        h_carga = len(df_c_dir) if not df_c_dir.empty else 0
        viag_h = t_viag / h_carga if h_carga > 0 else 0
        
        pct_martelo = "N/A"
        if not df_pt_dir.empty and 'horimetro_martelo_final' in df_pt_dir.columns:
            df_perf_pt = df_pt_dir[df_pt_dir['horimetro_martelo_final'].notna()]
            if not df_perf_pt.empty:
                t_motor = (pd.to_numeric(df_perf_pt['horimetro_final']) - pd.to_numeric(df_perf_pt['horimetro_inicial'])).sum()
                t_martelo = (pd.to_numeric(df_perf_pt['horimetro_martelo_final']) - pd.to_numeric(df_perf_pt['horimetro_martelo_inicial'])).sum()
                if t_motor > 0: pct_martelo = f"{(t_martelo / t_motor * 100):.1f}%"
        
        litros_total = 0
        if not df_rp_dir.empty:
            df_abast = df_rp_dir[df_rp_dir['tipo_registro'] == 'Abastecimento']
            for d in df_abast['detalhes']:
                if isinstance(d, dict) and 'litros' in d: litros_total += float(d['litros'])
        
        qtd_paradas = len(df_rp_dir[df_rp_dir['tipo_registro'] == 'Parada']) if not df_rp_dir.empty else 0

        c_d1, c_d2, c_d3, c_d4, c_d5 = st.columns(5)
        c_d1.markdown(f"<div class='dir-card'><div class='dir-titulo'>Metros / Hora</div><div class='dir-valor'>{metros_h:.1f} m/h</div></div>", unsafe_allow_html=True)
        c_d2.markdown(f"<div class='dir-card'><div class='dir-titulo'>Viagens / Hora</div><div class='dir-valor'>{viag_h:.1f} v/h</div></div>", unsafe_allow_html=True)
        c_d3.markdown(f"<div class='dir-card'><div class='dir-titulo'>% Utilização Martelo</div><div class='dir-valor'>{pct_martelo}</div></div>", unsafe_allow_html=True)
        c_d4.markdown(f"<div class='dir-card'><div class='dir-titulo'>Consumo Combustível</div><div class='dir-valor'>{litros_total:,.0f} L</div></div>", unsafe_allow_html=True)
        c_d5.markdown(f"<div class='dir-card'><div class='dir-titulo'>Ocorrências de Parada</div><div class='dir-valor'>{qtd_paradas}</div></div>", unsafe_allow_html=True)

    with aba_dados:
        c_t1, c_t2, c_t3, c_t4 = st.tabs(["Carga", "Perfuração", "Fechamentos", "Registros Parciais"])
        with c_t1: st.dataframe(df_carga, use_container_width=True)
        with c_t2: st.dataframe(df_perf, use_container_width=True)
        with c_t3: st.dataframe(df_parte, use_container_width=True)
        with c_t4: st.dataframe(df_rp, use_container_width=True)

    with aba_config:
        st.subheader("Gerenciar Listas do Operador")
        col_motivo, col_check = st.columns(2)
        
        with col_motivo:
            st.markdown("**🛑 Adicionar Motivo de Parada**")
            with st.form("form_add_parada"):
                novo_motivo = st.text_input("Nome do Motivo:")
                tipo_m = st.selectbox("Aplica-se a:", ["ambos", "carga", "perfuracao"], key="tm")
                if st.form_submit_button("➕ Adicionar Motivo"):
                    supabase.table("motivos_parada").insert({"motivo": novo_motivo, "tipo_equipamento": tipo_m}).execute()
                    st.success("Motivo Adicionado!")
            
            st.markdown("**🗑️ Excluir Motivo**")
            df_motivos = pd.DataFrame(supabase.table("motivos_parada").select("*").execute().data)
            if not df_motivos.empty:
                motivo_del = st.selectbox("Selecione para excluir:", df_motivos['motivo'])
                if st.button("Excluir Motivo Selecionado"):
                    supabase.table("motivos_parada").delete().eq("motivo", motivo_del).execute()
                    st.success("Excluído com sucesso!")
                    st.rerun()

        with col_check:
            st.markdown("**📋 Adicionar Item de Checklist**")
            with st.form("form_add_check"):
                novo_check = st.text_input("Nome do Item:")
                tipo_c = st.selectbox("Aplica-se a:", ["ambos", "carga", "perfuracao"], key="tc")
                if st.form_submit_button("➕ Adicionar Item"):
                    supabase.table("itens_checklist").insert({"item": novo_check, "tipo_equipamento": tipo_c}).execute()
                    st.success("Item Adicionado!")
            
            st.markdown("**🗑️ Excluir Item de Checklist**")
            df_checks = pd.DataFrame(supabase.table("itens_checklist").select("*").execute().data)
            if not df_checks.empty:
                check_del = st.selectbox("Selecione para excluir:", df_checks['item'])
                if st.button("Excluir Item Selecionado"):
                    supabase.table("itens_checklist").delete().eq("item", check_del).execute()
                    st.success("Excluído com sucesso!")
                    st.rerun()

# ==========================================
# 4. CONTROLADOR MESTRE DE ROTAS
# ==========================================
if st.session_state.perfil is not None:
    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.usuario}**")
        st.markdown(f"🔖 Nível: **{str(st.session_state.perfil).capitalize()}**")
        st.divider()
        
        if st.session_state.perfil == "gestor":
            if st.button("📊 Painel Gerencial", use_container_width=True):
                st.session_state.tela_atual = "gestor"; st.rerun()
            if st.button("📱 Simular Operador", use_container_width=True):
                st.session_state.tela_atual = "selecao_maquina"; st.rerun()
                
        st.divider()
        if st.button("🚪 Sair (Logout)", use_container_width=True):
            st.session_state.clear(); st.rerun()

if st.session_state.tela_atual == "login": tela_login()
elif st.session_state.tela_atual == "selecao_maquina": tela_selecao_maquina()
elif st.session_state.tela_atual == "operacao": tela_operacao()
elif st.session_state.tela_atual == "gestor" and st.session_state.perfil == "gestor": tela_gestor()
