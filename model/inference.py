"""Model inference using MLflow."""

import mlflow
import mlflow.xgboost
import pandas as pd
import joblib
import numpy as np
from config import config
from .data_loader import carregar_dados, preparar_merged
from .train import prepare_model_input
from utils.get_requisition_details import get_austa_api_token
import requests
from config.config import settings


def load_model(model_name="jair-autorizacoes"):
    """
    Carrega o modelo do MLflow e o pipeline de pré-processamento.

    Args:
        run_id: ID do experimento MLflow para carregar o modelo

    Returns:
        tuple: (modelo carregado, pipeline carregado)
    """
    print("Loading model...")
    print(config.settings.mlflow_track_uri)
    mlflow.set_tracking_uri(config.settings.mlflow_track_uri)

    # Carrega o modelo do MLflow
    model_uri = f"models:/{model_name}@production"
    print(f"Loading model from {model_uri}...")
    model = mlflow.pyfunc.load_model(model_uri)

    # Carrega o pipeline de pré-processamento
    print(f"Loading pipeline from {config.settings.pipeline_path}...")
    pipeline = joblib.load(config.settings.pipeline_path)

    return model, pipeline


def prepare_prediction_input(X):
    """
    Prepara o input para predição, garantindo tipos corretos.

    Args:
        X: DataFrame com os dados para predição

    Returns:
        DataFrame: Dados preparados para predição
    """
    X = X.copy()

    # Converte todas as colunas numéricas para float64
    numeric_cols = X.select_dtypes(include=["int", "float", "int64", "float64"]).columns
    for col in numeric_cols:
        X[col] = X[col].astype(np.float64)

    return X


