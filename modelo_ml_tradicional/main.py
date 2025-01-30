import pandas as pd
from sklearn.pipeline import Pipeline
from modelo_ml_tradicional.transformers import (
    DateDifferenceTransformer,
    DropColumnsTransformer,
    BinaryNumericTransformer,
    Word2VecTransformer,
    StatusItemMapper,
    OneHotEncodingTransformer
)

import mlflow
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score
from catboost import CatBoostClassifier
import mlflow.catboost
from sklearn.utils.class_weight import compute_sample_weight
import joblib



#mlflow.set_tracking_uri("http://44.211.164.41:5000")
mlflow.set_experiment('Americas Health All Data')

dataset_name = 'df_onehot_encoder_drop_agosto'


# =============================================================================
# Configurações
# =============================================================================
PATH_REQUISICAO = r'modelo_ml_tradicional/Evah/OMNI_DADOS_REQUISICAO.csv'
PATH_ITENS = r'modelo_ml_tradicional/Evah/OMNI_DADOS_REQUISICAO_ITEM.csv'
PATH_ITENS_NOME = r'modelo_ml_tradicional/Evah/OMNI_DADOS_ITEM.csv'
PATH_BENEFICIARIO = r'modelo_ml_tradicional/Evah/OMNI_DADOS_BENEFICIARIO.csv'
PATH_PRESTADOR = r'modelo_ml_tradicional/Evah/OMNI_DADOS_PRESTADOR.csv'

STATUS_ITEM_REMOVER = [
    'Liberado pelo sistema', 
    'Em desacordo com os critï¿½rios tï¿½cnicos', 
    'Em anï¿½lise'
]

MAP_STATUS_ITEM = {
    'Liberado pelo usuï¿½rio': 'Liberado pelo usuário',
    'Nï¿½o liberado': 'Não liberado'
}

STATUS_ITEM_NUM_MAP = {
    'Liberado pelo usuário': 1,
    'Não liberado': 0
}

COLUNAS_PARA_REMOVER = [
    'DS_STATUS_REQUISICAO', 
    'DT_ATUALIZACAO_y', 
    'ID_BENEFICIARIO', 
    'DT_REQUISICAO', 
    'DT_FIM_ANALISE', 
    'DT_ATUALIZACAO', 
    'CD_ITEM', 
    'ID_GUIA_PRINCIPAL', 
    'ID_ITEM', 
    'DS_TIPO_ACOMODACAO', 
    'DT_ENTRADA_HOSPITAL',
    'CD_UNIDADE_MEDIDA',
    'DS_CLASSIFICACAO_2',
    'DS_CLASSIFICACAO_3',
    'DS_CLASSIFICACAO_BI',
    'ID_PRESTADOR', 
    'ID_PROFISSIONAL', 
    'ID_TITULAR', 
    'ID_PLANO',
    'ID_ESTIPULANTE',
    'APOLICE',
    'DATA_INICIO_VIGENCIA',
    'CARENCIA',
    'NM_BENEFICIARIO',
    'NR_CPF',
    'PARENTESCO',
    'SEXO',
    'ESTADO_CIVIL',
    'EMAIL',
    'DDD_TELEFONE',
    'NR_TELEFONE'
]

COLUNAS_PARA_CODIFICAR = [
    'DS_TIPO_GUIA', 
    'DS_CARATER_ATENDIMENTO', 
    'DS_TIPO_INTERNACAO', 
    'DS_CBO_PROFISSIONAL', 
    'DS_REGIME_INTERNACAO', 
    'DS_TIPO_SADT', 
    'DS_TIPO_CONSULTA', 
    'DS_TIPO_ITEM', 
    'DS_CLASSIFICACAO_1'
]

# =============================================================================
# Funções Auxiliares
# =============================================================================
def carregar_dados():
    df_requisicao = pd.read_csv(PATH_REQUISICAO, encoding='latin1')
    df_itens = pd.read_csv(PATH_ITENS, encoding='latin1')
    df_itens_nome = pd.read_csv(PATH_ITENS_NOME, encoding='latin1')
    df_beneficiario = pd.read_csv(PATH_BENEFICIARIO, encoding='latin1')
    df_prestador = pd.read_csv(PATH_PRESTADOR, encoding='latin1')
    return df_requisicao, df_itens, df_itens_nome, df_beneficiario, df_prestador

def preparar_merged(df_requisicao, df_itens, df_beneficiario, df_itens_nome):
    df_filtrado = pd.merge(df_requisicao, df_beneficiario, on='ID_BENEFICIARIO', how='left')
    df_combinado = pd.merge(df_itens, df_filtrado, on='ID_REQUISICAO', how='left')
    # Remover linhas com DS_STATUS_REQUISICAO nulo
    df_combinado = df_combinado.dropna(subset=['DS_STATUS_REQUISICAO'])
    # Remover itens com status não desejados
    df_combinado = df_combinado[~df_combinado['DS_STATUS_ITEM'].isin(STATUS_ITEM_REMOVER)]
    # Ajustar acentuação
    df_combinado['DS_STATUS_ITEM'] = df_combinado['DS_STATUS_ITEM'].replace(MAP_STATUS_ITEM)
    # Mesclar com nomes de itens
    df_merged = pd.merge(df_combinado, df_itens_nome, on='ID_ITEM', how='left')
    return df_merged

