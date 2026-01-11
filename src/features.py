from __future__ import annotations
import numpy as np
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from .text_cleaning import find_urls

class FeatureBuilder:
    def __init__(self, max_features=120_000, ngram_range=(1,2), min_df=2):
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            min_df=min_df,
            lowercase=True
        )

    def _url_features(self, texts: list[str]):
        # simple but strong baseline signals
        feats = []
        for t in texts:
            urls = find_urls(t)
            n_urls = len(urls)
            n_https = sum(u.lower().startswith("https://") for u in urls)
            n_http = sum(u.lower().startswith("http://") for u in urls)
            n_short = sum(any(sh in u.lower() for sh in ["bit.ly", "tinyurl", "t.co", "goo.gl"]) for u in urls)
            feats.append([n_urls, n_https, n_http, n_short])
        return csr_matrix(np.asarray(feats, dtype=np.float32))

    def fit_transform(self, texts: list[str]):
        X_text = self.vectorizer.fit_transform(texts)
        X_url = self._url_features(texts)
        return hstack([X_text, X_url], format="csr")

    def transform(self, texts: list[str]):
        X_text = self.vectorizer.transform(texts)
        X_url = self._url_features(texts)
        return hstack([X_text, X_url], format="csr")
