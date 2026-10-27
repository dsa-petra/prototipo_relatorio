import streamlit as st
import pandas as pd
import plotly.express as px
import calendar
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from supabase import create_client

# 1. CONFIGURAÇÃO GLOBAL (Sempre a primeira linha)
st.set_page_config(page_title="Sistema PCP Petra", layout="wide", page_icon="⚙️")
st_autorefresh(interval=15000, limit=None, key="atualizacao_continua") # Atualiza a cada 15s

# 2. CONSTANTES E ESTILO
COR_AZUL = "#54728c"
COR_AMARELA = "#ffc107"
COR_FUNDO = "rgba(0,0,0,0)"

st.markdown(f"""
    <style>
    .kpi-card {{ background-color: {COR_AZUL}; color: white; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid {COR_AMARELA}; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }}
    .kpi-value {{ font-size: 2.5rem; font-weight: bold; color: {COR_AMARELA}; margin: 0; }}
    div[data-testid="stButton"] button {{ border-radius: 10px; font-weight: bold; }}
    .btn-operacao button {{ height: 80px !important; font-size: 30px !important; background-color: {COR_AZUL} !important; color: white !important; width: 100%; }}
    .btn-operacao button:active {{ background-color: {COR_AMARELA} !important; color: black !important; }}
    .valor-gigante {{ font-size: 60px; font-weight: bold; text-align: center; color: {COR_AMARELA}; }}
    </style>
""", unsafe_allow_html=True)

# 3. CONEXÃO COM A NUVEM
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase = init_connection()
except Exception:
    st.error("Erro ao conectar com o banco de dados. Verifique as chaves no Streamlit Cloud.")
    st.stop()

# 4. GESTÃO DE ESTADO (Variáveis que controlam onde o utilizador está)
if "usuario" not in st.session_state: st.session_state.usuario = None
if "perfil" not in st.session_state: st.session_state.perfil = None
if "tela_atual" not in st.session_state: st.session_state.tela_atual = "login"
if "tag_equipamento" not in st.session_state: st.session_state.tag_equipamento = None
if "tipo_equipamento" not in st.session_state: st.session_state.tipo_equipamento = None
if "dia_explodido" not in st.session_state: st.session_state.dia_explodido = None

# Base de Usuários Simulada (Pode ir para o Supabase depois)
USUARIOS = {
    "davi": {"senha": "123", "perfil": "gestor", "nome": "Davi Apolinário"},
    "op1": {"senha": "petra", "perfil": "operador", "nome": "Operador Frente 1"}
}

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

# ==========================================
# TELAS DO SISTEMA (FUNÇÕES)
# ==========================================

def tela_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://via.placeholder.com/600x150.png?text=PETRA+AGREGADOS", use_container_width=True)
        st.markdown(f"<h2 style='text-align:center; color:{COR_AZUL};'>Portal de Acesso PCP</h2>", unsafe_allow_html=True)
        with st.form("form_login"):
            usuario = st.text_input("Usuário:")
            senha = st.text_input("Senha:", type="password")
            if st.form_submit_button("Entrar no Sistema", use_container_width=True):
                user_limpo = usuario.lower().strip()
                if user_limpo in USUARIOS and USUARIOS[user_limpo]["senha"] == senha:
                    st.session_state.usuario = USUARIOS[user_limpo]["nome"]
                    st.session_state.perfil = USUARIOS[user_limpo]["perfil"]
                    # Roteamento automático baseado no perfil
                    if st.session_state.perfil == "gestor":
                        st.session_state.tela_atual = "gestor"
                    else:
                        st.session_state.tela_atual = "selecao_maquina"
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

def tela_selecao_maquina():
    st.markdown(f"<h3 style='text-align:center; color:{COR_AZUL};'>Olá, {st.session_state.usuario}</h3>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align:center;'>Selecione o seu equipamento para o turno:</h4>", unsafe_allow_html=True)
    
    res_eq = supabase.table("equipamentos").select("*").eq("ativo", True).execute()
    df_eq = pd.DataFrame(res_eq.data) if res_eq.data else pd.DataFrame([{"tag": "Erro de Conexão", "tipo": "ambos"}])
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_maquina"):
            tag_selecionada = st.selectbox("Máquina Disponível:", df_eq["tag"].tolist())
            if st.form_submit_button("Iniciar Operação", use_container_width=True):
                st.session_state.tag_equipamento = tag_selecionada
                st.session_state.tipo_equipamento = df_eq[df_eq["tag"] == tag_selecionada].iloc[0]["tipo"]
                st.session_state.tela_atual = "operacao"
                st.rerun()

