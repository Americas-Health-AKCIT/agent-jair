import streamlit as st
from utils.firebase_admin_init import verify_token
import utils.auth_functions as auth_functions
import streamlit.components.v1 as components
# TODO: Add menu items
if 'user_info' not in st.session_state:
    st.switch_page("0_Inicio.py")

# Verify token on each request
decoded_token = verify_token(st.session_state.id_token)
if not decoded_token:
    # Token is invalid or expired, clear session and force re-login
    st.session_state.clear()
    st.session_state.auth_warning = 'Session expired. Please sign in again.'
    st.rerun()


st.set_page_config(page_title="Assistente de Auditoria", page_icon="🔍", layout="wide")
import os
import argparse
import traceback
import json
from botocore.exceptions import ClientError

from langchain_openai import ChatOpenAI
from agentLogic import create_justificativa
from model.inference import fazer_predicao_por_id
from utils.get_requisition_details import get_requisition_details
from config.config import settings
from utils.requisition_history import RequisitionHistory

from langchain_core.pydantic_v1 import ValidationError

from utils.state import STATE_CLASS
from openai import OpenAI
client_openai = OpenAI(api_key=settings.openai_api_key)

# Configuração do S3 para auditores
BUCKET = "amh-model-dataset"
AUDITORS_KEY = "user_data_app/auditors/auditors.json"

def load_auditors():
    """Load auditors from S3"""
    try:
        response = s3.get_object(Bucket=BUCKET, Key=AUDITORS_KEY)
        return json.loads(response['Body'].read().decode('utf-8'))
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return {"auditors": []}
        raise


def change_button_color(widget_label, font_color='white', background_color='rgb(80, 184, 255)'):
    htmlstr = f"""
        <script>
            var elements = window.parent.document.querySelectorAll('button');
            for (var i = 0; i < elements.length; ++i) {{ 
                if (elements[i].innerText == '{widget_label}') {{ 
                    elements[i].style.color = '{font_color}';
                    elements[i].style.background = '{background_color}';
                    elements[i].style.border = '1px solid {background_color}';
                    elements[i].onmouseover = function() {{
                        this.style.backgroundColor = 'rgb(100, 204, 255)';
                    }};
                    elements[i].onmouseout = function() {{
                        this.style.backgroundColor = '{background_color}';
                    }};
                }}
            }}
        </script>
        """
    components.html(f"{htmlstr}", height=0, width=0)

@st.cache_resource
def get_state():
    return STATE_CLASS()

# Removendo o cache do history para forçar recarregamento
history = RequisitionHistory()
s3 = history.s3  # Reutilizar a conexão S3 do RequisitionHistory

state = get_state()

llm = ChatOpenAI(
    model="gpt-4o",
    api_key=settings.openai_api_key
    ) 

show_source = False

# Initialize session state variables
if 'show_source' not in st.session_state:
    st.session_state.show_source = None

if 'n_req' not in st.session_state:
    st.session_state.n_req = None

if 'resumo' not in st.session_state:
    st.session_state.resumo = None

if 'final_output' not in st.session_state:
    st.session_state.final_output = None

if 'feedback' not in st.session_state:
    st.session_state.feedback = {}

# Carregar lista de auditores
current_user = auth_functions.get_current_user_info(st.session_state.id_token)
auditors_data = load_auditors()
auditors_list = auditors_data.get('auditors', [])
auditor_names = [a['name'] for a in auditors_list]
auditor_info = next((a for a in auditors_list if a['email'] == current_user['email']), None)

###############################################################################################
#############################  Streamlit Display - Sidebar  ###################################
###############################################################################################

