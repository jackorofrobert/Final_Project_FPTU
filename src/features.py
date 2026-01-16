from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

from .text_cleaning import normalize_text, count_urls, has_url, exclamation_count, length_chars

@dataclass
class FeatureBuilder:
    max_features: int = 50000
    ngram_range: tuple = (1, 2)
    min_df: int = 2

    vectorizer: Optional[TfidfVectorizer] = None
    use_numeric: bool = True

    def fit(self, texts: List[str]):
        cleaned = [normalize_text(t) for t in texts]
        self.vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            min_df=self.min_df,
            lowercase=True
        )
        self.vectorizer.fit(cleaned)
        return self

    def _numeric_features(self, texts: List[str]) -> csr_matrix:
        arr = np.array([
            [has_url(t), count_urls(t), exclamation_count(t), length_chars(t)]
            for t in texts
        ], dtype=np.float32)
        return csr_matrix(arr)

    def transform(self, texts: List[str]):
        if self.vectorizer is None:
            raise RuntimeError("FeatureBuilder not fitted.")

        cleaned = [normalize_text(t) for t in texts]
        X_text = self.vectorizer.transform(cleaned)

        if not self.use_numeric:
            return X_text

        X_num = self._numeric_features(texts)
        return hstack([X_text, X_num], format="csr")

    def fit_transform(self, texts: List[str]):
        self.fit(texts)
        return self.transform(texts)
