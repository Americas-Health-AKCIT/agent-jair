import streamlit as st
from utils.firebase_admin_init import verify_token
from utils.requisition_history import RequisitionHistory
from utils.streamlit_utils import change_button_color
from utils.get_user_info import load_auditors
import utils.auth_functions as auth_functions
from utils.get_requisition_details import get_requisition_details
from utils.streamlit_utils import render_requisition_search

if 'user_info' not in st.session_state:
    st.switch_page("0_Inicio.py")

# Verify token on each request
decoded_token = verify_token(st.session_state.id_token)
if not decoded_token:
    # Token is invalid or expired, clear session and force re-login
    st.session_state.clear()
    st.session_state.auth_warning = 'Session expired. Please sign in again.'
    st.rerun()

BUCKET = "amh-model-dataset"
AUDITORS_KEY = "user_data_app/auditors/auditors.json"
history = RequisitionHistory()
s3 = history.s3

current_user = auth_functions.get_current_user_info(st.session_state.id_token)
auditors_data = load_auditors(s3, BUCKET, AUDITORS_KEY)
auditors_list = auditors_data.get("auditors", [])
auditor_names = [a["name"] for a in auditors_list]
auditor_info = next(
    (a for a in auditors_list if a["email"] == current_user["email"]), None
)

with st.sidebar:
    render_requisition_search(st.sidebar, auditor_names, auditor_info, history)

st.markdown("""
<style>
.instruction-card {
    background-color: {('#1E1E1E' if is_dark_theme else '#FFFFFF')};
    border-radius: 10px;
    padding: 20px;
    margin: 10px 0;
    border: 1px solid {('#333' if is_dark_theme else '#E0E0E0')};
}
.big-number {
    font-size: 24px;
    font-weight: bold;
    color: #4CAF50;
    margin-right: 10px;
}
.highlight {
    background-color: {('#2A2A2A' if is_dark_theme else '#F5F5F5')};
    padding: 2px 6px;
    border-radius: 4px;
}
</style>
""", unsafe_allow_html=True)

st.title("📖 Instruções de Uso")

# Visão Geral
st.header("Visão Geral")
st.markdown("""
O Jair é um assistente de auditoria projetado para auxiliar na análise e tomada de decisões sobre requisições médicas.
Ele utiliza inteligência artificial para analisar documentos e fornecer recomendações baseadas em diretrizes e práticas estabelecidas.
""")

# Como Usar
st.header("Como Usar o Sistema")

# Passo 1
st.markdown("""
<div class="instruction-card">
    <h3><span class="big-number">1</span> Inserindo uma Requisição</h3>
    <ul>
        <li>Digite o número da requisição no campo de entrada</li>
        <li>Clique no botão "Enviar"</li>
        <li>O sistema carregará automaticamente os detalhes da requisição</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Passo 2
st.markdown("""
<div class="instruction-card">
    <h3><span class="big-number">2</span> Analisando a Requisição</h3>
    <ul>
        <li>Revise o resumo da requisição com informações do beneficiário e procedimentos</li>
        <li>Examine a análise do Jair para cada item</li>
        <li>Verifique as fontes citadas clicando em "Ver análise completa"</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Passo 3
st.markdown("""
<div class="instruction-card">
    <h3><span class="big-number">3</span> Avaliando os Itens</h3>
    <ul>
        <li>Para cada item, você pode:
            <ul>
                <li>Aprovar ou recusar o item</li>
                <li>Avaliar a qualidade da resposta do Jair (👍 Boa ou 👎 Ruim)</li>
                <li>Adicionar comentários sobre sua decisão</li>
            </ul>
        </li>
        <li>Suas avaliações são salvas automaticamente</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Pontos Importantes
st.header("Pontos Importantes")
st.markdown("""
<div class="instruction-card">
    <h4>⚠️ Atenção</h4>
    <ul>
        <li>O Jair pode autorizar ou negar uma requisição com condições específicas - <span class="highlight">leia sempre a justificativa completa</span></li>
        <li>O assistente é uma ferramenta de apoio - <span class="highlight">a decisão final é sempre do auditor</span></li>
        <li>Verifique sempre as fontes citadas para garantir a precisão das informações</li>
        <li>Suas avaliações ajudam a melhorar o sistema - <span class="highlight">forneça feedback detalhado</span></li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Histórico
st.header("Histórico de Requisições")
st.markdown("""
<div class="instruction-card">
    <h4>📋 Acessando Requisições Anteriores</h4>
    <ul>
        <li>Use o menu lateral para ver requisições anteriores</li>
        <li>Requisições são marcadas como:
            <ul>
                <li>✅ Avaliada - quando você já completou a análise</li>
                <li>⏳ Pendente avaliação - quando ainda precisa ser analisada</li>
            </ul>
        </li>
        <li>Clique em qualquer requisição para retomar sua análise</li>
    </ul>
</div>
""", unsafe_allow_html=True) 