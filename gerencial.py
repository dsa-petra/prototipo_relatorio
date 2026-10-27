import streamlit as st
import pandas as pd
import plotly.express as px
import calendar
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from supabase import create_client, Client

st.set_page_config(page_title="Gestão PCP Petra", layout="wide", page_icon="📊")
st_autorefresh(interval=10000, limit=None, key="atualizacao_continua")

COR_AZUL_PETRA = "#54728c"
COR_AMARELO_PETRA = "#ffc107"
COR_FUNDO_GRAFICO = "rgba(0,0,0,0)"

st.markdown(f"""
    <style>
    .kpi-card {{ background-color: {COR_AZUL_PETRA}; color: white; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid {COR_AMARELO_PETRA}; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }}
    .kpi-title {{ font-size: 1.1rem; margin-bottom: 5px; opacity: 0.9; }}
    .kpi-value {{ font-size: 2.5rem; font-weight: bold; color: {COR_AMARELO_PETRA}; margin: 0; }}
    .cal-header {{ font-weight: bold; text-align: center; color: {COR_AZUL_PETRA}; background-color: #f0f2f6; padding: 5px; border-radius: 5px; }}
    </style>
""", unsafe_allow_html=True)

col_logo, col_titulo = st.columns([1, 4])
with col_titulo:
    st.markdown(f"<h1 style='color: {COR_AZUL_PETRA};'>📊 Painel de Controle - Operação de Lavra</h1>", unsafe_allow_html=True)
    st.markdown(f"**Gestor:** Davi da Silva Apolinário (CREA-MG 433115) | **Status:** <span style='color:{COR_AMARELO_PETRA};'>⚫ Nuvem (Supabase) Ativa</span>", unsafe_allow_html=True)

st.divider()

# --- CONEXÃO COM A NUVEM (SUPABASE) ---
@st.cache_resource
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()
def carregar_dados():
    carga = supabase.table("horaria_carga").select("*").execute()
    perf = supabase.table("horaria_perf").select("*").execute()
    parte = supabase.table("parte_diaria").select("*").execute()
    pcp = supabase.table("pcp_planejamento").select("*").execute()
    
    return pd.DataFrame(carga.data), pd.DataFrame(perf.data), pd.DataFrame(parte.data), pd.DataFrame(pcp.data)

def meses_disponiveis():
    hoje = datetime.today()
    meses = []
    for i in range(6, -1, -1):
        d = hoje.replace(day=1) - timedelta(days=30*i)
        meses.append((d.year, d.month))
    
    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    dias_restantes = ultimo_dia - hoje.day
    if dias_restantes <= 3:
        prox_mes = (hoje.replace(day=28) + timedelta(days=4))
        meses.append((prox_mes.year, prox_mes.month))
    
    opcoes = [f"{m[0]}-{m[1]:02d}" for m in meses]
    return opcoes, opcoes[-1] if dias_restantes <= 3 else opcoes[-2]

lista_meses, mes_padrao = meses_disponiveis()
if 'dia_explodido' not in st.session_state: st.session_state.dia_explodido = None

