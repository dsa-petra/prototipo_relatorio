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
    
    .linha-total {{ background-color: #334155; padding: 12px 20px; border-radius: 5px; color: #ffc107; font-weight: bold; display: flex; justify-content: space-between; margin-bottom: 15px; font-size: 16px; border-left: 5px solid #ffc107; }}
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
    df_rp = pd.DataFrame(supabase.table("registros_parciais").select("*").execute().data)
    df_os = pd.DataFrame(supabase.table("ordens_servico").select("*").execute().data)
    df_eq = pd.DataFrame(supabase.table("equipamentos").select("*").execute().data)
    
    if not df_c.empty and 'data_id' in df_c.columns: df_c['data_id'] = df_c['data_id'].astype(str)
    if not df_p.empty and 'data_id' in df_p.columns: df_p['data_id'] = df_p['data_id'].astype(str)
    if not df_pt.empty and 'data' in df_pt.columns: df_pt['data'] = df_pt['data'].astype(str)
    if not df_rp.empty and 'data' in df_rp.columns: df_rp['data'] = df_rp['data'].astype(str)
    if not df_os.empty and 'data_abertura' in df_os.columns: df_os['data_abertura'] = df_os['data_abertura'].astype(str)
    
    return df_c, df_p, df_pt, df_rp, df_os, df_eq

def destacar_linha_total(row):
    if row.get('HORA') == 'TOTAL' or row.get('Equipamento') == 'TOTAL':
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

    c_check, c_parada, c_abastecimento = st.columns(3)
    
    with c_check:
        with st.popover("📋 Checklist", use_container_width=True):
            res_chk = supabase.table("itens_checklist").select("item").in_("tipo_equipamento", [st.session_state.tipo_equipamento, 'ambos']).execute()
            respostas_chk = {linha['item']: st.selectbox(f"{linha['item']}:", ["OK", "Atenção", "Crítico"], key=f"chk_{i}") for i, linha in enumerate(res_chk.data or [])}
            
            if st.button("Enviar ao PCP", use_container_width=True):
                hora_exata = datetime.now().strftime("%H:%M")
                supabase.table("registros_parciais").insert({
                    "data": data_hoje, "hora": hora_exata, "equipamento": st.session_state.tag_equipamento, 
                    "operador": st.session_state.usuario, "tipo_registro": "Checklist", "detalhes": respostas_chk
                }).execute()
                
                itens_criticos = [item for item, status in respostas_chk.items() if status == "Crítico"]
                if itens_criticos:
                    for item in itens_criticos:
                        supabase.table("ordens_servico").insert({
                            "data_abertura": data_hoje, "hora_abertura": hora_exata, "equipamento": st.session_state.tag_equipamento,
                            "operador": st.session_state.usuario, "motivo": f"Checklist Crítico: {item}", "status": "ABERTA"
                        }).execute()
                    st.warning("⚠️ OS de Manutenção aberta automaticamente por item Crítico!")
                st.success("Checklist Enviado!")

    with c_parada:
        with st.popover("🛑 Parada", use_container_width=True):
            res_par = supabase.table("motivos_parada").select("motivo").in_("tipo_equipamento", [st.session_state.tipo_equipamento, 'ambos']).execute()
            opcoes_parada = [m['motivo'] for m in res_par.data] if res_par.data else ["Nenhuma"]
            motivo_sel = st.selectbox("Motivo:", opcoes_parada)
            c_h1, c_h2 = st.columns(2)
            hora_inicio = c_h1.time_input("Início da Parada")
            hora_fim = c_h2.time_input("Fim da Parada")
            
            if st.button("Avisar PCP", use_container_width=True):
                h_ini_str = hora_inicio.strftime("%H:%M")
                h_fim_str = hora_fim.strftime("%H:%M")
                detalhes_parada = {"motivo": motivo_sel, "inicio": h_ini_str, "fim": h_fim_str}
                
                supabase.table("registros_parciais").insert({
                    "data": data_hoje, "hora": h_ini_str, "equipamento": st.session_state.tag_equipamento, 
                    "operador": st.session_state.usuario, "tipo_registro": "Parada", "detalhes": detalhes_parada
                }).execute()
                
                tabela_gestor = "horaria_carga" if e_caminhao else "horaria_perf"
                supabase.table(tabela_gestor).update({"causa": f"{motivo_sel} ({h_ini_str}-{h_fim_str})"}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                st.success("Parada registrada com a Hora Inicial vinculada!")

    with c_abastecimento:
        with st.popover("⛽ Abastecimento", use_container_width=True):
            litros = st.number_input("Litros:", min_value=0.0, step=1.0)
            horimetro_abast = st.number_input("Horímetro Atual:", min_value=0.0, step=0.1)
            if st.button("Gravar Abastecimento", use_container_width=True):
                hora_exata = datetime.now().strftime("%H:%M")
                detalhes_abast = {"litros": litros, "horimetro": horimetro_abast}
                supabase.table("registros_parciais").insert({
                    "data": data_hoje, "hora": hora_exata, "equipamento": st.session_state.tag_equipamento, 
                    "operador": st.session_state.usuario, "tipo_registro": "Abastecimento", "detalhes": detalhes_abast
                }).execute()
                st.success("Abastecimento gravado!")

    st.write("---")

    # ==========================
    # APONTAMENTO DE PRODUÇÃO
    # ==========================
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
                st.session_state.incremento_val = max(0, int(st.session_state.incremento_val) - 1); st.rerun()
        with c_valor:
            val_input = st.number_input("Lancamento", value=int(st.session_state.incremento_val), step=1, format="%d", label_visibility="collapsed")
            if val_input != st.session_state.incremento_val: st.session_state.incremento_val = val_input
        with c_mais:
            if st.button("➕", key="add_v", use_container_width=True):
                st.session_state.incremento_val = int(st.session_state.incremento_val) + 1; st.rerun()
                
        st.write("")
        if st.button("🚀 Lançar Apontamento e Zerar", use_container_width=True, type="primary"):
            if st.session_state.incremento_val > 0:
                novo_valor = valor_db_atual + st.session_state.incremento_val
                supabase.table("horaria_carga").update({coluna_db: novo_valor}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                st.session_state.incremento_val = 0 
                st.success("✔️ Salvo!"); time.sleep(1); st.rerun()
            else: st.warning("O valor deve ser maior que zero.")
            
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
                st.session_state.incremento_val = max(0.0, float(st.session_state.incremento_val) - 1.0); st.rerun()
        with c_valor:
            val_input = st.number_input("Lancamento", value=float(st.session_state.incremento_val), step=1.0, format="%.1f", label_visibility="collapsed")
            if val_input != st.session_state.incremento_val: st.session_state.incremento_val = val_input
        with c_mais:
            if st.button("➕", key="add_p", use_container_width=True):
                st.session_state.incremento_val = float(st.session_state.incremento_val) + 1.0; st.rerun()
                
        st.write("")
        if st.button("🚀 Lançar Apontamento e Zerar", use_container_width=True, type="primary"):
            if st.session_state.incremento_val > 0:
                novo_valor = valor_db_atual + st.session_state.incremento_val
                supabase.table("horaria_perf").update({"realizado": novo_valor}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                st.session_state.incremento_val = 0 
                st.success("✔️ Salvo!"); time.sleep(1); st.rerun()
            else: st.warning("O valor deve ser maior que zero.")

    st.write("---")

    # ==========================
    # TABELA DE RESUMO PARA O OPERADOR
    # ==========================
    st.markdown(f"<h4 style='color:{COR_AZUL}; text-align:center;'>📊 Resumo da Operação Hoje</h4>", unsafe_allow_html=True)
    
    if e_caminhao:
        res_op_carga = supabase.table("horaria_carga").select("*").eq("data_id", data_hoje).execute().data
        df_op_carga = pd.DataFrame(res_op_carga)
        
        if not df_op_carga.empty:
            caminhoes_op = [col.upper() for col in df_op_carga.columns if 'ut' in col.lower() and df_op_carga[col].sum() > 0]
            tabela_excel = []
            
            for hora in HORARIOS_TURNO:
                linha = df_op_carga[df_op_carga['hora'] == hora]
                linha_dados = {"HORA": INTERVALOS[hora]}
                
                realizado_h = 0
                for cam in caminhoes_op:
                    val_c = linha.iloc[0][cam.lower()] if not linha.empty and cam.lower() in linha.columns else 0
                    linha_dados[cam] = val_c
                    realizado_h += val_c
                
                meta = linha.iloc[0]['meta'] if not linha.empty else 0
                linha_dados["REALIZADO"] = realizado_h
                linha_dados["PLANEJADO"] = meta
                linha_dados["% DESEMPENHO"] = f"{(realizado_h / meta * 100):.0f}%" if meta > 0 else "0%"
                tabela_excel.append(linha_dados)
            
            st.dataframe(pd.DataFrame(tabela_excel), use_container_width=True, hide_index=True)
        else:
            st.info("Ainda não existem registos de carga para o dia de hoje.")
            
    else: # Perfuração
        res_op_perf = supabase.table("horaria_perf").select("*").eq("data_id", data_hoje).execute().data
        df_op_perf = pd.DataFrame(res_op_perf)
        
        if not df_op_perf.empty:
            tabela_perf = []
            
            for hora in HORARIOS_TURNO:
                linha = df_op_perf[df_op_perf['hora'] == hora]
                realizado_p = float(linha.iloc[0]['realizado']) if not linha.empty else 0.0
                meta_p = float(linha.iloc[0]['meta']) if not linha.empty else 0.0
                
                tabela_perf.append({
                    "HORA": INTERVALOS[hora], 
                    "REALIZADO": f"{realizado_p:.1f}", 
                    "PLANEJADO": f"{meta_p:.1f}", 
                    "% DESEMPENHO": f"{(realizado_p / meta_p * 100):.0f}%" if meta_p > 0 else "0%"
                })
            
            st.dataframe(pd.DataFrame(tabela_perf), use_container_width=True, hide_index=True)
        else:
            st.info("Ainda não existem registos de perfuração para o dia de hoje.")

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
                else: st.error("Erro: O Horímetro Final é menor que o Inicial.")

def tela_gestor():
    col_logo, col_titulo = st.columns([1, 4])
    with col_titulo:
        st.markdown(f"<h1 style='color: {COR_AZUL};'>📊 Painel de Controle - Operação</h1>", unsafe_allow_html=True)
    st.divider()

    df_carga, df_perf, df_parte, df_rp, df_os, df_eq = carregar_dados_gestor()
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
    c1.markdown(f"<div class='kpi-card'><p class='kpi-title'>Viagens (Realizado / Planejado) Hoje</p><p class='kpi-value'>🚛 {int(total_viagens)} / {int(meta_viagens)}</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-card'><p class='kpi-title'>Metros (Realizado / Planejado) Hoje</p><p class='kpi-value'>🎯 {total_metros:.1f} / {meta_metros:.1f}</p></div>", unsafe_allow_html=True)
    st.write("") 

    aba_pcp, aba_manutencao, aba_diretoria, aba_dados, aba_config = st.tabs(["📋 Acompanhamento Diário", "🔧 Manutenção (OS)", "📊 Visão Diretoria", "🗄️ Dados Brutos", "🛠️ Cadastros"])

    with aba_pcp:
        dia_alvo = st.date_input("📅 Selecionar Data:", datetime.today(), format="DD/MM/YYYY")
        dia_alvo_str = dia_alvo.strftime("%Y-%m-%d")
        
        # ==========================
        # TABELA DE CARGA (EDITÁVEL)
        # ==========================
        st.markdown(f"<h3 style='color:{COR_AZUL}; text-align:center;'>🚜 Operação de Carga - {dia_alvo.strftime('%d/%m/%Y')}</h3>", unsafe_allow_html=True)
        df_carga_alvo = df_carga[df_carga['data_id'] == dia_alvo_str] if not df_carga.empty else pd.DataFrame()
        
        caminhoes_op = [col.upper() for col in df_carga_alvo.columns if 'ut' in col.lower() and df_carga_alvo[col].sum() > 0] if not df_carga_alvo.empty else []
        tabela_excel = []
        
        for hora in HORARIOS_TURNO:
            linha = df_carga_alvo[df_carga_alvo['hora'] == hora] if not df_carga_alvo.empty else pd.DataFrame()
            linha_dados = {"HORA": INTERVALOS[hora]}
            
            realizado_h = 0
            for cam in caminhoes_op:
                val_c = int(linha.iloc[0][cam.lower()]) if not linha.empty and cam.lower() in linha.columns else 0
                linha_dados[cam] = val_c
                realizado_h += val_c
            
            meta = int(linha.iloc[0]['meta']) if not linha.empty else 0
            linha_dados["REALIZADO"] = realizado_h
            linha_dados["PLANEJADO"] = meta
            linha_dados["% DESEMPENHO"] = f"{(realizado_h / meta * 100):.0f}%" if meta > 0 else "0%"
            tabela_excel.append(linha_dados)
        
        df_ex = pd.DataFrame(tabela_excel)
        
        st.markdown("💡 *Clique 2x na coluna **PLANEJADO** para editar as metas por hora.*")
        colunas_bloqueadas = [c for c in df_ex.columns if c != "PLANEJADO"]
        
        df_editado_carga = st.data_editor(df_ex, use_container_width=True, hide_index=True, disabled=colunas_bloqueadas)
        
        tot_r = int(df_editado_carga["REALIZADO"].sum()) if "REALIZADO" in df_editado_carga.columns else 0
        tot_p = int(df_editado_carga["PLANEJADO"].sum()) if "PLANEJADO" in df_editado_carga.columns else 0
        pct_t = f"{(tot_r / tot_p * 100):.0f}%" if tot_p > 0 else "0%"
        
        st.markdown(f"<div class='linha-total'><span>TOTAL CARGA</span><span>REALIZADO: {tot_r}</span><span>PLANEJADO: {tot_p}</span><span>DESEMPENHO: {pct_t}</span></div>", unsafe_allow_html=True)
        
        if st.button("💾 Gravar Novas Metas de Carga", type="primary", use_container_width=True):
            for i, row in df_editado_carga.iterrows():
                hora_base = row['HORA'].split(" - ")[0]
                nova_meta = int(row['PLANEJADO'])
                
                linha_existente = df_carga_alvo[df_carga_alvo['hora'] == hora_base] if not df_carga_alvo.empty else pd.DataFrame()
                if linha_existente.empty:
                    supabase.table("horaria_carga").insert({"data_id": dia_alvo_str, "hora": hora_base, "meta": nova_meta, "ut33": 0, "ut34": 0, "causa": ""}).execute()
                else:
                    supabase.table("horaria_carga").update({"meta": nova_meta}).eq("data_id", dia_alvo_str).eq("hora", hora_base).execute()
            st.success("Metas de Carga atualizadas na nuvem!")
            time.sleep(1); st.rerun()
            
        st.write("---")
        
        # ==========================
        # TABELA DE PERFURAÇÃO (EDITÁVEL)
        # ==========================
        st.markdown(f"<h3 style='color:{COR_AZUL}; text-align:center;'>🎯 Operação de Perfuração - {dia_alvo.strftime('%d/%m/%Y')}</h3>", unsafe_allow_html=True)
        df_perf_alvo = df_perf[df_perf['data_id'] == dia_alvo_str] if not df_perf.empty else pd.DataFrame()
        
        tabela_perf = []
        for hora in HORARIOS_TURNO:
            linha = df_perf_alvo[df_perf_alvo['hora'] == hora] if not df_perf_alvo.empty else pd.DataFrame()
            realizado_p = float(linha.iloc[0]['realizado']) if not linha.empty else 0.0
            meta_p = float(linha.iloc[0]['meta']) if not linha.empty else 0.0
            
            tabela_perf.append({
                "HORA": INTERVALOS[hora], 
                "REALIZADO": realizado_p, 
                "PLANEJADO": meta_p, 
                "% DESEMPENHO": f"{(realizado_p / meta_p * 100):.0f}%" if meta_p > 0 else "0%"
            })
        
        df_ex_p = pd.DataFrame(tabela_perf)
        
        st.markdown("💡 *Clique 2x na coluna **PLANEJADO** para editar as metas por hora.*")
        
        df_editado_perf = st.data_editor(
            df_ex_p, use_container_width=True, hide_index=True,
            disabled=["HORA", "REALIZADO", "% DESEMPENHO"],
            column_config={"REALIZADO": st.column_config.NumberColumn(format="%.1f m"), "PLANEJADO": st.column_config.NumberColumn(format="%.1f")}
        )
        
        tot_r_p = float(df_editado_perf["REALIZADO"].sum()) if "REALIZADO" in df_editado_perf.columns else 0.0
        tot_p_p = float(df_editado_perf["PLANEJADO"].sum()) if "PLANEJADO" in df_editado_perf.columns else 0.0
        pct_t_p = f"{(tot_r_p / tot_p_p * 100):.0f}%" if tot_p_p > 0 else "0%"
        
        st.markdown(f"<div class='linha-total'><span>TOTAL PERFURAÇÃO</span><span>REALIZADO: {tot_r_p:.1f}</span><span>PLANEJADO: {tot_p_p:.1f}</span><span>DESEMPENHO: {pct_t_p}</span></div>", unsafe_allow_html=True)

        if st.button("💾 Gravar Novas Metas de Perfuração", type="primary", use_container_width=True):
            for i, row in df_editado_perf.iterrows():
                hora_base = row['HORA'].split(" - ")[0]
                nova_meta = float(row['PLANEJADO'])
                
                linha_existente = df_perf_alvo[df_perf_alvo['hora'] == hora_base] if not df_perf_alvo.empty else pd.DataFrame()
                if linha_existente.empty:
                    supabase.table("horaria_perf").insert({"data_id": dia_alvo_str, "hora": hora_base, "meta": nova_meta, "realizado": 0.0, "causa": ""}).execute()
                else:
                    supabase.table("horaria_perf").update({"meta": nova_meta}).eq("data_id", dia_alvo_str).eq("hora", hora_base).execute()
            st.success("Metas de Perfuração atualizadas na nuvem!")
            time.sleep(1); st.rerun()

    with aba_manutencao:
        st.markdown(f"<h3 style='color:{COR_AZUL}; text-align:center;'>🔧 Central de Ordens de Serviço (OS)</h3>", unsafe_allow_html=True)
        st.write("Ordens de serviço abertas automaticamente por checklist crítico ou paradas operacionais, ou abertas manualmente.")
        if not df_os.empty:
            df_os = df_os.sort_values(by='id', ascending=False)
            st.dataframe(df_os, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma Ordem de Serviço registrada no momento.")

    with aba_diretoria:
        st.markdown(f"<h3 style='color:{COR_AZUL};'>Indicadores de Desempenho e Consumo (Por Setor)</h3>", unsafe_allow_html=True)
        filtro_mes = st.selectbox("Mês de Referência:", [datetime.today().strftime('%Y-%m')] + sorted(list(set(pd.to_datetime(df_rp['data']).dt.strftime('%Y-%m')) if not df_rp.empty else []), reverse=True))
        
        # Filtros do Mês
        df_c_dir = df_carga[df_carga['data_id'].str.startswith(filtro_mes)] if not df_carga.empty else pd.DataFrame()
        df_p_dir = df_perf[df_perf['data_id'].str.startswith(filtro_mes)] if not df_perf.empty else pd.DataFrame()
        df_pt_dir = df_parte[df_parte['data'].str.startswith(filtro_mes)] if not df_parte.empty else pd.DataFrame()
        df_rp_dir = df_rp[df_rp['data'].str.startswith(filtro_mes)] if not df_rp.empty else pd.DataFrame()
        
        # Identificar Equipamentos por Setor
        eqs_carga, eqs_perf = [], []
        if not df_eq.empty:
            eqs_carga = df_eq[df_eq['tipo'] == 'carga']['tag'].tolist()
            eqs_perf = df_eq[df_eq['tipo'] == 'perfuracao']['tag'].tolist()
        
        # Fallback caso a tabela equipamentos falhe
        if not eqs_carga and not eqs_perf:
            eqs_todas = set(df_pt_dir['equipamento'].unique()) | set(df_rp_dir['equipamento'].unique())
            for eq in eqs_todas:
                if 'UT' in str(eq).upper() or 'CA' in str(eq).upper(): eqs_carga.append(eq)
                else: eqs_perf.append(eq)

        # Processar Horas Rodadas e Martelo
        horas_rodadas, horas_martelo = {}, {}
        if not df_pt_dir.empty:
            for _, row in df_pt_dir.iterrows():
                eq = row['equipamento']
                h_i = pd.to_numeric(row.get('horimetro_inicial', 0), errors='coerce')
                h_f = pd.to_numeric(row.get('horimetro_final', 0), errors='coerce')
                hm_i = pd.to_numeric(row.get('horimetro_martelo_inicial', 0), errors='coerce')
                hm_f = pd.to_numeric(row.get('horimetro_martelo_final', 0), errors='coerce')
                
                h_i = h_i if pd.notna(h_i) else 0; h_f = h_f if pd.notna(h_f) else 0
                hm_i = hm_i if pd.notna(hm_i) else 0; hm_f = hm_f if pd.notna(hm_f) else 0
                
                if h_f >= h_i: horas_rodadas[eq] = horas_rodadas.get(eq, 0) + (h_f - h_i)
                if hm_f >= hm_i: horas_martelo[eq] = horas_martelo.get(eq, 0) + (hm_f - hm_i)

        # Processar Consumo e Paradas
        consumo, paradas = {}, {}
        if not df_rp_dir.empty:
            for _, row in df_rp_dir.iterrows():
                eq = row['equipamento']
                if row['tipo_registro'] == 'Abastecimento':
                    det = row['detalhes']
                    if isinstance(det, dict) and 'litros' in det:
                        consumo[eq] = consumo.get(eq, 0) + float(det['litros'])
                elif row['tipo_registro'] == 'Parada':
                    paradas[eq] = paradas.get(eq, 0) + 1

        # ==========================================
        # DASHBOARD: SETOR PRODUÇÃO (CARGA)
        # ==========================================
        st.markdown(f"<h4 style='color:{COR_AZUL}; margin-top:20px; border-bottom: 2px solid {COR_AMARELA}; padding-bottom: 5px;'>🚜 SETOR: PRODUÇÃO (CARGA)</h4>", unsafe_allow_html=True)
        
        cols_ut_dir = [c for c in df_c_dir.columns if 'ut' in c.lower()] if not df_c_dir.empty else []
        t_viag = df_c_dir[cols_ut_dir].sum().sum() if not df_c_dir.empty else 0
        h_carga_count = len(df_c_dir) if not df_c_dir.empty else 0
        viag_h = t_viag / h_carga_count if h_carga_count > 0 else 0
        
        cons_carga = sum([consumo.get(eq, 0) for eq in eqs_carga])
        paradas_carga = sum([paradas.get(eq, 0) for eq in eqs_carga])
        
        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.markdown(f"<div class='dir-card'><div class='dir-titulo'>Viagens / Hora</div><div class='dir-valor'>{viag_h:.1f} v/h</div></div>", unsafe_allow_html=True)
        cc2.markdown(f"<div class='dir-card'><div class='dir-titulo'>Total Viagens (Mês)</div><div class='dir-valor'>{int(t_viag)}</div></div>", unsafe_allow_html=True)
        cc3.markdown(f"<div class='dir-card'><div class='dir-titulo'>Consumo Combustível (Setor)</div><div class='dir-valor'>{cons_carga:,.0f} L</div></div>", unsafe_allow_html=True)
        cc4.markdown(f"<div class='dir-card'><div class='dir-titulo'>Ocorrências de Parada</div><div class='dir-valor'>{paradas_carga}</div></div>", unsafe_allow_html=True)
        
        tabela_carga = []
        for eq in eqs_carga:
            hr = horas_rodadas.get(eq, 0)
            cons = consumo.get(eq, 0)
            v_tot = 0
            if not df_c_dir.empty:
                col_eq = eq.lower().replace("-", "")
                if col_eq in df_c_dir.columns: v_tot = int(df_c_dir[col_eq].sum())
                
            if hr > 0 or cons > 0 or v_tot > 0:
                tabela_carga.append({
                    "Equipamento": eq,
                    "Viagens Realizadas": v_tot,
                    "Horas Rodadas (Motor)": round(hr, 1),
                    "Consumo Total (Litros)": cons,
                    "Média L/h": round(cons/hr, 1) if hr > 0 else 0
                })
        
        if tabela_carga:
            st.dataframe(pd.DataFrame(tabela_carga), use_container_width=True, hide_index=True)
        else:
            st.info("Sem registos detalhados de equipamentos de carga para este mês.")

        # ==========================================
        # DASHBOARD: SETOR PERFURAÇÃO
        # ==========================================
        st.markdown(f"<h4 style='color:{COR_AZUL}; margin-top:30px; border-bottom: 2px solid {COR_AMARELA}; padding-bottom: 5px;'>🎯 SETOR: PERFURAÇÃO</h4>", unsafe_allow_html=True)
        
        t_metros = df_p_dir['realizado'].sum() if not df_p_dir.empty else 0
        h_perf_count = len(df_p_dir[df_p_dir['realizado'] > 0]) if not df_p_dir.empty else 0
        metros_h = t_metros / h_perf_count if h_perf_count > 0 else 0
        
        cons_perf = sum([consumo.get(eq, 0) for eq in eqs_perf])
        paradas_perf = sum([paradas.get(eq, 0) for eq in eqs_perf])
        
        t_mot_perf = sum([horas_rodadas.get(eq, 0) for eq in eqs_perf])
        t_mar_perf = sum([horas_martelo.get(eq, 0) for eq in eqs_perf])
        pct_martelo = f"{(t_mar_perf / t_mot_perf * 100):.1f}%" if t_mot_perf > 0 else "N/A"
        
        cp1, cp2, cp3, cp4 = st.columns(4)
        cp1.markdown(f"<div class='dir-card'><div class='dir-titulo'>Metros / Hora</div><div class='dir-valor'>{metros_h:.1f} m/h</div></div>", unsafe_allow_html=True)
        cp2.markdown(f"<div class='dir-card'><div class='dir-titulo'>Total Metros (Mês)</div><div class='dir-valor'>{t_metros:.1f} m</div></div>", unsafe_allow_html=True)
        cp3.markdown(f"<div class='dir-card'><div class='dir-titulo'>Consumo Combustível (Setor)</div><div class='dir-valor'>{cons_perf:,.0f} L</div></div>", unsafe_allow_html=True)
        cp4.markdown(f"<div class='dir-card'><div class='dir-titulo'>% Utilização Martelo Global</div><div class='dir-valor'>{pct_martelo}</div></div>", unsafe_allow_html=True)

        tabela_perf = []
        for eq in eqs_perf:
            hr = horas_rodadas.get(eq, 0)
            hm = horas_martelo.get(eq, 0)
            cons = consumo.get(eq, 0)
            if hr > 0 or hm > 0 or cons > 0:
                tabela_perf.append({
                    "Equipamento": eq,
                    "Horas Rodadas (Motor)": round(hr, 1),
                    "Horas Martelo": round(hm, 1),
                    "% Martelo": f"{(hm/hr*100):.1f}%" if hr > 0 else "0%",
                    "Consumo Total (Litros)": cons,
                    "Média L/h": round(cons/hr, 1) if hr > 0 else 0
                })
                
        if tabela_perf:
            st.dataframe(pd.DataFrame(tabela_perf).style.apply(destacar_linha_total, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("Sem registos detalhados de equipamentos de perfuração para este mês.")

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
                    st.success("Excluído com sucesso!"); st.rerun()

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
                    st.success("Excluído com sucesso!"); st.rerun()

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
