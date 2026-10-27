import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

st.set_page_config(page_title="Terminal Operador", layout="centered")

COR_AZUL = "#54728c"
COR_AMARELA = "#ffc107"

st.markdown(f"""
    <style>
    div[data-testid="stButton"] button {{ height: 100px; font-size: 40px; font-weight: bold; width: 100%; border-radius: 15px; background-color: {COR_AZUL}; color: white; }}
    div[data-testid="stButton"] button:active {{ background-color: {COR_AMARELA}; color: black; }}
    .btn-parcial button {{ height: 50px !important; font-size: 18px !important; background-color: {COR_AMARELA} !important; color: black !important; }}
    .valor-gigante {{ font-size: 70px; font-weight: bold; text-align: center; color: {COR_AMARELA}; margin-top: -10px; margin-bottom: -10px; }}
    .titulo-hora {{ text-align: center; color: gray; font-size: 20px; }}
    .meta-box {{ background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; border-left: 5px solid {COR_AZUL}; margin-bottom: 10px; }}
    .meta-destaque {{ font-size: 25px; font-weight: bold; color: {COR_AZUL}; display: block; margin-top: 5px;}}
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM A NUVEM ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

def obter_horario_atual():
    agora = datetime.now()
    hora = agora.hour
    if 7 <= hora < 8: slot = "07:15"
    elif 8 <= hora < 9: slot = "08:00"
    elif 9 <= hora < 10: slot = "09:00"
    elif 10 <= hora < 11: slot = "10:00"
    elif 11 <= hora < 12: slot = "11:00"
    elif 13 <= hora < 14: slot = "13:00"
    elif 14 <= hora < 15: slot = "14:00"
    elif 15 <= hora < 16: slot = "15:00"
    elif 16 <= hora < 17: slot = "16:00"
    else: slot = "Fora de Turno"
    return slot, agora.strftime('%Y-%m-%d')

if 'logado' not in st.session_state: st.session_state.logado = False

# --- TELA DE LOGIN DINÂMICA ---
if not st.session_state.logado:
    st.image("https://via.placeholder.com/600x150.png?text=PETRA+AGREGADOS", use_container_width=True)
    st.markdown(f"<h2 style='text-align:center; color:{COR_AZUL};'>Acesso Operacional Nuvem</h2>", unsafe_allow_html=True)
    
    # Busca equipamentos ativos no banco
    res_eq = supabase.table("equipamentos").select("*").eq("ativo", True).execute()
    df_eq = pd.DataFrame(res_eq.data) if res_eq.data else pd.DataFrame([{"tag": "Sem Conexão", "tipo": "ambos"}])
    
    with st.form("form_login"):
        login = st.text_input("Seu Login (Nome/Matrícula):")
        tag_selecionada = st.selectbox("Equipamento:", df_eq["tag"].tolist())
        
        if st.form_submit_button("Entrar", use_container_width=True) and login:
            st.session_state.logado = True
            st.session_state.usuario = login
            st.session_state.tag = tag_selecionada
            st.session_state.tipo_eq = df_eq[df_eq["tag"] == tag_selecionada].iloc[0]["tipo"]
            st.rerun()

# --- TELA DE OPERAÇÃO ---
else:
    st.markdown(f"**👤 {st.session_state.usuario}** | **🚜 {st.session_state.tag}**")
    if st.button("Sair", key="btn_sair"):
        st.session_state.logado = False
        st.rerun()
    st.divider()

    data_hoje = datetime.now().strftime('%Y-%m-%d')
    slot_atual, _ = obter_horario_atual()
    e_caminhao = (st.session_state.tipo_eq == "carga")

    # --- ABA 1: CHECKLIST SEPARADO ---
    with st.expander("📋 Preencher Checklist", expanded=False):
        st.markdown("**Avaliação do Equipamento**")
        res_chk = supabase.table("itens_checklist").select("item").in_("tipo_equipamento", [st.session_state.tipo_eq, 'ambos']).execute()
        
        respostas_chk = {}
        if res_chk.data:
            for i, linha in enumerate(res_chk.data):
                item = linha['item']
                respostas_chk[item] = st.selectbox(f"{item}:", ["OK", "Requer Atenção", "Crítico"], key=f"chk_{i}")
        
        st.markdown("<div class='btn-parcial'>", unsafe_allow_html=True)
        if st.button("📤 Enviar Checklist Parcial", use_container_width=True):
            supabase.table("registros_parciais").insert({
                "data": data_hoje, "hora": slot_atual, "equipamento": st.session_state.tag,
                "operador": st.session_state.usuario, "tipo_registro": "Checklist", "detalhes": respostas_chk
            }).execute()
            st.success("Checklist enviado para o PCP!")
        st.markdown("</div>", unsafe_allow_html=True)

    # --- ABA 2: REGISTRO DE PARADAS SEPARADO ---
    with st.expander("🛑 Registrar Parada", expanded=False):
        st.markdown("**Motivo da Parada Atual**")
        res_par = supabase.table("motivos_parada").select("motivo").in_("tipo_equipamento", [st.session_state.tipo_eq, 'ambos']).execute()
        opcoes_parada = [m['motivo'] for m in res_par.data] if res_par.data else ["Nenhuma"]
        
        motivo_sel = st.selectbox("Selecione o Motivo:", opcoes_parada)
        
        st.markdown("<div class='btn-parcial'>", unsafe_allow_html=True)
        if st.button("📤 Enviar Parada Parcial", use_container_width=True):
            # Salva no histórico de envios parciais
            supabase.table("registros_parciais").insert({
                "data": data_hoje, "hora": slot_atual, "equipamento": st.session_state.tag,
                "operador": st.session_state.usuario, "tipo_registro": "Parada", "detalhes": {"motivo": motivo_sel}
            }).execute()
            
            # Atualiza também o gráfico principal de pizza do gestor
            tabela_gestor = "horaria_carga" if e_caminhao else "horaria_perf"
            supabase.table(tabela_gestor).update({"causa": motivo_sel}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
            
            st.success("Parada registrada! O Gestor já foi notificado.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # --- LÓGICA DE APONTAMENTO (Tempo Real) ---
    res_pcp = supabase.table("pcp_planejamento").select("*").eq("data", data_hoje).execute()
    df_pcp = pd.DataFrame(res_pcp.data)
    meta_viagens = df_pcp.iloc[0]['meta_viagens_equipe_hora'] if not df_pcp.empty else 0
    meta_metros = df_pcp.iloc[0]['meta_perf_metros_hora'] if not df_pcp.empty else 0.0

    meta_valida = (meta_viagens > 0) if e_caminhao else (meta_metros > 0)

    if slot_atual == "Fora de Turno":
        st.warning("Fora do horário de operação da mina.")
    else:
        st.markdown(f"<p class='titulo-hora'>Horário: <b>{slot_atual}</b></p>", unsafe_allow_html=True)
        
        if e_caminhao:
            res_hora = supabase.table("horaria_carga").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()
            if not res_hora.data:
                supabase.table("horaria_carga").insert({"data_id": data_hoje, "hora": slot_atual, "ut33": 0, "ut34": 0, "meta": meta_viagens, "causa": ""}).execute()
                res_hora = supabase.table("horaria_carga").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                
            df_hora = pd.DataFrame(res_hora.data)
            coluna_db = st.session_state.tag.lower().replace("-", "")
            
            # Se for um caminhão novo que não tem coluna na tabela horaria_carga, o sistema avisa:
            if coluna_db not in df_hora.columns:
                st.error(f"Erro: O equipamento {st.session_state.tag} ainda não tem uma coluna na base de dados de carga.")
            else:
                valor_individual = df_hora.iloc[0][coluna_db]
                valor_equipe = sum([df_hora.iloc[0][col] for col in df_hora.columns if 'ut' in col.lower()])
                
                st.markdown(f"""
                    <div class='meta-box'>
                        <div>Sua Carga: <b>{valor_individual} viagens</b></div>
                        <div style='margin-top:5px;'>Carga Total da Equipe: <span class='meta-destaque'>{valor_equipe} / {meta_viagens if meta_viagens > 0 else 'N/A'} viagens</span></div>
                    </div>
                """, unsafe_allow_html=True)

                c_menos, c_valor, c_mais = st.columns([1, 1.5, 1])
                with c_menos:
                    if st.button("➖", key="sub_v"):
                        supabase.table("horaria_carga").update({coluna_db: max(0, int(valor_individual) - 1)}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                        st.rerun()
                with c_valor:
                    st.markdown(f"<div class='valor-gigante'>{int(valor_individual)}</div>", unsafe_allow_html=True)
                with c_mais:
                    if st.button("➕", key="add_v"):
                        supabase.table("horaria_carga").update({coluna_db: int(valor_individual) + 1}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                        st.rerun()

        else: # É PERFURATRIZ
            res_hora = supabase.table("horaria_perf").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()
            if not res_hora.data:
                supabase.table("horaria_perf").insert({"data_id": data_hoje, "hora": slot_atual, "realizado": 0.0, "meta": meta_metros, "causa": ""}).execute()
                res_hora = supabase.table("horaria_perf").select("*").eq("data_id", data_hoje).eq("hora", slot_atual).execute()

            df_hora = pd.DataFrame(res_hora.data)
            valor_perf = df_hora.iloc[0]['realizado']
            
            st.markdown(f"""
                <div class='meta-box'>
                    <div>Perfuração Realizada: <span class='meta-destaque'>{valor_perf:.1f} / {meta_metros if meta_metros > 0 else 'N/A'} metros</span></div>
                </div>
            """, unsafe_allow_html=True)

            c_menos, c_valor, c_mais = st.columns([1, 1.5, 1])
            with c_menos:
                if st.button("➖", key="sub_p"):
                    supabase.table("horaria_perf").update({"realizado": max(0.0, float(valor_perf) - 1.0)}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                    st.rerun()
            with c_valor:
                st.markdown(f"<div class='valor-gigante'>{valor_perf:.1f}</div>", unsafe_allow_html=True)
            with c_mais:
                if st.button("➕", key="add_p"):
                    supabase.table("horaria_perf").update({"realizado": float(valor_perf) + 1.0}).eq("data_id", data_hoje).eq("hora", slot_atual).execute()
                    st.rerun()