import streamlit as st
import pandas as pd
import plotly.express as px
import calendar
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
    /* Estilos Gerais */
    .kpi-card {{ background-color: {COR_AZUL}; color: white; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid {COR_AMARELA}; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }}
    .kpi-title {{ font-size: 1.1rem; margin-bottom: 5px; opacity: 0.9; }}
    .kpi-value {{ font-size: 2.5rem; font-weight: bold; color: {COR_AMARELA}; margin: 0; }}
    .cal-header {{ font-weight: bold; text-align: center; color: {COR_AZUL}; background-color: #f0f2f6; padding: 5px; border-radius: 5px; }}
    div[data-testid="stButton"] button {{ border-radius: 10px; font-weight: bold; }}
    
    /* Botões Operação */
    .btn-operacao button {{ height: 80px !important; font-size: 30px !important; background-color: {COR_AZUL} !important; color: white !important; width: 100%; }}
    .btn-operacao button:active {{ background-color: {COR_AMARELA} !important; color: black !important; }}
    .valor-gigante {{ font-size: 60px; font-weight: bold; text-align: center; color: {COR_AMARELA}; }}
    .meta-box {{ background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; border-left: 5px solid {COR_AZUL}; margin-bottom: 10px; }}
    .meta-destaque {{ font-size: 25px; font-weight: bold; color: {COR_AZUL}; display: block; margin-top: 5px;}}
    
    /* Novo Estilo: Tela de Login */
    [data-testid="stForm"] {{ background-color: #ffffff; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); border-top: 8px solid {COR_AZUL}; }}
    .login-title {{ text-align: center; color: {COR_AZUL}; font-weight: bold; font-size: 28px; margin-bottom: 10px; }}
    .login-subtitle {{ text-align: center; color: #666; font-size: 16px; margin-bottom: 30px; }}
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

def obter_horario_atual():
    agora = datetime.now()
    hora = agora.hour
    if 7 <= hora < 8: return "07:15", agora.strftime('%Y-%m-%d')
    elif 8 <= hora < 9: return "08:00", agora.strftime('%Y-%m-%d')
    elif 9 <= hora < 10: return "09:00", agora.strftime('%Y-%m-%d')
    elif 10 <= hora < 11: return "10:00", agora.strftime('%Y-%m-%d')
    elif 11 <= hora < 12: return "11:00", agora.strftime('%Y-%m-%d')
    elif 13 <= hora < 14: return "13:00", agora.strftime('%Y-%m-%d')
    elif 14 <= hora < 15: return "14:00", agora.strftime('%Y-%m-%d')
    elif 15 <= hora < 16: return "15:00", agora.strftime('%Y-%m-%d')
    elif 16 <= hora < 17: return "16:00", agora.strftime('%Y-%m-%d')
    else: return "Fora de Turno", agora.strftime('%Y-%m-%d')

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
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("form_login"):
            st.markdown(f"<div class='login-title'>🏢 Petra Agregados</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='login-subtitle'>Sistema Integrado de PCP e FMS</div>", unsafe_allow_html=True)
            
            usuario = st.text_input("👤 Usuário:", placeholder="Digite seu usuário")
            senha = st.text_input("🔑 Senha:", type="password", placeholder="Digite sua senha")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("🚀 Entrar no Sistema", use_container_width=True):
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
                    st.error("⚠️ Usuário ou senha incorretos. Acesso negado.")

def tela_selecao_maquina():
    st.markdown(f"<h3 style='text-align:center; color:{COR_AZUL};'>Olá, {st.session_state.usuario}</h3>", unsafe_allow_html=True)
    res_eq = supabase.table("equipamentos").select("*").eq("ativo", True).execute()
    df_eq = pd.DataFrame(res_eq.data) if res_eq.data else pd.DataFrame()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_maquina"):
            if not df_eq.empty:
                tag_selecionada = st.selectbox("Selecione o Equipamento:", df_eq["tag"].tolist())
                if st.form_submit_button("Iniciar Operação", use_container_width=True):
                    st.session_state.tag_equipamento = tag_selecionada
                    st.session_state.tipo_equipamento = df_eq[df_eq["tag"] == tag_selecionada].iloc[0]["tipo"]
                    st.session_state.tela_atual = "operacao"
                    st.rerun()
            else:
                st.warning("Nenhum equipamento cadastrado.")

def tela_operacao():
    slot_atual, data_hoje = obter_horario_atual()
    e_caminhao = (st.session_state.tipo_equipamento == "carga")
    
    st.markdown(f"**👤 {st.session_state.usuario}** | **🚜 {st.session_state.tag_equipamento}** | ⏰ **{slot_atual}**")
    
    # Abas dinâmicas do Operador (Checklist e Parada)
    with st.expander("📋 Preencher Checklist", expanded=False):
        res_chk = supabase.table("itens_checklist").select("item").in_("tipo_equipamento", [st.session_state.tipo_equipamento, 'ambos']).execute()
        respostas_chk = {}
        if res_chk.data:
            for i, linha in enumerate(res_chk.data):
                item = linha['item']
                respostas_chk[item] = st.selectbox(f"{item}:", ["OK", "Requer Atenção", "Crítico"], key=f"chk_{i}")
        if st.button("📤 Enviar Checklist Parcial", use_container_width=True):
            supabase.table("registros_parciais").insert({"data": data_hoje, "hora": slot_atual, "equipamento": st.session_state.tag_equipamento, "operador": st.session_state.usuario, "tipo_registro": "Checklist", "detalhes": respostas_chk}).execute()
            st.success("Enviado para o PCP!")

    with st.expander("🛑 Registrar Parada", expanded=False):
        res_par = supabase.table("motivos_parada").select("motivo").in_("tipo_equipamento", [st.session_state.tipo_equipamento, 'ambos']).execute()
        opcoes_parada = [m['motivo'] for m in res_par.data] if res_par.data else ["Nenhuma"]
        motivo_sel = st.selectbox("Selecione o Motivo:", opcoes_parada)
        if st.button("📤 Enviar Parada", use_container_width=True):
            supabase.table("registros_parciais").insert({"data": data_hoje, "hora": slot_atual, "equipamento": st.session_state.tag_equipamento, "operador": st.session_state.usuario, "tipo_registro": "Parada", "detalhes": {"motivo": motivo_sel}}).execute()
            tabela_gestor = "horaria_carga" if e_caminhao else "horaria_perf"
            supabase.table(tabela_gestor).update({"causa": motivo_sel}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
            st.success("Parada registrada!")

    st.divider()

    # Lógica de Apontamento
    if slot_atual == "Fora de Turno":
        st.warning("Fora do horário de operação da mina.")
    else:
        res_pcp = supabase.table("pcp_planejamento").select("*").eq("data", data_hoje).execute()
        meta_viagens = res_pcp.data[0]['meta_viagens_equipe_hora'] if res_pcp.data else 0
        meta_metros = res_pcp.data[0]['meta_perf_metros_hora'] if res_pcp.data else 0.0

        st.markdown("<div class='btn-operacao'>", unsafe_allow_html=True)
        if e_caminhao:
            coluna_db = st.session_state.tag_equipamento.lower().replace("-", "")
            res_hora = supabase.table("horaria_carga").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()
            if not res_hora.data:
                supabase.table("horaria_carga").insert({"data_id": data_hoje, "hora": slot_atual, "ut33": 0, "ut34": 0, "meta": meta_viagens, "causa": ""}).execute()
                res_hora = supabase.table("horaria_carga").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()
            
            df_hora = pd.DataFrame(res_hora.data)
            if coluna_db in df_hora.columns:
                valor_individual = df_hora.iloc[0][coluna_db]
                valor_equipe = sum([df_hora.iloc[0][col] for col in df_hora.columns if 'ut' in col.lower()])
                st.markdown(f"<div class='meta-box'>Sua Carga: <b>{valor_individual}</b> | Equipe: <span class='meta-destaque'>{valor_equipe} / {meta_viagens if meta_viagens>0 else 'N/A'}</span></div>", unsafe_allow_html=True)

                c_menos, c_valor, c_mais = st.columns([1, 1.5, 1])
                if c_menos.button("➖", key="sub_v"):
                    supabase.table("horaria_carga").update({coluna_db: max(0, int(valor_individual) - 1)}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                    st.rerun()
                c_valor.markdown(f"<div class='valor-gigante'>{int(valor_individual)}</div>", unsafe_allow_html=True)
                if c_mais.button("➕", key="add_v"):
                    supabase.table("horaria_carga").update({coluna_db: int(valor_individual) + 1}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                    st.rerun()
        else:
            res_hora = supabase.table("horaria_perf").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()
            if not res_hora.data:
                supabase.table("horaria_perf").insert({"data_id": data_hoje, "hora": slot_atual, "realizado": 0.0, "meta": meta_metros, "causa": ""}).execute()
                res_hora = supabase.table("horaria_perf").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()

            valor_perf = res_hora.data[0]['realizado']
            st.markdown(f"<div class='meta-box'>Perfuração Realizada: <span class='meta-destaque'>{valor_perf:.1f} / {meta_metros if meta_metros>0 else 'N/A'} m</span></div>", unsafe_allow_html=True)

            c_menos, c_valor, c_mais = st.columns([1, 1.5, 1])
            if c_menos.button("➖", key="sub_p"):
                supabase.table("horaria_perf").update({"realizado": max(0.0, float(valor_perf) - 1.0)}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                st.rerun()
            c_valor.markdown(f"<div class='valor-gigante'>{valor_perf:.1f}</div>", unsafe_allow_html=True)
            if c_mais.button("➕", key="add_p"):
                supabase.table("horaria_perf").update({"realizado": float(valor_perf) + 1.0}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    
    # Nova Seção: Fechamento da Parte Diária (Sempre Visível no Fundo)
    st.markdown(f"<h3 style='color:{COR_AZUL};'>📝 Relatório de Parte Diária</h3>", unsafe_allow_html=True)
    with st.expander("Finalizar e Enviar Turno", expanded=False):
        with st.form("form_parte_diaria"):
            col_h1, col_h2 = st.columns(2)
            h_inicial = col_h1.number_input("Horímetro Inicial:", min_value=0.0, step=0.1, format="%.1f")
            h_final = col_h2.number_input("Horímetro Final:", min_value=0.0, step=0.1, format="%.1f")
            obs = st.text_area("Observações Gerais do Turno (Opcional):")
            
            if st.form_submit_button("✅ Enviar Relatório Diário", use_container_width=True):
                if h_final >= h_inicial:
                    dados_parte_diaria = {
                        "data": data_hoje,
                        "equipamento": st.session_state.tag_equipamento,
                        "operador": st.session_state.usuario,
                        "horimetro_inicial": h_inicial,
                        "horimetro_final": h_final,
                        "observacoes": obs
                    }
                    supabase.table("parte_diaria").insert(dados_parte_diaria).execute()
                    st.success("Parte diária enviada com sucesso para o PCP!")
                else:
                    st.error("O Horímetro Final não pode ser menor que o Inicial.")

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
                    fig_c.upda
