import streamlit as st
import boto3
import json
from botocore.exceptions import ClientError
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Resultados - Assistente de Auditoria", page_icon="📊", layout="wide")

# Configuração do S3
s3 = boto3.client('s3')
BUCKET = "amh-model-dataset"
BASE_PREFIX = "user_data_app/requisitions"

def load_all_requisitions():
    """Carrega todas as requisições do S3 para análise"""
    requisitions = []
    try:
        # Listar todos os objetos no diretório de requisições
        response = s3.list_objects_v2(Bucket=BUCKET, Prefix=BASE_PREFIX)
        
        for obj in response.get('Contents', []):
            if obj['Key'].endswith('.json'):
                file_response = s3.get_object(Bucket=BUCKET, Key=obj['Key'])
                req_data = json.loads(file_response['Body'].read().decode('utf-8'))
                requisitions.append(req_data)
                
        return requisitions
    except Exception as e:
        st.error(f"Erro ao carregar requisições: {str(e)}")
        return []

def extract_items_data(requisitions):
    """Extrai dados dos itens para análise"""
    items_data = []
    
    for req in requisitions:
        if not req.get('model_output') or not req['model_output'].get('items'):
            continue
            
        req_id = req['requisition']['Número da requisição']
        timestamp = datetime.fromisoformat(req['timestamp'].split('.')[0])
        auditor = req.get('auditor', 'Não informado')
        
        for item in req['model_output']['items']:
            item_data = {
                'requisicao': req_id,
                'data': timestamp,
                'auditor': auditor,
                'descricao': item['description'],
                'codigo': item['Código correspondente ao item'],
                'decisao_jair': 'AUTORIZADO' if 'AUTORIZADO' in item.get('Situação', '').upper() else 'NEGADO',
                'decisao_auditor': 'AUTORIZADO' if item.get('auditor', {}).get('authorized_item', False) else 'NEGADO',
                'avaliacao_qualidade': 'BOA' if item.get('auditor', {}).get('quality_rating', False) else 'RUIM',
                'tem_avaliacao': 'auditor' in item and 'authorized_item' in item['auditor']
            }
            items_data.append(item_data)
            
    return pd.DataFrame(items_data)

# Carregar dados
st.title("📊 Resultados")

with st.spinner("Carregando dados para análise..."):
    requisitions = load_all_requisitions()
    if not requisitions:
        st.warning("Nenhuma requisição encontrada para análise.")
        st.stop()
    
    df = extract_items_data(requisitions)
    if df.empty:
        st.warning("Nenhum item encontrado para análise.")
        st.stop()

# Dashboard
st.header("Visão Geral")

# Métricas principais
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total de Requisições", len(requisitions))
with col2:
    st.metric("Total de Itens", len(df))
with col3:
    st.metric("Itens Avaliados", df['tem_avaliacao'].sum())
with col4:
    concordancia = (df[df['tem_avaliacao']]['decisao_jair'] == df[df['tem_avaliacao']]['decisao_auditor']).mean()
    st.metric("Taxa de Concordância", f"{concordancia:.1%}")

# Gráficos
st.subheader("Análise Detalhada")

# Linha 1 de gráficos
col1, col2 = st.columns(2)

with col1:
    # Comparação de decisões Jair vs Auditor
    df_comp = df[df['tem_avaliacao']].groupby(['decisao_jair', 'decisao_auditor']).size().reset_index(name='count')
    fig_comp = px.bar(df_comp, 
                     x='decisao_jair', 
                     y='count', 
                     color='decisao_auditor',
                     title='Comparação de Decisões: Jair vs Auditor',
                     labels={'decisao_jair': 'Decisão do Jair',
                            'decisao_auditor': 'Decisão do Auditor',
                            'count': 'Quantidade de Itens'})
    st.plotly_chart(fig_comp, use_container_width=True)

with col2:
    # Qualidade das respostas ao longo do tempo
    df_quality = df[df['tem_avaliacao']].groupby(['data', 'avaliacao_qualidade']).size().reset_index(name='count')
    fig_quality = px.line(df_quality, 
                         x='data', 
                         y='count', 
                         color='avaliacao_qualidade',
                         title='Qualidade das Respostas ao Longo do Tempo',
                         labels={'data': 'Data',
                                'avaliacao_qualidade': 'Avaliação de Qualidade',
                                'count': 'Quantidade de Itens'})
    st.plotly_chart(fig_quality, use_container_width=True)

# Linha 2 de gráficos
col1, col2 = st.columns(2)

with col1:
    # Matriz de confusão
    confusion_matrix = pd.crosstab(df[df['tem_avaliacao']]['decisao_jair'], 
                                 df[df['tem_avaliacao']]['decisao_auditor'],
                                 normalize='index')
    
    fig_matrix = px.imshow(confusion_matrix,
                          title='Matriz de Confusão Normalizada',
                          labels=dict(x='Decisão do Auditor', y='Decisão do Jair'),
                          color_continuous_scale='RdYlBu')
    st.plotly_chart(fig_matrix, use_container_width=True)

with col2:
    # Top 10 procedimentos mais frequentes
    top_procedures = df.groupby('descricao').size().sort_values(ascending=False).head(10)
    fig_top = px.bar(top_procedures,
                    title='Top 10 Procedimentos Mais Frequentes',
                    labels={'index': 'Procedimento', 'value': 'Quantidade'})
    fig_top.update_layout(showlegend=False)
    st.plotly_chart(fig_top, use_container_width=True)

# Análise por Auditor
st.subheader("Análise por Auditor")

# Métricas por auditor
df_auditor = df[df['tem_avaliacao']].groupby('auditor').agg({
    'requisicao': 'count',
    'tem_avaliacao': 'sum',
}).reset_index()

df_auditor['taxa_concordancia'] = df[df['tem_avaliacao']].groupby('auditor').apply(
    lambda x: (x['decisao_jair'] == x['decisao_auditor']).mean()
).values

fig_auditor = go.Figure(data=[
    go.Bar(name='Itens Avaliados', x=df_auditor['auditor'], y=df_auditor['tem_avaliacao']),
    go.Scatter(name='Taxa de Concordância', x=df_auditor['auditor'], y=df_auditor['taxa_concordancia'],
              yaxis='y2', mode='lines+markers')
])

fig_auditor.update_layout(
    title='Métricas por Auditor',
    yaxis=dict(title='Quantidade de Itens'),
    yaxis2=dict(title='Taxa de Concordância', overlaying='y', side='right', tickformat=',.0%'),
    barmode='group'
)

st.plotly_chart(fig_auditor, use_container_width=True)

# Filtros e análise detalhada
st.subheader("Análise Detalhada")

col1, col2 = st.columns(2)

with col1:
    selected_period = st.date_input(
        "Período de Análise",
        [df['data'].min().date(), df['data'].max().date()]
    )

with col2:
    selected_auditor = st.multiselect(
        "Filtrar por Auditor",
        options=df['auditor'].unique(),
        default=df['auditor'].unique()
    )

# Aplicar filtros
mask = (
    (df['data'].dt.date >= selected_period[0]) &
    (df['data'].dt.date <= selected_period[1]) &
    (df['auditor'].isin(selected_auditor))
)

filtered_df = df[mask]

# Exibir dados filtrados
if not filtered_df.empty:
    st.dataframe(
        filtered_df[['requisicao', 'data', 'auditor', 'descricao', 'decisao_jair', 'decisao_auditor', 'avaliacao_qualidade']]
        .sort_values('data', ascending=False),
        use_container_width=True
    ) 