with st.sidebar:
    st.title("Jair - Assistente de Auditoria")
    # st.write(f"Auditor: {auditor_info['name']}")
    st.write("Digite o número da requisição para receber uma análise detalhada.")
    
    # Campo de entrada da requisição
    if st.session_state.n_req is None:
        n_req_input = st.text_input(
            "Número da requisição:",
            value="",
            placeholder="Digite aqui",
            key='n_req_input'
        )

    else:
        n_req_input = st.text_input(
            "Número da requisição:",
            value=str(st.session_state.n_req),
            placeholder="Digite aqui",
            key='n_req_input_existing'
        )
        
    if not auditor_names:
        st.error("Nenhum auditor cadastrado. Por favor, cadastre um auditor na página de Configurações.")
        auditor_input = None
    elif not auditor_info:
        st.error("Auditor atual não encontrado. Por favor, reporte o problema para o administrador.")
        auditor_input = None
    else:
        auditor_input = auditor_info['name']
            
    send_button = st.button("Enviar", use_container_width=True)
    
    # Link para instruções
    button_label = "ℹ️ 📖 Precisa de ajuda? Consulte as Instruções"
    if st.button(button_label, use_container_width=True, key='help_button_sidebar'):
        st.switch_page("pages/2_Instruções.py")
    change_button_color(button_label, 'blue', 'lightblue')
    
    st.divider()
    
    # Histórico em formato dropdown
    st.title("Histórico")
    requisitions = history.get_all_requisitions()
    if requisitions:
        # Criar lista de opções para o dropdown
        req_options = []
        for req in requisitions:
            req_num = req.get('Número da requisição')
            if req_num:  # Skip invalid entries
                status_icon = "✅" if req.get('has_evaluation') else "⏳"
                req_options.append(f"Requisição {req_num} {status_icon}")
        
        if req_options:
            selected_req = st.selectbox(
                "Requisições anteriores:",
                options=req_options,
                key="history_dropdown"
            )
            
            # Extrair número da requisição da opção selecionada
            selected_req_num = selected_req.split()[1]
            
            if st.button("Carregar Requisição", use_container_width=True):
                complete_req = history.get_complete_requisition(selected_req_num)
                if complete_req:
                    st.session_state.n_req = selected_req_num
                    st.session_state.resumo = complete_req["requisition"]
                    st.session_state.final_output = complete_req["model_output"]
                    st.session_state.auditor = complete_req.get("auditor", "")
                    if complete_req.get("feedback"):
                        st.session_state.feedback = complete_req["feedback"]
                    if complete_req.get("evaluation"):
                        st.session_state.feedback = complete_req["evaluation"]
                    st.rerun()
    else:
        st.write("Nenhuma requisição processada ainda.")

# Update session state when button is clicked
if send_button:
    if not n_req_input or not n_req_input.isdigit():
        st.error('Digite um número de requisição válido.')
    elif not auditor_input:
        st.error('O nome do auditor é obrigatório.')
    else:
        st.session_state.auditor = auditor_input
        # Check if we already have this requisition processed
        complete_req = history.get_complete_requisition(n_req_input)
        if complete_req and complete_req.get("model_output"):
            st.session_state.resumo = complete_req["requisition"]
            st.session_state.final_output = complete_req["model_output"]
            if complete_req.get("feedback"):
                st.session_state.feedback = complete_req["feedback"]
            st.session_state.n_req = n_req_input
        else:
            print("starting to get requisition details")
            resumo = get_requisition_details(int(n_req_input), state)
            
            if resumo == {"Error": "REQUISICAO_ID not found"}:
                st.error("Número da requisição não encontrado. Por favor, confire o número da requisição e tente novamente")
                st.session_state.resumo = None
            else:
                st.session_state.resumo = resumo
                st.session_state.n_req = n_req_input
                st.session_state.final_output = None

###############################################################################################
#############################  Streamlit Display - Resumo Output  #############################
###############################################################################################

is_dark_theme = st.get_option("theme.base") == "dark"


auditor_info = next((a for a in auditors_list if a['email'] == current_user['email']), None)

if not st.session_state.resumo:
    st.subheader(f"Seja Bem-Vindo/a, {auditor_info['name']}!")
    col1_help, col2_help = st.columns([1,1])
    with col1_help:
        button_label_2 = "ℹ️ 📖 Precisa de ajuda? Consulte as Instruções"
        if st.button(button_label_2, use_container_width=True, key='help_button_main'):
            st.switch_page("pages/2_Instruções.py")
        change_button_color(button_label_2, 'blue', 'lightblue')

