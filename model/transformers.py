import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from gensim.models import Word2Vec
from sklearn.preprocessing import OneHotEncoder


class DateDifferenceTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, start_date_col='DT_REQUISICAO', end_date_col='DT_FIM_ANALISE', output_col='DIFERENCA_DIAS'):
        self.start_date_col = start_date_col
        self.end_date_col = end_date_col
        self.output_col = output_col

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()
        X[self.start_date_col] = pd.to_datetime(X[self.start_date_col], format='%d/%m/%y', errors='coerce')
        X[self.end_date_col] = pd.to_datetime(X[self.end_date_col], format='%d/%m/%y', errors='coerce')
        X[self.output_col] = (X[self.end_date_col] - X[self.start_date_col]).dt.days
        return X


class DropColumnsTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, columns_to_drop):
        self.columns_to_drop = columns_to_drop

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return X.drop(columns=self.columns_to_drop, errors='ignore')


class BinaryNumericTransformer(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()
        # DATA_CANCELAMENTO: 1 se não nulo, caso contrário 0
        X['DATA_CANCELAMENTO'] = X['DATA_CANCELAMENTO'].notnull().astype(int)
        # DATA_FIM_CARENCIA: 1 se não nulo, 0 caso contrário
        X['DATA_FIM_CARENCIA'] = X['DATA_FIM_CARENCIA'].notnull().astype(int)
        # DATA_NASCIMENTO: 2024 - ano
        X['DATA_NASCIMENTO'] = 2024 - X['DATA_NASCIMENTO']
        # TITULARIDADE: N->0, S->1
        X['TITULARIDADE'] = X['TITULARIDADE'].map({'N': 0, 'S': 1}).astype(int)
        return X


class Word2VecTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, text_col='DS_ITEM', vector_size=100, window=5, min_count=1, sg=1, epochs=10, seed=42):
        self.text_col = text_col
        self.vector_size = vector_size
        self.window = window
        self.min_count = min_count
        self.sg = sg
        self.epochs = epochs
        self.seed = seed
        self.model = None

    def fit(self, X, y=None):
        texts = X[self.text_col].astype(str).str.lower().str.split()
        self.model = Word2Vec(
            sentences=texts, vector_size=self.vector_size,
            window=self.window, min_count=self.min_count,
            sg=self.sg, epochs=self.epochs, seed=self.seed
        )
        return self

    def transform(self, X):
        X = X.copy()
        texts = X[self.text_col].astype(str).str.lower().str.split()

        def get_embedding(item_tokens):
            vectors = [self.model.wv[word] for word in item_tokens if word in self.model.wv]
            return np.mean(vectors, axis=0) if len(vectors) > 0 else np.zeros(self.model.vector_size)

        embeddings = texts.apply(get_embedding)
        embedding_df = pd.DataFrame(embeddings.tolist(), index=X.index)
        embedding_df.columns = [f'EMBEDDING_{i}' for i in range(embedding_df.shape[1])]

        X = pd.concat([X, embedding_df], axis=1)
        return X


class StatusItemMapper(BaseEstimator, TransformerMixin):
    def __init__(self, status_map):
        self.status_map = status_map

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()
        X['DS_STATUS_ITEM'] = X['DS_STATUS_ITEM'].map(self.status_map)
        return X


class OneHotEncodingTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, cols_to_encode):
        self.cols_to_encode = cols_to_encode
        self.encoder = OneHotEncoder(
            sparse_output=False, 
            drop='first', 
            handle_unknown='ignore',
            min_frequency=0.01,  # Ignora categorias muito raras
            max_categories=50  # Limita número máximo de categorias
        )
        self.categories_ = None

    def fit(self, X, y=None):
        print("Fitting OneHotEncoder and filtering rare categories...")
        # Guarda todas as categorias únicas para diagnóstico
        self.unique_categories_ = {}
        for col in self.cols_to_encode:
            # Converte para string para evitar problemas com tipos mistos
            unique_vals = X[col].astype(str).unique()
            # Remove valores nulos
            unique_vals = [v for v in unique_vals if v != 'nan']
            self.unique_categories_[col] = unique_vals
                
        # Converte todas as colunas para string antes do fit
        X_str = X.copy()
        for col in self.cols_to_encode:
            X_str[col] = X_str[col].astype(str)
        
        # Fit do encoder
        self.encoder.fit(X_str[self.cols_to_encode])
        self.categories_ = self.encoder.categories_
        return self

    def transform(self, X):
        X = X.copy()
        print("Applying one-hot encoding transformation...")
        
        # Converte para string antes da transformação
        for col in self.cols_to_encode:
            X[col] = X[col].astype(str)
        
        # Verifica categorias não vistas
        for i, col in enumerate(self.cols_to_encode):
            current_cats = set(X[col].unique()) - {'nan'}
            known_cats = set(self.categories_[i])
            unseen = current_cats - known_cats
            if unseen:
                print(f"Warning: Found {len(unseen)} unknown categories in {col}")
                print(f"Sample unknown categories: {list(unseen)[:5]}")
        
        encoded_array = self.encoder.transform(X[self.cols_to_encode])
        feature_names = self.encoder.get_feature_names_out(self.cols_to_encode)
        
        encoded_df = pd.DataFrame(
            encoded_array,
            columns=feature_names,
            index=X.index
        )
        
        # Adiciona as novas colunas e remove as originais
        X = pd.concat([X, encoded_df], axis=1)
        X.drop(columns=self.cols_to_encode, inplace=True, errors='ignore')
        
        print(f"Encoded {len(feature_names)} features")
        return X