def fazer_predicao_por_id(id_requisicao):
    """Make predictions for a specific requisition ID.

    Args:
        id_requisicao: ID of the requisition to predict

    Returns:
        dict: Dictionary containing predictions and probabilities
    """
    API_TOKEN = get_austa_api_token()
    base_url = settings.austa_api_base_url

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }
    params = {"request_id": id_requisicao}

    dados_requisicao = None

    try:
        response = requests.get(
            f"{base_url}/auditor/requests/", headers=headers, params=params
        )
        response.raise_for_status()  # Lança exceção se o status não for 200
        dados_requisicao = response.json()

        dados_requisicao = dados_requisicao[0]
        df_requisicao = pd.DataFrame([dados_requisicao])

        # Drop unnecessary columns from df_requisicao
        df_requisicao = df_requisicao.drop(
            columns=[
                "DS_ITEM",
                "DS_TIPO_ITEM",
                "DS_CLASSIFICACAO_1",
                "ID_REQUISICAO_ITEM",
                "NM_PRESTADOR",
            ],
            errors="ignore",
        )

        response_item = requests.get(
            f"{base_url}/auditor/request-item/", headers=headers, params=params
        )
        response_item.raise_for_status()
        dados_item = response_item.json()

        df_itens = pd.DataFrame(dados_item)

        df_itens = df_itens.drop(
            columns=["QT_SOLICITADA", "QT_LIBERADA", "QT_EXECUTADA", "VL_LIBERADO"],
            errors="ignore",
        )

        df_merged = df_requisicao.merge(df_itens, on="ID_REQUISICAO")

        print(df_merged.columns)

        if df_merged.empty:
            raise ValueError("No request item data found for prediction")

        colunas_a_mais = config.settings.colunas_para_remover

        # Add missing columns with empty values
        for coluna in colunas_a_mais:
            if coluna not in df_merged.columns:
                df_merged[coluna] = ""

        # Ensure all required columns exist with empty values if missing
        required_columns = [
            "ID_REQUISICAO_ITEM",
            "DT_ATUALIZACAO_x",
            "ID_REQUISICAO",
            "ID_ITEM",
            "DS_STATUS_ITEM",
            "DT_ATUALIZACAO_y",
            "ID_BENEFICIARIO",
            "ID_PRESTADOR",
            "ID_PROFISSIONAL",
            "DS_STATUS_REQUISICAO",
            "DT_REQUISICAO",
            "DT_FIM_ANALISE",
            "DS_CBO_PROFISSIONAL",
            "DS_TIPO_GUIA",
            "DS_CARATER_ATENDIMENTO",
            "DS_TIPO_INTERNACAO",
            "DS_REGIME_INTERNACAO",
            "DS_TIPO_ACOMODACAO",
            "DS_TIPO_SADT",
            "DS_TIPO_CONSULTA",
            "ID_GUIA_PRINCIPAL",
            "DT_ENTRADA_HOSPITAL",
            "ID_TITULAR",
            "ID_PLANO",
            "ID_ESTIPULANTE",
            "APOLICE",
            "DATA_INICIO_VIGENCIA",
            "DATA_CANCELAMENTO",
            "CARENCIA",
            "DATA_FIM_CARENCIA",
            "NM_BENEFICIARIO",
            "DATA_NASCIMENTO",
            "NR_CPF",
            "PARENTESCO",
            "SEXO",
            "ESTADO_CIVIL",
            "TITULARIDADE",
            "EMAIL",
            "DDD_TELEFONE",
            "NR_TELEFONE",
            "DT_ATUALIZACAO",
            "DS_TIPO_ITEM",
            "CD_ITEM",
            "DS_ITEM",
            "CD_UNIDADE_MEDIDA",
            "DS_CLASSIFICACAO_1",
            "DS_CLASSIFICACAO_2",
            "DS_CLASSIFICACAO_3",
            "DS_CLASSIFICACAO_BI",
        ]

        for col in required_columns:
            if col not in df_merged.columns:
                df_merged[col] = None

        # Reorder columns
        df_merged = df_merged[required_columns]

    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err}"

    if df_merged.empty:
        print("\nDebug - Checking intermediate joins:")
        df_itens_filtered = df_itens[df_itens["ID_REQUISICAO"] == id_requisicao]
        print(f"Items found for requisition: {df_itens_filtered.shape[0]}")
        if not df_itens_filtered.empty:
            print("Item IDs found:", df_itens_filtered["ID_REQUISICAO_ITEM"].tolist())
            itens_encontrados = df_itens[
                df_itens["ID_REQUISICAO_ITEM"].isin(
                    df_itens_filtered["ID_REQUISICAO_ITEM"]
                )
            ]
            print(f"Items found in df_itens_nome: {itens_encontrados.shape[0]}")
        raise ValueError("After merge, no data found for prediction")

    # Store IDs and descriptions before transformation
    ids_itens = df_merged["ID_REQUISICAO_ITEM"].astype(int).tolist()
    descricoes_itens = df_merged["DS_ITEM"].tolist()

    # Load model and pipeline
    model, pipeline = load_model()

    print(df_merged.columns)

    # Convert DATA_NASCIMENTO to numeric before transformation
    df_merged["DATA_NASCIMENTO"] = pd.to_numeric(
        df_merged["DATA_NASCIMENTO"].str[:4], errors="coerce"
    )

    # Apply transformations
    X_transform = pipeline.transform(df_merged)
    print(f"\nDebug - After transformation:")
    print(f"X_transform shape: {X_transform.shape}")

    # Remove ID and date columns
    colunas_para_remover = [
        "ID_REQUISICAO_ITEM",
        "DT_ATUALIZACAO_x",
        "ID_REQUISICAO",
        "DS_STATUS_ITEM",
    ]
    colunas_existentes = [
        col for col in colunas_para_remover if col in X_transform.columns
    ]
    X_transform = X_transform.drop(columns=colunas_existentes)

    print(f"\nDebug - After removing ID columns:")
    print(f"X_transform final shape: {X_transform.shape}")

    if X_transform.empty:
        raise ValueError("Transformed data is empty")

    # Prepara input garantindo tipos corretos
    X_transform = prepare_prediction_input(X_transform)

    # Make predictions
    print("Making predictions...")
    if hasattr(model, "predict_proba"):
        # Use predict_proba if available to get probabilities
        probabilities = model.predict_proba(X_transform)
        # Assume the second column is the probability of class 1
        raw_predictions = probabilities[:, 1]
    else:
        # Fallback to predict if predict_proba is not available
        raw_predictions = model.predict(X_transform)

    # Debug: Print raw predictions
    print("RAW Predictions:", raw_predictions)

    # Converte as predições para o formato correto (0 ou 1) usando um limiar
    # Considera 1 se a probabilidade for maior ou igual a 0.5, caso contrário 0
    predicoes = np.array([1 if pred >= 0.5 else 0 for pred in raw_predictions])

    # Map results
    mapa_status_reverso = {0: "Recusado", 1: "Aprovado"}

    # Prepare detailed results
    resultados_detalhados = []
    resultados_bool_dict = {}

    for i in range(len(predicoes)):
        pred = predicoes[i]
        resultado = {
            "id_requisicao": id_requisicao,
            "id_requisicao_item": ids_itens[i],
            "descricao_item": descricoes_itens[i],
            "predicao": mapa_status_reverso[pred],
            "probabilidade_recusado": 1.0 if pred == 0 else 0.0,
            "probabilidade_aprovado": 1.0 if pred == 1 else 0.0,
        }
        resultados_detalhados.append(resultado)
        resultados_bool_dict[ids_itens[i]] = pred == 1

    # Return overall result
    return {
        "id_requisicao": id_requisicao,
        "resultados_por_item": resultados_detalhados,
        "resultados_bool_dict": resultados_bool_dict,
        "total_itens": len(resultados_detalhados),
        "itens_aprovados": sum(
            1 for r in resultados_detalhados if r["predicao"] == "Aprovado"
        ),
        "itens_recusados": sum(
            1 for r in resultados_detalhados if r["predicao"] == "Recusado"
        ),
    }


if __name__ == "__main__":
    # Test prediction for a specific requisition ID
    id_requisicao = 42089629
    result = fazer_predicao_por_id(id_requisicao)
    print(result)
