"""Pipeline definition for model training and inference."""
from sklearn.pipeline import Pipeline
from . import config
from .transformers import (
    DateDifferenceTransformer,
    DropColumnsTransformer,
    BinaryNumericTransformer,
    Word2VecTransformer,
    StatusItemMapper,
    OneHotEncodingTransformer
)

def create_pipeline():
    """Create and return the complete preprocessing pipeline."""
    print("Creating preprocessing pipeline...")
    pipeline = Pipeline([
        ('date_diff', DateDifferenceTransformer()),
        ('drop_cols', DropColumnsTransformer(config.settings.colunas_para_remover)),
        ('binary_numeric', BinaryNumericTransformer()),
        ('word2vec', Word2VecTransformer(text_col='DS_ITEM')),
        ('status_map', StatusItemMapper(config.settings.status_num_map)),
        ('one_hot', OneHotEncodingTransformer(config.settings.colunas_para_codificar)),
        ('drop_ds_item', DropColumnsTransformer(['DS_ITEM'])),
    ], verbose=True)  # Adiciona verbose para melhor diagnóstico
    
    return pipeline 