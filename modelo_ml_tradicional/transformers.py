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
        X['TITULARIDADE'] = X['TITULARIDADE'].replace({'N': 0, 'S': 1})
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
        self.encoder = OneHotEncoder(sparse_output=False, drop='first')

    def fit(self, X, y=None):
        self.encoder.fit(X[self.cols_to_encode])
        return self

    def transform(self, X):
        X = X.copy()
        encoded_array = self.encoder.transform(X[self.cols_to_encode])
        encoded_df = pd.DataFrame(
            encoded_array,
            columns=self.encoder.get_feature_names_out(self.cols_to_encode),
            index=X.index
        )
        X = pd.concat([X, encoded_df], axis=1)
        X.drop(columns=self.cols_to_encode, inplace=True, errors='ignore')
        return X

