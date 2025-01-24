"""Model training with MLflow tracking."""
import mlflow
import mlflow.xgboost
import mlflow.models
from mlflow.models.signature import infer_signature
import joblib
import numpy as np
import pandas as pd
import os
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.utils.class_weight import compute_sample_weight

from . import config
from .data_loader import preparar_dados_treinamento
from .pipeline import create_pipeline

# Desabilita o logging de variáveis de ambiente no MLflow
os.environ['MLFLOW_RECORD_ENV_VARS_IN_MODEL_LOGGING'] = 'false'

def prepare_model_input(X):
    """Prepara o input para o modelo, garantindo tipos corretos."""
    X = X.copy()
    
    # Converte todas as colunas numéricas para float64
    numeric_cols = X.select_dtypes(include=['int', 'float']).columns
    X[numeric_cols] = X[numeric_cols].astype(np.float64)
    
    return X

def train_model(ano=2024, mes=8):
    """Train the model and track with MLflow."""
    # Set up MLflow
    mlflow.set_tracking_uri("http://3.236.36.170:5000")
    mlflow.set_experiment(config.settings.mlflow_experiment_name)

    # Prepare data
    X_train, X_test = preparar_dados_treinamento(ano=ano, mes=mes)
    
    # Create and fit pipeline
    pipeline = create_pipeline()
    
    # Fit pipeline on training data
    print("Fitting pipeline on training data...")
    X_train_transformed = pipeline.fit_transform(X_train)
    
    # Transform test data using fitted pipeline
    print("Transforming test data...")
    X_test_transformed = pipeline.transform(X_test)
    
    # Extract target variable after transformation
    y_train = X_train_transformed['DS_STATUS_ITEM']
    y_test = X_test_transformed['DS_STATUS_ITEM']
    
    # Remove target variable from features
    X_train_transformed = X_train_transformed.drop(columns=['DS_STATUS_ITEM'])
    X_test_transformed = X_test_transformed.drop(columns=['DS_STATUS_ITEM'])
    
    # Prepara inputs garantindo tipos corretos
    X_train_transformed = prepare_model_input(X_train_transformed)
    X_test_transformed = prepare_model_input(X_test_transformed)
    
    # Save pipeline
    print("Saving pipeline...")
    joblib.dump(pipeline, config.settings.pipeline_path)
    
    with mlflow.start_run() as run:
        # Calculate sample weights
        sample_weights = compute_sample_weight(class_weight='balanced', y=y_train)
        
        # Train model
        print("Training XGBoost model...")
        model = XGBClassifier(
            random_state=42,
            n_jobs=-1,  # Usar todos os cores disponíveis
            enable_categorical=True  # Habilita suporte a variáveis categóricas
        )
        model.fit(X_train_transformed, y_train, sample_weight=sample_weights)
        
        # Make predictions
        print("Making predictions...")
        y_pred = model.predict(X_test_transformed)
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        accuracy_rounded = round(accuracy, 2)
        
        # Print detailed classification report
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        # Log metrics and model
        print("Logging to MLflow...")
        mlflow.log_metric('accuracy', accuracy_rounded)
        
        # Prepare model signature and input example
        print("Preparing model signature and input example...")
        input_example = X_train_transformed.iloc[:5].copy()
        
        # Fazer uma predição com o exemplo para inferir a assinatura
        example_pred = model.predict(input_example)
        
        # Inferir a assinatura do modelo usando os dados reais
        signature = infer_signature(
            model_input=input_example,
            model_output=example_pred
        )
        
        # Log model primeiro para obter o model_uri
        print("Logging model to MLflow...")
        # Salva o modelo em formato booster nativo do XGBoost
        model.get_booster().save_model(config.settings.model_path)
        
        # Log model usando mlflow.xgboost
        logged_model = mlflow.xgboost.log_model(
            xgb_model=model.get_booster(),  # Usa o booster nativo do XGBoost
            artifact_path='xgboost_model',
            signature=signature,
            input_example=input_example  # Usa o DataFrame diretamente como exemplo
        )
        
        # Log parâmetros adicionais
        mlflow.log_params({
            'dataset': config.settings.mlflow_dataset_name,
            'ano': ano,
            'mes': mes,
            'n_features': X_train_transformed.shape[1],
            'n_train_samples': X_train_transformed.shape[0],
            'n_test_samples': X_test_transformed.shape[0]
        })
        
        print(f"Model trained successfully. Accuracy: {accuracy:.2f}")
        return model, pipeline

if __name__ == '__main__':
    train_model() 