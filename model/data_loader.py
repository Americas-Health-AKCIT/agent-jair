"""Data loading and preprocessing functions."""
import pandas as pd
from . import config

def carregar_dados():
    """Load raw data from CSV files."""
    df_requisicao = pd.read_csv(
        config.settings.path_requisicao, 
        encoding='latin1',
        low_memory=False  # Evita warning de tipos mistos
    )
    print(df_requisicao.head())
    df_itens = pd.read_csv(
        config.settings.path_itens, 
        encoding='latin1',
        low_memory=False
    )
    df_itens_nome = pd.read_csv(
        config.settings.path_itens_nome, 
        encoding='latin1',
        low_memory=False
    )
    print(df_itens_nome.head())
    df_beneficiario = pd.read_csv(
        config.settings.path_beneficiario, 
        encoding='latin1',
        low_memory=False
    )
    print(df_beneficiario.head())
    df_prestador = pd.read_csv(
        config.settings.path_prestador, 
        encoding='latin1',
        low_memory=False
    )
    return df_requisicao, df_itens, df_itens_nome, df_beneficiario, df_prestador

def preparar_merged(df_requisicao, df_itens, df_beneficiario, df_itens_nome):
    """Merge and preprocess dataframes."""
    df_filtrado = pd.merge(df_requisicao, df_beneficiario, on='ID_BENEFICIARIO', how='left')
    df_combinado = pd.merge(df_itens, df_filtrado, on='ID_REQUISICAO', how='left')
    
    # Remove rows with null DS_STATUS_REQUISICAO
    df_combinado = df_combinado.dropna(subset=['DS_STATUS_REQUISICAO'])
    
    # Remove items with unwanted status
    df_combinado = df_combinado[~df_combinado['DS_STATUS_ITEM'].isin(config.settings.status_remover)]
    
    # Fix accents in status
    df_combinado['DS_STATUS_ITEM'] = df_combinado['DS_STATUS_ITEM'].replace(config.settings.status_map)
    
    # Merge with item names
    df_merged = pd.merge(df_combinado, df_itens_nome, on='ID_ITEM', how='left')
    return df_merged

def filtrar_dados_por_mes(df, ano=2024, mes=8):
    """Filter data for a specific month and year."""
    df['DT_ATUALIZACAO_x'] = pd.to_datetime(df['DT_ATUALIZACAO_x'], format='%d/%m/%y', errors='coerce')
    data_inicio = pd.to_datetime(f'{ano}-{mes:02d}-01')
    data_fim = (data_inicio + pd.offsets.MonthEnd(1))

    df_filtrado_mes = df[(df['DT_ATUALIZACAO_x'] >= data_inicio) & (df['DT_ATUALIZACAO_x'] <= data_fim)]
    df_excluido_mes = df[~df['DT_ATUALIZACAO_x'].between(data_inicio, data_fim)]
    return df_filtrado_mes, df_excluido_mes

def preparar_dados_treinamento(ano=2024, mes=8):
    """Prepare data for training, including all preprocessing steps."""
    # Load data
    df_requisicao, df_itens, df_itens_nome, df_beneficiario, df_prestador = carregar_dados()
    
    # Merge data
    df_merged = preparar_merged(df_requisicao, df_itens, df_beneficiario, df_itens_nome)
    
    # Filter by month
    df_filtrado_mes, df_excluido_mes = filtrar_dados_por_mes(df_merged, ano=ano, mes=mes)

    df_excluido_mes.to_csv('data/Evah/df_excluido_mes.csv', index=False)
    
    # Remove only ID and date columns
    colunas_para_remover = ['ID_REQUISICAO_ITEM', 'DT_ATUALIZACAO_x', 'ID_REQUISICAO']
    
    # Prepare train data (keeping DS_STATUS_ITEM for pipeline)
    X_train = df_excluido_mes.drop(columns=colunas_para_remover)
    
    # Prepare test data (keeping DS_STATUS_ITEM for pipeline)
    X_test = df_filtrado_mes.drop(columns=colunas_para_remover)
    
    return X_train, X_test 