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

# Análise por Item
st.subheader("Análise por Item")

# Agrupar dados por item
df_items = df[df['tem_avaliacao']].groupby(['descricao', 'codigo']).agg({
    'requisicao': 'count',
    'tem_avaliacao': 'sum'
}).reset_index()

# Calcular métricas por item
df_items['taxa_concordancia'] = df[df['tem_avaliacao']].groupby(['descricao', 'codigo']).apply(
    lambda x: (x['decisao_jair'] == x['decisao_auditor']).mean()
).values

df_items['taxa_aprovacao_jair'] = df[df['tem_avaliacao']].groupby(['descricao', 'codigo']).apply(
    lambda x: (x['decisao_jair'] == 'AUTORIZADO').mean()
).values

df_items['taxa_aprovacao_auditor'] = df[df['tem_avaliacao']].groupby(['descricao', 'codigo']).apply(
    lambda x: (x['decisao_auditor'] == 'AUTORIZADO').mean()
).values

df_items['avaliacao_qualidade'] = df[df['tem_avaliacao']].groupby(['descricao', 'codigo']).apply(
    lambda x: (x['avaliacao_qualidade'] == 'BOA').mean()
).values

# Ordenar por quantidade de avaliações
df_items = df_items.sort_values('requisicao', ascending=False)

# Criar tabs para diferentes visualizações
tab1, tab2 = st.tabs(["📊 Gráficos", "📋 Tabela Detalhada"])

with tab1:
    # Gráfico 1: Taxa de Concordância e Qualidade por Item
    fig_item_metrics = go.Figure()
    
    fig_item_metrics.add_trace(go.Bar(
        name='Taxa de Concordância',
        x=df_items['descricao'],
        y=df_items['taxa_concordancia'],
        marker_color='#2ecc71'
    ))
    
    fig_item_metrics.add_trace(go.Bar(
        name='Avaliação de Qualidade',
        x=df_items['descricao'],
        y=df_items['avaliacao_qualidade'],
        marker_color='#3498db'
    ))
    
    fig_item_metrics.update_layout(
        title='Taxa de Concordância e Qualidade por Item',
        barmode='group',
        xaxis_tickangle=-45,
        yaxis_tickformat=',.0%',
        height=500
    )
    
    st.plotly_chart(fig_item_metrics, use_container_width=True)
    
    # Gráfico 2: Comparação de Taxas de Aprovação
    fig_approval = go.Figure()
    
    fig_approval.add_trace(go.Bar(
        name='Taxa de Aprovação (Jair)',
        x=df_items['descricao'],
        y=df_items['taxa_aprovacao_jair'],
        marker_color='#e74c3c'
    ))
    
    fig_approval.add_trace(go.Bar(
        name='Taxa de Aprovação (Auditor)',
        x=df_items['descricao'],
        y=df_items['taxa_aprovacao_auditor'],
        marker_color='#9b59b6'
    ))
    
    fig_approval.update_layout(
        title='Comparação de Taxas de Aprovação por Item',
        barmode='group',
        xaxis_tickangle=-45,
        yaxis_tickformat=',.0%',
        height=500
    )
    
    st.plotly_chart(fig_approval, use_container_width=True)

with tab2:
    # Formatar colunas para exibição
    df_display = df_items.copy()
    df_display['Taxa de Concordância'] = df_display['taxa_concordancia'].map('{:.1%}'.format)
    df_display['Taxa de Aprovação (Jair)'] = df_display['taxa_aprovacao_jair'].map('{:.1%}'.format)
    df_display['Taxa de Aprovação (Auditor)'] = df_display['taxa_aprovacao_auditor'].map('{:.1%}'.format)
    df_display['Avaliação de Qualidade'] = df_display['avaliacao_qualidade'].map('{:.1%}'.format)
    df_display['Quantidade de Avaliações'] = df_display['requisicao']
    
    # Renomear colunas
    df_display = df_display.rename(columns={
        'descricao': 'Procedimento',
        'codigo': 'Código'
    })
    
    # Selecionar e ordenar colunas para exibição
    cols_to_display = [
        'Procedimento',
        'Código',
        'Quantidade de Avaliações',
        'Taxa de Concordância',
        'Taxa de Aprovação (Jair)',
        'Taxa de Aprovação (Auditor)',
        'Avaliação de Qualidade'
    ]
    
    st.dataframe(
        df_display[cols_to_display],
        use_container_width=True,
        hide_index=True
    )

# Adicionar filtro por item específico
st.subheader("Análise Individual de Item")

selected_item = st.selectbox(
    "Selecione um item para análise detalhada:",
    options=df_items['descricao'].unique()
)

if selected_item:
    item_data = df[df['descricao'] == selected_item]
    item_data = item_data[item_data['tem_avaliacao']]
    
    if not item_data.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_avaliacoes = len(item_data)
            st.metric("Total de Avaliações", total_avaliacoes)
            
        with col2:
            concordancia = (item_data['decisao_jair'] == item_data['decisao_auditor']).mean()
            st.metric("Taxa de Concordância", f"{concordancia:.1%}")
            
        with col3:
            qualidade = (item_data['avaliacao_qualidade'] == 'BOA').mean()
            st.metric("Taxa de Qualidade", f"{qualidade:.1%}")
            
        with col4:
            aprovacao_diff = (
                (item_data['decisao_jair'] == 'AUTORIZADO').mean() -
                (item_data['decisao_auditor'] == 'AUTORIZADO').mean()
            )
            st.metric(
                "Diferença na Taxa de Aprovação",
                f"{abs(aprovacao_diff):.1%}",
                delta=f"{'Maior' if aprovacao_diff > 0 else 'Menor'} que o Auditor"
            )
        
        # Matriz de confusão para o item específico
        confusion_matrix = pd.crosstab(
            item_data['decisao_jair'],
            item_data['decisao_auditor'],
            normalize='index'
        )
        
        fig_matrix = px.imshow(
            confusion_matrix,
            title=f'Matriz de Confusão - {selected_item}',
            labels=dict(x='Decisão do Auditor', y='Decisão do Jair'),
            color_continuous_scale='RdYlBu'
        )
        
        st.plotly_chart(fig_matrix, use_container_width=True)
        
        # Histórico de decisões ao longo do tempo
        fig_history = go.Figure()
        
        fig_history.add_trace(go.Scatter(
            x=item_data['data'],
            y=item_data['decisao_jair'].map({'AUTORIZADO': 1, 'NEGADO': 0}),
            name='Decisão do Jair',
            mode='markers',
            marker=dict(size=10)
        ))
        
        fig_history.add_trace(go.Scatter(
            x=item_data['data'],
            y=item_data['decisao_auditor'].map({'AUTORIZADO': 1, 'NEGADO': 0}),
            name='Decisão do Auditor',
            mode='markers',
            marker=dict(size=10)
        ))
        
        fig_history.update_layout(
            title='Histórico de Decisões ao Longo do Tempo',
            yaxis=dict(
                ticktext=['NEGADO', 'AUTORIZADO'],
                tickvals=[0, 1],
                title='Decisão'
            ),
            xaxis_title='Data',
            height=400
        )
        
        st.plotly_chart(fig_history, use_container_width=True) 