"""Configuration settings for the model training and inference pipeline."""
from typing import List, Dict, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Main settings class."""
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='allow'  # Permite campos extras do .env
    )
    
    # API Keys
    openai_api_key: str = Field(default="")
    mistral_api_key: str = Field(default="")
    
    # Paths
    data_path: str = Field(default="./data/embeddings_05_09_2024")
    requisicoes_adress_or_path: str = Field(default="./data/Evah")
    
    # Service Configuration
    judge_model: str = Field(default="GPT-4o-mini")
    feedback_port: int = Field(default=80)
    feedback_adress: Optional[str] = Field(default="")
    requisicoes_port: int = Field(default=80)
    
    # Data paths
    path_requisicao: str = Field(
        default='data/Evah/OMNI_DADOS_REQUISICAO.csv',
        description="Path to requisition data file"
    )
    path_itens: str = Field(
        default='data/Evah/OMNI_DADOS_REQUISICAO_ITEM.csv',
        description="Path to items data file"
    )
    path_itens_nome: str = Field(
        default='data/Evah/OMNI_DADOS_ITEM.csv',
        description="Path to item names data file"
    )
    path_beneficiario: str = Field(
        default='data/Evah/OMNI_DADOS_BENEFICIARIO.csv',
        description="Path to beneficiary data file"
    )
    path_prestador: str = Field(
        default='data/Evah/OMNI_DADOS_PRESTADOR.csv',
        description="Path to provider data file"
    )
    
    # Model paths
    pipeline_path: str = Field(
        default='model/pipeline_transformers.joblib',
        description="Path to save/load pipeline"
    )
    model_path: str = Field(
        default='model/xgboost_model.json',
        description="Path to save/load model"
    )
    
    # MLflow settings
    mlflow_experiment_name: str = Field(
        default='Americas Health All Data',
        description="MLflow experiment name"
    )
    mlflow_dataset_name: str = Field(
        default='df_onehot_encoder_drop_agosto',
        description="Dataset name for tracking"
    )
    mlflow_track_uri: str = Field(
        default='',
        description="MLflow tracking URI"
    )
    
    # Status configurations
    status_remover: List[str] = Field(
        default=[
            'Liberado pelo sistema', 
            'Em desacordo com os critï¿½rios tï¿½cnicos', 
            'Em anï¿½lise'
        ],
        description="Status values to remove from dataset"
    )
    status_map: Dict[str, str] = Field(
        default={
            'Liberado pelo usuï¿½rio': 'Liberado pelo usuário',
            'Nï¿½o liberado': 'Não liberado'
        },
        description="Mapping for status text normalization"
    )
    status_num_map: Dict[str, int] = Field(
        default={
            'Liberado pelo usuário': 1,
            'Não liberado': 0
        },
        description="Mapping from status text to numeric values"
    )
    
    # Feature configurations
    colunas_para_remover: List[str] = Field(
        default=[
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
        ],
        description="Columns to remove during preprocessing"
    )
    colunas_para_codificar: List[str] = Field(
        default=[
            'DS_TIPO_GUIA', 
            'DS_CARATER_ATENDIMENTO', 
            'DS_TIPO_INTERNACAO', 
            'DS_CBO_PROFISSIONAL', 
            'DS_REGIME_INTERNACAO', 
            'DS_TIPO_SADT', 
            'DS_TIPO_CONSULTA', 
            'DS_TIPO_ITEM', 
            'DS_CLASSIFICACAO_1'
        ],
        description="Columns to one-hot encode"
    )

# Create settings instance
settings = Settings()