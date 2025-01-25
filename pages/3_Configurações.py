import streamlit as st
import boto3
import json
from botocore.exceptions import ClientError

st.set_page_config(page_title="Configurações - Assistente de Auditoria", page_icon="⚙️", layout="wide")

# Configuração do S3
s3 = boto3.client('s3')
BUCKET = "amh-model-dataset"
AUDITORS_KEY = "user_data_app/auditors/auditors.json"

def load_auditors():
    try:
        response = s3.get_object(Bucket=BUCKET, Key=AUDITORS_KEY)
        return json.loads(response['Body'].read().decode('utf-8'))
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return {"auditors": []}
        raise

def save_auditors(auditors_data):
    s3.put_object(
        Bucket=BUCKET,
        Key=AUDITORS_KEY,
        Body=json.dumps(auditors_data, ensure_ascii=False, indent=2).encode('utf-8'),
        ContentType='application/json'
    )

# Carregar auditores existentes
if 'auditors_data' not in st.session_state:
    st.session_state.auditors_data = load_auditors()

st.title("⚙️ Configurações")

# Seção de Auditores
st.header("👥 Gerenciamento de Auditores")

# Formulário para adicionar novo auditor
with st.form(key="add_auditor_form"):
    st.subheader("Adicionar Novo Auditor")
    
    col1, col2 = st.columns(2)
    with col1:
        new_name = st.text_input("Nome completo", placeholder="Digite o nome do auditor")
        new_email = st.text_input("Email", placeholder="Digite o email do auditor")
    
    with col2:
        # Gerar próximo ID disponível
        existing_ids = [a.get('id', 0) for a in st.session_state.auditors_data.get('auditors', [])]
        next_id = max(existing_ids, default=0) + 1
        new_id = st.number_input("ID", value=next_id, disabled=True)
    
    submit_button = st.form_submit_button("Adicionar Auditor", use_container_width=True)
    
    if submit_button:
        if not new_name or not new_email:
            st.error("Por favor, preencha todos os campos.")
        elif not "@" in new_email:
            st.error("Por favor, insira um email válido.")
        else:
            # Adicionar novo auditor
            new_auditor = {
                "id": new_id,
                "name": new_name,
                "email": new_email
            }
            
            if 'auditors' not in st.session_state.auditors_data:
                st.session_state.auditors_data['auditors'] = []
                
            st.session_state.auditors_data['auditors'].append(new_auditor)
            save_auditors(st.session_state.auditors_data)
            st.success(f"Auditor {new_name} adicionado com sucesso!")
            st.rerun()

# Lista de auditores existentes
st.divider()
st.subheader("Auditores Cadastrados")

if not st.session_state.auditors_data.get('auditors'):
    st.info("Nenhum auditor cadastrado ainda.")
else:
    # Criar uma tabela para exibir os auditores
    auditors_list = st.session_state.auditors_data['auditors']
    
    # Ordenar por ID
    auditors_list = sorted(auditors_list, key=lambda x: x['id'])
    
    # Criar colunas para cada auditor
    cols = st.columns(len(auditors_list))
    
    for idx, auditor in enumerate(auditors_list):
        with cols[idx]:
            st.markdown(f"**ID:** {auditor['id']}")
            st.markdown(f"**Nome:** {auditor['name']}")
            st.markdown(f"**Email:** {auditor['email']}")
            
            # Botão para remover auditor
            if st.button("🗑️ Remover", key=f"remove_{auditor['id']}", use_container_width=True):
                st.session_state.auditors_data['auditors'].remove(auditor)
                save_auditors(st.session_state.auditors_data)
                st.success(f"Auditor {auditor['name']} removido com sucesso!")
                st.rerun() 