def tela_operacao():
    slot_atual, data_hoje = obter_horario_atual()
    e_caminhao = (st.session_state.tipo_equipamento == "carga")
    
    st.markdown(f"**👤 {st.session_state.usuario}** | **🚜 {st.session_state.tag_equipamento}** | ⏰ **{slot_atual}**")
    
    # Checklists e Paradas
    c_check, c_parada = st.columns(2)
    with c_check:
        with st.popover("📋 Checklist"):
            st.write("Avaliação Rápida")
            # Simulando envio rápido para manter o código limpo
            if st.button("Tudo OK com a Máquina"):
                supabase.table("registros_parciais").insert({"data": data_hoje, "hora": slot_atual, "equipamento": st.session_state.tag_equipamento, "tipo_registro": "Checklist", "detalhes": {"Status": "OK"}}).execute()
                st.success("Enviado!")
    with c_parada:
        with st.popover("🛑 Registrar Parada"):
            res_par = supabase.table("motivos_parada").select("motivo").in_("tipo_equipamento", [st.session_state.tipo_equipamento, 'ambos']).execute()
            opcoes = [m['motivo'] for m in res_par.data] if res_par.data else ["Nenhuma"]
            motivo = st.selectbox("Motivo:", opcoes)
            if st.button("Informar PCP"):
                supabase.table("registros_parciais").insert({"data": data_hoje, "hora": slot_atual, "equipamento": st.session_state.tag_equipamento, "tipo_registro": "Parada", "detalhes": {"motivo": motivo}}).execute()
                st.success("PCP Notificado!")

    st.divider()

    # Lógica de Apontamento
    if slot_atual == "Fora de Turno":
        st.warning("Fora do horário de operação.")
        return

    # Buscar Meta
    res_pcp = supabase.table("pcp_planejamento").select("*").eq("data", data_hoje).execute()
    meta = res_pcp.data[0] if res_pcp.data else {"meta_viagens_equipe_hora": 0, "meta_perf_metros_hora": 0.0}

    st.markdown("<div class='btn-operacao'>", unsafe_allow_html=True)
    if e_caminhao:
        tabela = "horaria_carga"
        coluna = st.session_state.tag_equipamento.lower().replace("-", "")
        # Garante que a linha existe
        res = supabase.table(tabela).select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()
        if not res.data:
            supabase.table(tabela).insert({"data_id": data_hoje, "hora": slot_atual, "ut33": 0, "ut34": 0, "meta": meta["meta_viagens_equipe_hora"], "causa": ""}).execute()
        
        # Lê o valor atual
        valor = supabase.table(tabela).select(coluna).eq("data_id", data_hoje).eq("hora", slot_atual).execute().data[0][coluna]
        
        st.markdown(f"<p style='text-align:center;'>Sua Produção: <b>{valor} viagens</b></p>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 1])
        if c1.button("➖"):
            supabase.table(tabela).update({coluna: max(0, int(valor) - 1)}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
            st.rerun()
        with c2: st.markdown(f"<div class='valor-gigante'>{valor}</div>", unsafe_allow_html=True)
        if c3.button("➕"):
            supabase.table(tabela).update({coluna: int(valor) + 1}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
            st.rerun()
    else:
        # Lógica de Perfuração similar (omitida para manter a resposta compacta, replique a lógica acima alterando para 'horaria_perf')
        st.info("Terminal de Perfuração ativo. (Lógica de + e - igual à carga)")
    st.markdown("</div>", unsafe_allow_html=True)

def tela_gestor():
    st.markdown(f"<h1 style='color: {COR_AZUL};'>📊 Painel de Controle - Operação de Lavra</h1>", unsafe_allow_html=True)
    
    # KPIs rápidos
    df_carga = pd.DataFrame(supabase.table("horaria_carga").select("*").execute().data)
    data_hoje = datetime.now().strftime('%Y-%m-%d')
    viagens_hoje = df_carga[df_carga['data_id'] == data_hoje][['ut33', 'ut34']].sum().sum() if not df_carga.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='kpi-card'><p>Total Viagens Hoje</p><p class='kpi-value'>🚛 {int(viagens_hoje)}</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-card'><p>Status BD</p><p class='kpi-value'>🟢 Online</p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-card'><p>Alertas Parciais</p><p class='kpi-value'>📥 {len(supabase.table('registros_parciais').select('*').eq('data', data_hoje).execute().data)}</p></div>", unsafe_allow_html=True)
    
    st.write("---")
    aba1, aba2 = st.tabs(["📈 Histórico de Produção", "⚙️ Planejamento PCP"])
    
    with aba1:
        if not df_carga.empty:
            df_carga['mes'] = pd.to_datetime(df_carga['data_id']).dt.strftime('%Y-%m')
            df_agrupado = df_carga.groupby('mes')[['ut33', 'ut34']].sum().reset_index()
            fig = px.bar(df_agrupado.melt(id_vars='mes'), x='mes', y='value', color='variable', title="Transporte Mensal")
            st.plotly_chart(fig, use_container_width=True)
            
    with aba2:
        st.info("Calendário de Planejamento Ativo.")

# ==========================================
# CONTROLADOR MESTRE DE ROTAS (STATE MACHINE)
# ==========================================

# 1. Desenhar a barra lateral (se logado)
if st.session_state.perfil is not None:
    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.usuario}**")
        st.markdown(f"🔖 Nível: **{str(st.session_state.perfil).capitalize()}**")
        st.divider()
        
        # Menu de navegação para Gestor
        if st.session_state.perfil == "gestor":
            if st.button("📊 Painel Gerencial", use_container_width=True):
                st.session_state.tela_atual = "gestor"
                st.rerun()
            if st.button("📱 Simular Operador", use_container_width=True):
                st.session_state.tela_atual = "selecao_maquina"
                st.rerun()
                
        # Botão comum de Logout
        st.divider()
        if st.button("🚪 Sair (Logout)", use_container_width=True):
            st.session_state.clear() # Limpa tudo
            st.rerun()

# 2. Chamar a tela correta baseada no estado
if st.session_state.tela_atual == "login":
    tela_login()
elif st.session_state.tela_atual == "selecao_maquina":
    tela_selecao_maquina()
elif st.session_state.tela_atual == "operacao":
    tela_operacao()
elif st.session_state.tela_atual == "gestor":
    if st.session_state.perfil == "gestor":
        tela_gestor()
    else:
        st.error("Acesso Negado.")
