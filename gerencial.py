import streamlit as st
import pandas as pd
import plotly.express as px
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
    .cal-header {{ font-weight: bold; text-align: center; color: {COR_AZUL}; background-color: #f0f2f6; padding: 5px; border-radius: 5px; }}
    
    .login-box {{ background: linear-gradient(135deg, #ffffff 0%, #f4f6f9 100%); padding: 50px 30px; border-radius: 20px; box-shadow: 0px 20px 40px rgba(0,0,0,0.08); border-top: 8px solid {COR_AZUL}; margin-top: 50px; }}
    .login-title {{ text-align: center; color: {COR_AZUL}; font-weight: 800; font-size: 32px; margin-bottom: 5px; letter-spacing: -1px; }}
    .login-subtitle {{ text-align: center; color: #7f8c8d; font-size: 16px; margin-bottom: 30px; font-weight: 500; }}
    
    .meta-box {{ background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid {COR_AZUL}; margin-bottom: 20px; box-shadow: inset 0px 2px 5px rgba(0,0,0,0.05); display: flex; justify-content: space-around; text-align: center; }}
    .meta-titulo {{ font-size: 16px; color: #7f8c8d; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }}
    .meta-destaque {{ font-size: 28px; font-weight: bold; color: {COR_AZUL}; display: block; margin-top: 5px;}}
    .valor-gigante {{ font-size: 80px; font-weight: 900; text-align: center; color: {COR_AMARELA}; line-height: 120px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }}
    
    button:has(p:contains("➕")) {{ background: linear-gradient(180deg, #00e676 0%, #00c853 100%) !important; color: white !important; height: 120px !important; border-radius: 25px !important; border: 2px solid #00a042 !important; box-shadow: 0px 8px 15px rgba(0,200,83,0.3) !important; transition: all 0.2s !important; }}
    button:has(p:contains("➕")):active {{ transform: translateY(4px) !important; box-shadow: 0px 4px 10px rgba(0,200,83,0.3) !important; }}
    button:has(p:contains("➕")) p {{ font-size: 60px !important; font-weight: bold; margin: 0; }}
    
    button:has(p:contains("➖")) {{ background: linear-gradient(180deg, #ff5252 0%, #ff1744 100%) !important; color: white !important; height: 120px !important; border-radius: 25px !important; border: 2px solid #d50000 !important; box-shadow: 0px 8px 15px rgba(255,23,68,0.3) !important; transition: all 0.2s !important; }}
    button:has(p:contains("➖")):active {{ transform: translateY(4px) !important; box-shadow: 0px 4px 10px rgba(255,23,68,0.3) !important; }}
    button:has(p:contains("➖")) p {{ font-size: 60px !important; font-weight: bold; margin: 0; line-height: 50px; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXÃO COM A NUVEM E ESTADO
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
if "dia_explodido" not in st.session_state: st.session_state.dia_explodido = None

if "prod_val" not in st.session_state: st.session_state.prod_val = 0
if "sync_pendente" not in st.session_state: st.session_state.sync_pendente = False
if "ultima_alteracao" not in st.session_state: st.session_state.ultima_alteracao = 0
if "slot_selecionado_estado" not in st.session_state: st.session_state.slot_selecionado_estado = None

def obter_horario_sugerido():
    agora = datetime.now()
    hora = agora.hour
    if 7 <= hora < 8: return "07:15"
    elif 8 <= hora < 9: return "08:00"
    elif 9 <= hora < 10: return "09:00"
    elif 10 <= hora < 11: return "10:00"
    elif 11 <= hora < 12: return "11:00"
    elif 13 <= hora < 14: return "13:00"
    elif 14 <= hora < 15: return "14:00"
    elif 15 <= hora < 16: return "15:00"
    elif 16 <= hora < 17: return "16:00"
    else: return "07:15"

def carregar_dados_gestor():
    df_c = pd.DataFrame(supabase.table("horaria_carga").select("*").execute().data)
    df_p = pd.DataFrame(supabase.table("horaria_perf").select("*").execute().data)
    df_pt = pd.DataFrame(supabase.table("parte_diaria").select("*").execute().data)
    df_pcp = pd.DataFrame(supabase.table("pcp_planejamento").select("*").execute().data)
    return df_c, df_p, df_pt, df_pcp

# ==========================================
# 3. TELAS DO SISTEMA
# ==========================================

def tela_login():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.image("https://via.placeholder.com/600x150.png?text=PETRA+AGREGADOS", use_container_width=True)
        st.markdown("<div class='login-title'>FMS Petra</div>", unsafe_allow_html=True)
        st.markdown("<div class='login-subtitle'>Gestão de Frota e Planejamento de Lavra</div>", unsafe_allow_html=True)
        
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
                    if st.session_state.perfil == "gestor":
                        st.session_state.tela_atual = "gestor"
                    else:
                        st.session_state.tela_atual = "selecao_maquina"
                    st.rerun()
                else:
                    st.error("⚠️ Credenciais inválidas. Verifique seu acesso.")
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
                    st.rerun()
            else:
                st.warning("Nenhum equipamento cadastrado.")

def tela_operacao():
    data_hoje = datetime.now().strftime('%Y-%m-%d')
    e_caminhao = (st.session_state.tipo_equipamento == "carga")
    
    st.markdown(f"**👤 {st.session_state.usuario}** | **🚜 {st.session_state.tag_equipamento}**")
    
    # ---------------------------------------------------------
    # RELÓGIO HORA A HORA (SELETOR)
    # ---------------------------------------------------------
    horarios_turno = ["07:15", "08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"]
    if st.session_state.slot_selecionado_estado not in horarios_turno:
        st.session_state.slot_selecionado_estado = obter_horario_sugerido()
    
    idx_padrao = horarios_turno.index(st.session_state.slot_selecionado_estado)
    
    st.markdown("### ⏰ Selecione a Hora do Apontamento")
    slot_atual = st.selectbox("Horário:", horarios_turno, index=idx_padrao)
    
    if slot_atual != st.session_state.slot_selecionado_estado:
        st.session_state.slot_selecionado_estado = slot_atual
        st.session_state.sync_pendente = False
        st.rerun()

    # ---------------------------------------------------------
    # MOTOR DE SINCRONIZAÇÃO ASSÍNCRONA
    # ---------------------------------------------------------
    if st.session_state.sync_pendente:
        tempo_passado = time.time() - st.session_state.ultima_alteracao
        if tempo_passado >= 10:
            try:
                if e_caminhao:
                    coluna_db = st.session_state.tag_equipamento.lower().replace("-", "")
                    supabase.table("horaria_carga").update({coluna_db: st.session_state.prod_val}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                else:
                    supabase.table("horaria_perf").update({"realizado": st.session_state.prod_val}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                
                st.session_state.sync_pendente = False
                st.toast(f"☁️ Apontamento das {slot_atual} salvo na nuvem!", icon="✅")
            except Exception:
                st.toast("⚠️ Sem sinal de internet. Tentando salvar novamente...", icon="🔄")

    # ---------------------------------------------------------
    # MENU SUPERIOR: Checklist e Paradas
    # ---------------------------------------------------------
    c_check, c_parada = st.columns(2)
    with c_check:
        with st.popover("📋 Checklist"):
            res_chk = supabase.table("itens_checklist").select("item").in_("tipo_equipamento", [st.session_state.tipo_equipamento, 'ambos']).execute()
            respostas_chk = {}
            if res_chk.data:
                for i, linha in enumerate(res_chk.data):
                    respostas_chk[linha['item']] = st.selectbox(f"{linha['item']}:", ["OK", "Atenção", "Crítico"], key=f"chk_{i}")
            if st.button("Enviar ao PCP", use_container_width=True):
                supabase.table("registros_parciais").insert({"data": data_hoje, "hora": slot_atual, "equipamento": st.session_state.tag_equipamento, "operador": st.session_state.usuario, "tipo_registro": "Checklist", "detalhes": respostas_chk}).execute()
                st.success("Enviado!")

    with c_parada:
        with st.popover("🛑 Parada"):
            st.markdown(f"**Registro de Parada ({slot_atual})**")
            res_par = supabase.table("motivos_parada").select("motivo").in_("tipo_equipamento", [st.session_state.tipo_equipamento, 'ambos']).execute()
            opcoes_parada = [m['motivo'] for m in res_par.data] if res_par.data else ["Nenhuma"]
            motivo_sel = st.selectbox("Motivo da Parada:", opcoes_parada)
            
            c_h1, c_h2 = st.columns(2)
            hora_inicio = c_h1.time_input("Horário Inicial")
            hora_fim = c_h2.time_input("Horário Final")
            
            if st.button("Avisar PCP", use_container_width=True):
                h_ini_str = hora_inicio.strftime("%H:%M")
                h_fim_str = hora_fim.strftime("%H:%M")
                texto_causa = f"{motivo_sel} ({h_ini_str} às {h_fim_str})"
                
                detalhes_parada = {"motivo": motivo_sel, "inicio": h_ini_str, "fim": h_fim_str}
                
                supabase.table("registros_parciais").insert({
                    "data": data_hoje, "hora": slot_atual, "equipamento": st.session_state.tag_equipamento, 
                    "operador": st.session_state.usuario, "tipo_registro": "Parada", "detalhes": detalhes_parada
                }).execute()
                
                tabela_gestor = "horaria_carga" if e_caminhao else "horaria_perf"
                supabase.table(tabela_gestor).update({"causa": texto_causa}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                st.success("Parada registrada com sucesso!")

    st.write("---")

    # ---------------------------------------------------------
    # TELA DE APONTAMENTO
    # ---------------------------------------------------------
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
        
        if not st.session_state.sync_pendente:
            if coluna_db in df_hora.columns:
                st.session_state.prod_val = df_hora.iloc[0][coluna_db]
        
        valor_equipe = sum([df_hora.iloc[0][col] for col in df_hora.columns if 'ut' in col.lower()])
        
        # NOVO BANNER: META vs REALIZADO (Carga)
        st.markdown(f"""
            <div class='meta-box'>
                <div>
                    <span class='meta-titulo'>META (P)</span>
                    <span class='meta-destaque'>{meta_viagens if meta_viagens>0 else 'N/A'} viag.</span>
                </div>
                <div>
                    <span class='meta-titulo'>REALIZADO EQUIPE (R)</span>
                    <span class='meta-destaque'>{valor_equipe} viag.</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        c_menos, c_valor, c_mais = st.columns([1, 1.5, 1])
        with c_menos:
            if st.button("➖", key="sub_v", use_container_width=True):
                st.session_state.prod_val = max(0, int(st.session_state.prod_val) - 1)
                st.session_state.sync_pendente = True
                st.session_state.ultima_alteracao = time.time()
                st.rerun()
                
        with c_valor:
            st.markdown(f"<div class='valor-gigante'>{int(st.session_state.prod_val)}</div>", unsafe_allow_html=True)
            
        with c_mais:
            if st.button("➕", key="add_v", use_container_width=True):
                st.session_state.prod_val = int(st.session_state.prod_val) + 1
                st.session_state.sync_pendente = True
                st.session_state.ultima_alteracao = time.time()
                st.rerun()
                
        if st.session_state.sync_pendente:
            st.markdown("<p style='text-align:center; color:#7f8c8d; font-size:12px;'>Salvando na nuvem em breve...</p>", unsafe_allow_html=True)
            
    else: # Perfuração
        res_hora = supabase.table("horaria_perf").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()
        if not res_hora.data:
            supabase.table("horaria_perf").insert({"data_id": data_hoje, "hora": slot_atual, "realizado": 0.0, "meta": meta_metros, "causa": ""}).execute()
            res_hora = supabase.table("horaria_perf").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()

        if not st.session_state.sync_pendente:
            st.session_state.prod_val = res_hora.data[0]['realizado']
            
        # NOVO BANNER: META vs REALIZADO (Perfuração)
        st.markdown(f"""
            <div class='meta-box'>
                <div>
                    <span class='meta-titulo'>META (P)</span>
                    <span class='meta-destaque'>{meta_metros if meta_metros>0 else 'N/A'} m</span>
                </div>
                <div>
                    <span class='meta-titulo'>REALIZADO (R)</span>
                    <span class='meta-destaque'>{float(st.session_state.prod_val):.1f} m</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        c_menos, c_valor, c_mais = st.columns([1, 1.5, 1])
        with c_menos:
            if st.button("➖", key="sub_p", use_container_width=True):
                st.session_state.prod_val = max(0.0, float(st.session_state.prod_val) - 1.0)
                st.session_state.sync_pendente = True
                st.session_state.ultima_alteracao = time.time()
                st.rerun()
                
        with c_valor:
            st.markdown(f"<div class='valor-gigante'>{float(st.session_state.prod_val):.1f}</div>", unsafe_allow_html=True)
            
        with c_mais:
            if st.button("➕", key="add_p", use_container_width=True):
                st.session_state.prod_val = float(st.session_state.prod_val) + 1.0
                st.session_state.sync_pendente = True
                st.session_state.ultima_alteracao = time.time()
                st.rerun()

    st.divider()

    # ---------------------------------------------------------
    # NOVO: TABELA DE RESUMO DO TURNO (P | R | %)
    # ---------------------------------------------------------
    st.markdown(f"<h4 style='color:{COR_AZUL};'>📊 Resumo do Turno</h4>", unsafe_allow_html=True)
    if e_caminhao:
        res_dia = supabase.table("horaria_carga").select("*").eq("data_id", data_hoje).execute()
    else:
        res_dia = supabase.table("horaria_perf").select("*").eq("data_id", data_hoje).execute()
        
    if res_dia.data:
        df_dia = pd.DataFrame(res_dia.data)
        tabela_resumo = []
        for hora in horarios_turno:
            linha = df_dia[df_dia['hora'] == hora]
            if not linha.empty:
                m_h = linha.iloc[0]['meta']
                if e_caminhao:
                    cols_ut = [c for c in linha.columns if 'ut' in c.lower()]
                    r_h = sum([linha.iloc[0][c] for c in cols_ut])
                else:
                    r_h = linha.iloc[0]['realizado']
                
                pct = (r_h / m_h * 100) if m_h > 0 else 0
                tabela_resumo.append({
                    "Horário": hora,
                    "P (Meta)": int(m_h) if e_caminhao else float(m_h),
                    "R (Realizado)": int(r_h) if e_caminhao else float(r_h),
                    "% Alcance": f"{pct:.0f}%"
                })
        
        if tabela_resumo:
            st.dataframe(pd.DataFrame(tabela_resumo), use_container_width=True, hide_index=True)
        else:
            st.write("Sem registros no turno de hoje.")

    st.write("---")
    
    # ---------------------------------------------------------
    # FECHAMENTO DO TURNO (Parte Diária)
    # ---------------------------------------------------------
    with st.expander("📝 Preencher Relatório Diário", expanded=False):
        with st.form("form_parte_diaria"):
            col_h1, col_h2 = st.columns(2)
            h_inicial = col_h1.number_input("Horímetro Inicial:", min_value=0.0, step=0.1, format="%.1f")
            h_final = col_h2.number_input("Horímetro Final:", min_value=0.0, step=0.1, format="%.1f")
            obs = st.text_area("Observações Gerais (Opcional):")
            
            if st.form_submit_button("✅ Enviar e Fechar Parte Diária", use_container_width=True):
                if h_final >= h_inicial:
                    dados = {
                        "data": data_hoje,
                        "equipamento": st.session_state.tag_equipamento,
                        "operador": st.session_state.usuario,
                        "horimetro_inicial": h_inicial,
                        "horimetro_final": h_final,
                        "observacoes": obs
                    }
                    supabase.table("parte_diaria").insert(dados).execute()
                    st.success("Parte diária enviada com sucesso para o PCP!")
                else:
                    st.error("Erro: O Horímetro Final é menor que o Inicial.")

def tela_gestor():
    col_logo, col_titulo = st.columns([1, 4])
    with col_titulo:
        st.markdown(f"<h1 style='color: {COR_AZUL};'>📊 Painel de Controle - Operação</h1>", unsafe_allow_html=True)
        st.markdown(f"**Gestor:** {st.session_state.usuario} | **Status:** <span style='color:{COR_AMARELA};'>⚫ Nuvem Ativa</span>", unsafe_allow_html=True)
    st.divider()

    df_carga, df_perf, df_parte, df_pcp = carregar_dados_gestor()
    data_hoje_str = datetime.today().strftime('%Y-%m-%d')
    
    df_carga_hoje = df_carga[df_carga['data_id'] == data_hoje_str] if not df_carga.empty else pd.DataFrame()
    total_viagens = df_carga_hoje['ut33'].sum() + df_carga_hoje['ut34'].sum() if not df_carga_hoje.empty else 0
    df_perf_hoje = df_perf[df_perf['data_id'] == data_hoje_str] if not df_perf.empty else pd.DataFrame()
    total_metros = df_perf_hoje['realizado'].sum() if not df_perf_hoje.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='kpi-card'><p class='kpi-title'>Total Viagens (Hoje)</p><p class='kpi-value'>🚛 {int(total_viagens)}</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-card'><p class='kpi-title'>Metros (Hoje)</p><p class='kpi-value'>🎯 {total_metros:.1f} m</p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-card'><p class='kpi-title'>Relatórios Turno</p><p class='kpi-value'>📋 {len(df_parte)}</p></div>", unsafe_allow_html=True)
    st.write("") 

    aba_hoje, aba_pcp, aba_diretoria, aba_dados, aba_config = st.tabs(["📈 Produção (Hoje)", "⚙️ Planejamento PCP", "📊 Visão Diretoria", "🗄️ Dados Brutos", "🛠️ Cadastros"])

    with aba_hoje:
        st.info("Painel de acompanhamento diário ativo. Visualize os KPI's acima.")

    with aba_pcp:
        st.subheader("Planejamento Mensal de Lavra")
        hoje = datetime.today()
        meses = [f"{(hoje.replace(day=1) - timedelta(days=30*i)).year}-{(hoje.replace(day=1) - timedelta(days=30*i)).month:02d}" for i in range(6, -1, -1)]
        mes_selecionado = st.selectbox("Selecione o Mês:", reversed(meses))
        
        ano_sel, mes_sel = map(int, mes_selecionado.split('-'))
        cal = calendar.Calendar(firstweekday=6)
        matriz_dias = cal.monthdayscalendar(ano_sel, mes_sel)
        
        dias_semana = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SAB"]
        cols_dias = st.columns(7)
        for i, d in enumerate(dias_semana): cols_dias[i].markdown(f"<div class='cal-header'>{d}</div>", unsafe_allow_html=True)
        
        for semana in matriz_dias:
            cols_semana = st.columns(7)
            for i, dia in enumerate(semana):
                if dia != 0:
                    data_formatada = f"{ano_sel}-{mes_sel:02d}-{dia:02d}"
                    if cols_semana[i].button(f"{dia:02d}", key=data_formatada, type="primary" if data_formatada == data_hoje_str else "secondary", use_container_width=True):
                        st.session_state.dia_explodido = data_formatada
                else:
                    cols_semana[i].write("")
        st.divider()

        if st.session_state.dia_explodido:
            dia_alvo = st.session_state.dia_explodido
            df_meta = df_pcp[df_pcp['data'] == dia_alvo] if not df_pcp.empty else pd.DataFrame()
            m_viagens = df_meta.iloc[0]['meta_viagens_equipe_hora'] if not df_meta.empty else 0
            m_metros = df_meta.iloc[0]['meta_perf_metros_hora'] if not df_meta.empty else 0.0

            with st.form(f"form_pcp_{dia_alvo}"):
                c_prod, c_perf = st.columns(2)
                nova_meta_v = c_prod.number_input(f"Meta Viagens ({dia_alvo}):", value=int(m_viagens), step=1)
                nova_meta_m = c_perf.number_input(f"Meta Metros ({dia_alvo}):", value=float(m_metros), step=1.0)
                if st.form_submit_button("💾 Salvar Planejamento na Nuvem", use_container_width=True):
                    supabase.table("pcp_planejamento").upsert({"data": dia_alvo, "meta_viagens_equipe_hora": nova_meta_v, "meta_perf_metros_hora": nova_meta_m}).execute()
                    st.success("Atualizado!")
                    st.rerun()

    with aba_diretoria:
        st.markdown("### Consolidado Global")
        if not df_carga.empty and not df_perf.empty:
            df_carga['ano'] = pd.to_datetime(df_carga['data_id']).dt.year.astype(str)
            df_carga['mes'] = pd.to_datetime(df_carga['data_id']).dt.strftime('%m')
            df_carga['ano_mes'] = pd.to_datetime(df_carga['data_id']).dt.strftime('%Y-%m')

            df_perf['ano'] = pd.to_datetime(df_perf['data_id']).dt.year.astype(str)
            df_perf['mes'] = pd.to_datetime(df_perf['data_id']).dt.strftime('%m')
            df_perf['ano_mes'] = pd.to_datetime(df_perf['data_id']).dt.strftime('%Y-%m')

            anos = ["Todos"] + sorted(list(df_carga['ano'].unique()), reverse=True)
            meses_op = ["Todos", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
            
            c_f1, c_f2 = st.columns(2)
            ano_f = c_f1.selectbox("📅 Ano:", anos)
            mes_f = c_f2.selectbox("📆 Mês:", meses_op)

            df_c_f, df_p_f = df_carga.copy(), df_perf.copy()
            if ano_f != "Todos": df_c_f, df_p_f = df_c_f[df_c_f['ano'] == ano_f], df_p_f[df_p_f['ano'] == ano_f]
            if mes_f != "Todos": df_c_f, df_p_f = df_c_f[df_c_f['mes'] == mes_f], df_p_f[df_p_f['mes'] == mes_f]

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                df_carga_mes = df_c_f.groupby('ano_mes')[['ut33', 'ut34']].sum().reset_index()
                if not df_carga_mes.empty:
                    fig_c = px.bar(df_carga_mes.melt(id_vars='ano_mes'), x='ano_mes', y='value', color='variable', barmode='stack', color_discrete_sequence=[COR_AZUL, COR_AMARELA])
                    fig_c.update_layout(plot_bgcolor=COR_FUNDO, paper_bgcolor=COR_FUNDO)
                    st.plotly_chart(fig_c, use_container_width=True)
            with col_d2:
                df_perf_mes = df_p_f.groupby('ano_mes')['realizado'].sum().reset_index()
                if not df_perf_mes.empty:
                    fig_p = px.area(df_perf_mes, x='ano_mes', y='realizado', color_discrete_sequence=[COR_AMARELA])
                    fig_p.update_layout(plot_bgcolor=COR_FUNDO, paper_bgcolor=COR_FUNDO)
                    st.plotly_chart(fig_p, use_container_width=True)

    with aba_dados:
        c_t1, c_t2, c_t3 = st.tabs(["Carga", "Perfuração", "Fechamentos (Parte Diária)"])
        with c_t1: st.dataframe(df_carga, use_container_width=True)
        with c_t2: st.dataframe(df_perf, use_container_width=True)
        with c_t3: st.dataframe(df_parte, use_container_width=True)

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
            
            st.markdown("Motivos Atuais:")
            df_motivos = pd.DataFrame(supabase.table("motivos_parada").select("*").execute().data)
            st.dataframe(df_motivos, hide_index=True)

        with col_check:
            st.markdown("**📋 Adicionar Item de Checklist**")
            with st.form("form_add_check"):
                novo_check = st.text_input("Nome do Item:")
                tipo_c = st.selectbox("Aplica-se a:", ["ambos", "carga", "perfuracao"], key="tc")
                if st.form_submit_button("➕ Adicionar Item"):
                    supabase.table("itens_checklist").insert({"item": novo_check, "tipo_equipamento": tipo_c}).execute()
                    st.success("Item Adicionado!")
            
            st.markdown("Checklist Atual:")
            df_checks = pd.DataFrame(supabase.table("itens_checklist").select("*").execute().data)
            st.dataframe(df_checks, hide_index=True)

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
                st.session_state.tela_atual = "gestor"
                st.rerun()
            if st.button("📱 Simular Operador", use_container_width=True):
                st.session_state.tela_atual = "selecao_maquina"
                st.rerun()
                
        st.divider()
        if st.button("🚪 Sair (Logout)", use_container_width=True):
            st.session_state.clear()
            st.rerun()

if st.session_state.tela_atual == "login":
    tela_login()
elif st.session_state.tela_atual == "selecao_maquina":
    tela_selecao_maquina()
elif st.session_state.tela_atual == "operacao":
    tela_operacao()
elif st.session_state.tela_atual == "gestor" and st.session_state.perfil == "gestor":
    tela_gestor()