else:
    st.markdown("""
    <style>
    .summary-card {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid #333;
        height: 100%;
    }
    .card-header {
        border-bottom: 1px solid #333;
        padding-bottom: 10px;
        margin-bottom: 15px;
    }
    .info-grid {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 8px;
        align-items: center;
    }
    .info-label {
        color: #888;
        font-weight: 500;
    }
    .info-value {
        color: #fff;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;
    }
    .status-active {
        background-color: #4CAF50;
        color: white;
    }
    .status-inactive {
        background-color: #f44336;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Cards lado a lado
    col1, col2 = st.columns(2)
    
    # Card do Beneficiário
    with col1:
        with st.container():
            st.subheader("👤 Informações do Beneficiário")
            st.divider()
            
            col_labels1, col_values1 = st.columns([1, 2])
            with col_labels1:
                st.markdown("🔢 **Requisição:**")
                st.markdown("📝 **Nome:**")
                st.markdown("🎂 **Idade:**")
                st.markdown("📋 **Situação:**")
                st.markdown("⏳ **Carência:**")
                # st.markdown("👨‍⚕️ **Auditor:**")
            
            with col_values1:
                st.write(st.session_state.resumo['Número da requisição'])
                st.write(st.session_state.resumo['Nome do beneficiário'])
                st.write(f"{st.session_state.resumo['Idade do beneficiário']} anos")
                st.write(st.session_state.resumo['Situação contratual'])
                st.write(st.session_state.resumo['Período de carência?'])
                # st.write(st.session_state.auditor)
    
    # Card do Atendimento
    with col2:
        with st.container():
            st.subheader("🏥 Informações do Atendimento")
            st.divider()
            
            col_labels2, col_values2 = st.columns([1, 2])
            with col_labels2:
                st.markdown("👨‍⚕️ **Médico:**")
                st.markdown("📅 **Data da Requisição:**")
                st.markdown("🚨 **Caráter:**")
                st.markdown("📄 **Tipo Guia:**")
                st.markdown("🔍 **Itens:**")
            
            with col_values2:
                st.write(st.session_state.resumo['Médico solicitante'])
                st.write(st.session_state.resumo['Data da abertura da requisição'])
                st.write(st.session_state.resumo['Caráter de atendimento (Urgência ou eletiva)'])
                st.write(st.session_state.resumo['Tipo Guia'])
                st.write(f"{len(st.session_state.resumo['Descrição dos procedimentos'])} item(s)")

    st.divider()
    if st.session_state.resumo and st.session_state.final_output is None:
        try:
            is_large = len(st.session_state.resumo['Descrição dos procedimentos'])
            if is_large > 4:
                st.toast('Carregando resposta do Jair, essa requisição pode demorar mais que o esperado...', icon="⏳")
            else:
                st.toast('Carregando resposta do Jair, isso pode demorar até 20 segundos...', icon="⏳")
            with st.spinner(f"O Jair está pensando... ⏳"):
                resultado = fazer_predicao_por_id(st.session_state.resumo['Número da requisição'])

                final_output = create_justificativa(st.session_state.resumo, resultado['resultados_bool_dict'])
                st.session_state.final_output = final_output
                
                # Salvar imediatamente após o RAG
                history.save_complete_requisition(
                    st.session_state.resumo,
                    st.session_state.final_output,
                    None,
                    auditor=st.session_state.auditor
                )
                st.toast('Análise salva com sucesso!', icon="✅")
                
                print("passou")
                print("final output: ", final_output)
                print("\nstate 1: ", st.session_state)
                print("state: ", st.session_state.final_output)
        except ValidationError as e:
            st.error(f"Erro de validação JSON: {e}")
            st.error(traceback.format_exc())
        except Exception as e:
            st.error(f"Erro inesperado: {e}")
            st.error(traceback.format_exc())

###############################################################################################
#############################  Streamlit Display - Jair Output  ###############################
###############################################################################################

auditor_notification = st.empty()
if 'auditor_success' in st.session_state:
    st.toast(st.session_state.auditor_success, icon="✅")
    del st.session_state.auditor_success

if st.session_state.final_output:
    st.markdown("""
    <style>
    .item-card {
        background-color: {('#1E1E1E' if is_dark_theme else '#FFFFFF')};
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid {('#333' if is_dark_theme else '#E0E0E0')};
    }
    .item-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }
    .evaluation-section {
        background-color: {('#2A2A2A' if is_dark_theme else '#F5F5F5')};
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .button-row {
        display: flex;
        gap: 10px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## Itens da Requisição")
    st.write("")

    for idx, item in enumerate(st.session_state.final_output["items"]):
        # Card principal do item
        st.markdown(f"""
        <div class="item-card">
            <div class="item-header">
                <h3>🔍 {item['description']}</h3>
                <p>🏷️ Código: {item['Código correspondente ao item']}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Conteúdo do card
        col_info, col_status = st.columns([3, 1])
        
        with col_info:
            situacao = item.get('Situação', 'Jair não conseguiu processar esse item')
            if "AUTORIZADO" in situacao:
                st.success(f"🤖 **Avaliação do Jair:** {situacao}")
            elif "NEGADO" in situacao or "RECUSADO" in situacao:
                st.error(f"🤖 **Avaliação do Jair:** {situacao}")
            else:
                st.warning(f"🤖 **Avaliação do Jair:** {situacao}")
        
        with col_status:
            toggle_state = st.toggle("🔍 Ver análise completa", key=f"toggle_{idx}")

        # Seção de avaliação do auditor
        st.markdown('<div class="evaluation-section">', unsafe_allow_html=True)
        
        # Primeira linha: Decisão e Qualidade
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("👨‍⚕️ **Decisão do Auditor**")
            # Mostrar status atual se existir
            if "auditor" in item and "authorized_item" in item["auditor"]:
                current_status = "✅ Aprovado" if item["auditor"]["authorized_item"] else "❌ Recusado"
                st.info(f"📌 Status atual: {current_status}")
            
            col_apr, col_rec = st.columns(2)
            with col_apr:
                approved = st.button("✅ Aprovar", key=f"approve_{idx}", 
                                   use_container_width=True,
                                   type="secondary" if not item.get("auditor", {}).get("authorized_item", None) else "primary")
            with col_rec:
                rejected = st.button("❌ Recusar", key=f"reject_{idx}", 
                                   use_container_width=True,
                                   type="secondary" if item.get("auditor", {}).get("authorized_item", None) else "primary")
        
        with col2:
            st.write("⭐ **Avaliação da Resposta**")
            # Mostrar avaliação atual se existir
            if "auditor" in item and "quality_rating" in item["auditor"]:
                current_rating = "👍 Boa" if item["auditor"]["quality_rating"] else "👎 Ruim"
                st.info(f"📌 Avaliação atual: {current_rating}")
                
            col_like, col_dislike = st.columns(2)
            with col_like:
                liked = st.button("👍 Boa", key=f"like_{idx}", 
                                use_container_width=True,
                                type="secondary" if not item.get("auditor", {}).get("quality_rating", None) else "primary")
            with col_dislike:
                disliked = st.button("👎 Ruim", key=f"dislike_{idx}", 
                                   use_container_width=True,
                                   type="secondary" if item.get("auditor", {}).get("quality_rating", None) else "primary")

        # Campo de comentários
        st.write("💭 **Comentários**")
        previous_comment = item.get("auditor", {}).get("comments", "")
        comment = st.text_area(
            "Adicione seus comentários sobre este item:",
            value=previous_comment,
            key=f"comment_{idx}",
            height=100,
            placeholder="Digite aqui seus comentários sobre a avaliação..."
        )
        
        # Atualizar estados e salvar
        if approved:
            if "auditor" not in item:
                item["auditor"] = {}
            item["auditor"]["authorized_item"] = True
            history.save_complete_requisition(st.session_state.resumo, st.session_state.final_output, None, auditor=st.session_state.auditor)
            st.session_state.auditor_success = 'Avaliação salva!'
            st.rerun()
        elif rejected:
            if "auditor" not in item:
                item["auditor"] = {}
            item["auditor"]["authorized_item"] = False
            history.save_complete_requisition(st.session_state.resumo, st.session_state.final_output, None, auditor=st.session_state.auditor)
            st.session_state.auditor_success = 'Avaliação salva!'
            st.rerun()
        if liked:
            if "auditor" not in item:
                item["auditor"] = {}
            item["auditor"]["quality_rating"] = True
            history.save_complete_requisition(st.session_state.resumo, st.session_state.final_output, None, auditor=st.session_state.auditor)
            st.session_state.auditor_success = 'Avaliação salva!'
            st.rerun()
        elif disliked:
            if "auditor" not in item:
                item["auditor"] = {}
            item["auditor"]["quality_rating"] = False
            history.save_complete_requisition(st.session_state.resumo, st.session_state.final_output, None, auditor=st.session_state.auditor)
            st.session_state.auditor_success = 'Avaliação salva!'
            st.rerun()

        if comment != previous_comment:
            if "auditor" not in item:
                item["auditor"] = {}
            item["auditor"]["comments"] = comment
            history.save_complete_requisition(st.session_state.resumo, st.session_state.final_output, None, auditor=st.session_state.auditor)
            st.toast('Comentário salvo!', icon="✅")

        st.markdown('</div>', unsafe_allow_html=True)

        # Análise detalhada (expandida)
        if toggle_state:
            with st.expander("Análise do Jair", expanded=True):
                st.markdown(item['analysis'])
                st.write("**Fonte:**")
                source_raw = item.get('source', 'Jair não conseguiu processar esse item')
                source = list(source_raw.items())[0][1]
                st.info(source)

        st.write("")
        st.write("")

    # Botão de reiniciar
    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        if st.button("🔎 Nova Consulta", use_container_width=True):
            for key in ['n_req', 'resumo', 'final_output', 'feedback']:
                st.session_state[key] = None
            st.rerun()

    # st.json(st.session_state.final_output)

if __name__ == "__main__":

    if 'run_once' not in st.session_state:
        # This block will only run once
        parser = argparse.ArgumentParser(description="Assistente de Auditoria")
        parser.add_argument('--dev', action='store_true', help="Show the sidebar (dev mode)")
        try:
            args = parser.parse_args()
        except SystemExit as e:
            os._exit(e.code)

        # Store the dev_mode flag and mark that argparse has run
        st.session_state.dev_mode = args.dev
        st.session_state.run_once = True 
        st.rerun()
    
    print("App rodando")

