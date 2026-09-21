"""Feature extraction and preprocessing pipeline."""

from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from scipy.sparse import hstack, csr_matrix

ANOMALY_FEATURE_NAMES = [
    "response_time_ms",
    "db_latency_ms",
    "cpu_percent",
    "memory_percent",
    "request_rate",
    "error_rate",
    "active_connections",
]

CLASSIFIER_NUMERIC_FEATURES = [
    "status_code",
    "response_time_ms",
    "db_latency_ms",
    "cpu_percent",
    "memory_percent",
]


class IncidentFeatureExtractor(BaseEstimator, TransformerMixin):
    """Combines TF-IDF log text features with scaled tabular metadata features."""

    def __init__(self, max_features: int = 1500):
        self.max_features = max_features
        self.tfidf = TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=(1, 2),
            stop_words="english",
        )
        self.scaler = StandardScaler()

    def fit(self, X: pd.DataFrame, y=None):
        texts = X["text"].fillna("").astype(str)
        self.tfidf.fit(texts)

        num_data = X[CLASSIFIER_NUMERIC_FEATURES].fillna(0).values
        self.scaler.fit(num_data)
        return self

    def transform(self, X: pd.DataFrame):
        texts = X["text"].fillna("").astype(str)
        text_matrix = self.tfidf.transform(texts)

        num_data = X[CLASSIFIER_NUMERIC_FEATURES].fillna(0).values
        scaled_num = self.scaler.transform(num_data)

        # Horizontally stack text sparse matrix with numerical features
        combined = hstack([text_matrix, csr_matrix(scaled_num)])
        return combined