def filtrar_dados_por_mes(df, ano=2024, mes=8):
    df['DT_ATUALIZACAO_x'] = pd.to_datetime(df['DT_ATUALIZACAO_x'], format='%d/%m/%y', errors='coerce')
    data_inicio = pd.to_datetime(f'{ano}-{mes:02d}-01')
    data_fim = (data_inicio + pd.offsets.MonthEnd(1))

    df_filtrado_mes = df[(df['DT_ATUALIZACAO_x'] >= data_inicio) & (df['DT_ATUALIZACAO_x'] <= data_fim)]
    df_excluido_mes = df[~df['DT_ATUALIZACAO_x'].between(data_inicio, data_fim)]
    return df_filtrado_mes, df_excluido_mes

def main(ano=2024, mes=8):
    # Carrega dados
    df_requisicao, df_itens, df_itens_nome, df_beneficiario, df_prestador = carregar_dados()
    
    # Merge inicial
    df_merged = preparar_merged(df_requisicao, df_itens, df_beneficiario, df_itens_nome)
    
    # Cria a pipeline
    pipeline = Pipeline([
        ('date_diff', DateDifferenceTransformer()),
        ('drop_cols', DropColumnsTransformer(COLUNAS_PARA_REMOVER)),
        ('binary_numeric', BinaryNumericTransformer()),
        ('word2vec', Word2VecTransformer(text_col='DS_ITEM')),
        ('status_map', StatusItemMapper(STATUS_ITEM_NUM_MAP)),
        ('one_hot', OneHotEncodingTransformer(COLUNAS_PARA_CODIFICAR)),
        ('drop_ds_item', DropColumnsTransformer(['DS_ITEM'])),
    ])
    
    # Aplica a pipeline
    df_final = pipeline.fit_transform(df_merged)
    
    # Salva a pipeline treinada
    joblib.dump(pipeline, 'modelo_ml_tradicional/pipeline_transformers.joblib')
    
    # Remove valores nulos (se houver)
    df_final = df_final.dropna()
    
    # Filtra dados para o mês/ano desejado
    df_filtrado_mes, df_excluido_mes = filtrar_dados_por_mes(df_final, ano=ano, mes=mes)
    
    # Prepara X e y
    # Remove colunas de identificação e data do conjunto final
    df_filtrado_mes = df_filtrado_mes.drop(columns=['ID_REQUISICAO_ITEM', 'DT_ATUALIZACAO_x', 'ID_REQUISICAO'], errors='ignore')
    df_excluido_mes = df_excluido_mes.drop(columns=['ID_REQUISICAO_ITEM', 'DT_ATUALIZACAO_x', 'ID_REQUISICAO'], errors='ignore')
    
    X_train = df_excluido_mes.drop(columns=['DS_STATUS_ITEM'])
    y_train = df_excluido_mes['DS_STATUS_ITEM']
    
    X_test = df_filtrado_mes.drop(columns=['DS_STATUS_ITEM'])
    y_test = df_filtrado_mes['DS_STATUS_ITEM']
    
    return X_train, y_train, X_test, y_test

if __name__ == '__main__':
    X_train, y_train, X_test, y_test = main(ano=2024, mes=8)
    print("X_train shape:", X_train.shape)
    print("y_train shape:", y_train.shape)
    print("X_test shape:", X_test.shape)
    print("y_test shape:", y_test.shape)



    # Começando o MLflow para monitorar o experimento
    with mlflow.start_run():

        # Calculando sample weights com base na distribuição da variável target
        sample_weights = compute_sample_weight(class_weight='balanced', y=y_train)

        # Treinando o modelo XGBoost com sample weights
        model = XGBClassifier(random_state=42)
        model.fit(X_train, y_train, sample_weight=sample_weights)

        # Salvando o modelo treinado localmente também
        joblib.dump(model, 'modelo_ml_tradicional/xgboost_model.joblib')

        # Fazendo previsões
        y_pred = model.predict(X_test)

        # Calculando a acurácia
        accuracy = accuracy_score(y_test, y_pred)
        accuracy_rounded = round(accuracy, 2)

        # Registrando a acurácia como métrica
        mlflow.log_metric('accuracy', accuracy_rounded)
        mlflow.xgboost.log_model(model, 'xgboost_model')
        mlflow.log_param('dataset', dataset_name)

        print(f"Accuracy: {accuracy:.2f}")