try:
    df_carga, df_perf, df_parte, df_pcp = carregar_dados()
    data_hoje_str = datetime.today().strftime('%Y-%m-%d')
    
    df_carga_hoje = df_carga[df_carga['data_id'] == data_hoje_str] if not df_carga.empty else pd.DataFrame()
    total_viagens = df_carga_hoje['ut33'].sum() + df_carga_hoje['ut34'].sum() if not df_carga_hoje.empty else 0
    df_perf_hoje = df_perf[df_perf['data_id'] == data_hoje_str] if not df_perf.empty else pd.DataFrame()
    total_metros = df_perf_hoje['realizado'].sum() if not df_perf_hoje.empty else 0

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"<div class='kpi-card'><p class='kpi-title'>Total de Viagens (Hoje)</p><p class='kpi-value'>🚛 {int(total_viagens)}</p></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='kpi-card'><p class='kpi-title'>Metros Perfurados (Hoje)</p><p class='kpi-value'>🎯 {total_metros:.1f} m</p></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='kpi-card'><p class='kpi-title'>Relatórios de Turno</p><p class='kpi-value'>📋 {len(df_parte)}</p></div>", unsafe_allow_html=True)
    st.write("") 

    aba_graficos, aba_pcp, aba_diretoria, aba_dados = st.tabs(["📈 Produção (Hoje)", "⚙️ Planejamento PCP (Calendário)", "📊 Visão Diretoria", "🗄️ Dados Brutos"])

    with aba_pcp:
        st.subheader("Planejamento Mensal de Lavra")
        col_mes, col_info = st.columns([1, 3])
        with col_mes:
            mes_selecionado = st.selectbox("Selecione o Mês:", reversed(lista_meses), index=list(reversed(lista_meses)).index(mes_padrao))
        with col_info:
            st.info("💡 A abertura do próximo mês só é liberada quando faltam **3 dias** para o encerramento do mês atual.")

        ano_sel, mes_sel = map(int, mes_selecionado.split('-'))
        cal = calendar.Calendar(firstweekday=6)
        matriz_dias = cal.monthdayscalendar(ano_sel, mes_sel)
        
        st.markdown("### Calendário Operacional")
        dias_semana = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SAB"]
        cols_dias = st.columns(7)
        for i, d in enumerate(dias_semana):
            cols_dias[i].markdown(f"<div class='cal-header'>{d}</div>", unsafe_allow_html=True)
        
        for semana in matriz_dias:
            cols_semana = st.columns(7)
            for i, dia in enumerate(semana):
                if dia != 0:
                    data_formatada = f"{ano_sel}-{mes_sel:02d}-{dia:02d}"
                    tipo_botao = "primary" if data_formatada == data_hoje_str else "secondary"
                    if cols_semana[i].button(f"{dia:02d}", key=data_formatada, type=tipo_botao, use_container_width=True):
                        st.session_state.dia_explodido = data_formatada
                else:
                    cols_semana[i].write("")

        st.divider()

        if st.session_state.dia_explodido:
            dia_alvo = st.session_state.dia_explodido
            st.markdown(f"### Detalhes do Dia: <span style='color:{COR_AMARELO_PETRA}'>{dia_alvo}</span>", unsafe_allow_html=True)
            
            df_dia_carga = df_carga[df_carga['data_id'] == dia_alvo] if not df_carga.empty else pd.DataFrame()
            df_dia_perf = df_perf[df_perf['data_id'] == dia_alvo] if not df_perf.empty else pd.DataFrame()
            
            realizado_viagens = (df_dia_carga['ut33'].sum() + df_dia_carga['ut34'].sum()) if not df_dia_carga.empty else 0
            realizado_metros = df_dia_perf['realizado'].sum() if not df_dia_perf.empty else 0
            
            df_meta = df_pcp[df_pcp['data'] == dia_alvo] if not df_pcp.empty else pd.DataFrame()
            meta_viagens = df_meta.iloc[0]['meta_viagens_equipe_hora'] if not df_meta.empty else 0
            meta_metros = df_meta.iloc[0]['meta_perf_metros_hora'] if not df_meta.empty else 0.0

            if (realizado_viagens > 0 or realizado_metros > 0) and (meta_viagens == 0 and meta_metros == 0):
                st.error("⚠️ **ATENÇÃO:** Existem apontamentos operacionais neste dia, mas ele **não estava planejado** no PCP! (Fora de Especificação)")

            with st.form(f"form_pcp_{dia_alvo}"):
                c_prod, c_perf, c_real = st.columns(3)
                with c_prod:
                    st.markdown("**🚛 Produção (Carga e Transporte)**")
                    nova_meta_v = st.number_input("Meta da Equipe (Viagens/Hora):", value=int(meta_viagens), step=1)
                with c_perf:
                    st.markdown("**🎯 Perfuração (Desmonte)**")
                    nova_meta_m = st.number_input("Meta (Metros/Hora):", value=float(meta_metros), step=1.0)
                with c_real:
                    st.markdown("**📊 Status Operacional Real**")
                    st.metric("Carga Executada", f"{int(realizado_viagens)} viagens")
                    st.metric("Perfuração Executada", f"{realizado_metros:.1f} m")
                    
                if st.form_submit_button("💾 Salvar Planejamento na Nuvem", use_container_width=True):
                    # Inserir/Atualizar no Supabase (Upsert)
                    supabase.table("pcp_planejamento").upsert({
                        "data": dia_alvo, 
                        "meta_viagens_equipe_hora": nova_meta_v, 
                        "meta_perf_metros_hora": nova_meta_m
                    }).execute()
                    st.success(f"PCP de {dia_alvo} atualizado na nuvem!")
                    st.rerun()
        else:
            st.info("👆 Clique em um dia no calendário acima.")

    with aba_graficos:
        st.info("Vá para a aba 'Planejamento PCP' (Calendário) para gerir as metas e apontamentos.")

    with aba_diretoria:
        st.markdown("### 📊 Consolidado de Produção - Histórico Global")
        
        if not df_carga.empty and not df_perf.empty:
            # 1. Preparar Datas
            df_carga['data_dt'] = pd.to_datetime(df_carga['data_id'])
            df_carga['ano'] = df_carga['data_dt'].dt.year.astype(str)
            df_carga['mes'] = df_carga['data_dt'].dt.strftime('%m')
            df_carga['ano_mes'] = df_carga['data_dt'].dt.strftime('%Y-%m')

            df_perf['data_dt'] = pd.to_datetime(df_perf['data_id'])
            df_perf['ano'] = df_perf['data_dt'].dt.year.astype(str)
            df_perf['mes'] = df_perf['data_dt'].dt.strftime('%m')
            df_perf['ano_mes'] = df_perf['data_dt'].dt.strftime('%Y-%m')

            # 2. Criar Filtros Dinâmicos
            anos_disponiveis = sorted(list(set(df_carga['ano'].unique()).union(set(df_perf['ano'].unique()))), reverse=True)
            meses_opcoes = ["Todos os Meses", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
            
            st.markdown("<div style='background-color:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:20px;'>", unsafe_allow_html=True)
            col_filtro1, col_filtro2, _ = st.columns([1, 1, 2])
            ano_filtro = col_filtro1.selectbox("📅 Filtrar por Ano:", ["Todos os Anos"] + anos_disponiveis)
            mes_filtro = col_filtro2.selectbox("📆 Filtrar por Mês:", meses_opcoes)
            st.markdown("</div>", unsafe_allow_html=True)

            # 3. Aplicar Filtros aos Dados
            df_c_filtrado = df_carga.copy()
            df_p_filtrado = df_perf.copy()

            if ano_filtro != "Todos os Anos":
                df_c_filtrado = df_c_filtrado[df_c_filtrado['ano'] == ano_filtro]
                df_p_filtrado = df_p_filtrado[df_p_filtrado['ano'] == ano_filtro]
                
            if mes_filtro != "Todos os Meses":
                df_c_filtrado = df_c_filtrado[df_c_filtrado['mes'] == mes_filtro]
                df_p_filtrado = df_p_filtrado[df_p_filtrado['mes'] == mes_filtro]

            # 4. Desenhar Gráficos se houver dados
            if df_c_filtrado.empty and df_p_filtrado.empty:
                st.warning("⚠️ Nenhum dado de produção registado para o período selecionado.")
            else:
                df_carga_mes = df_c_filtrado.groupby('ano_mes')[['ut33', 'ut34']].sum().reset_index()
                df_perf_mes = df_p_filtrado.groupby('ano_mes')['realizado'].sum().reset_index()

                col_dir1, col_dir2 = st.columns(2)
                
                with col_dir1:
                    st.markdown("**Volume Total de Viagens Transportadas**")
                    if not df_carga_mes.empty:
                        df_carga_mes_melt = df_carga_mes.melt(id_vars=['ano_mes'], value_vars=['ut33', 'ut34'], var_name='Caminhão', value_name='Total Viagens')
                        fig_hist_carga = px.bar(df_carga_mes_melt, x='ano_mes', y='Total Viagens', color='Caminhão', barmode='stack', color_discrete_sequence=[COR_AZUL_PETRA, COR_AMARELO_PETRA])
                        fig_hist_carga.update_layout(plot_bgcolor=COR_FUNDO_GRAFICO, paper_bgcolor=COR_FUNDO_GRAFICO, xaxis_title="Mês / Ano", yaxis_title="Nº de Viagens")
                        st.plotly_chart(fig_hist_carga, use_container_width=True)
                    else:
                        st.info("Sem dados de transporte para este filtro.")
                    
                with col_dir2:
                    st.markdown("**Total de Metros Perfurados**")
                    if not df_perf_mes.empty:
                        fig_hist_perf = px.area(df_perf_mes, x='ano_mes', y='realizado', color_discrete_sequence=[COR_AMARELO_PETRA])
                        fig_hist_perf.update_layout(plot_bgcolor=COR_FUNDO_GRAFICO, paper_bgcolor=COR_FUNDO_GRAFICO, xaxis_title="Mês / Ano", yaxis_title="Metros (m)")
                        st.plotly_chart(fig_hist_perf, use_container_width=True)
                    else:
                        st.info("Sem dados de perfuração para este filtro.")
        else:
            st.warning("A aguardar os primeiros dados da nuvem para desenhar o histórico.")
except Exception as erro:
    st.error(f"Erro ao carregar ou processar os dados: {erro}")
