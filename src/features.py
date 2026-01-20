from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from xgboost import XGBClassifier


def build_feature_pipeline():
    """
    Build feature extraction + classifier pipeline.
    Returns a sklearn Pipeline object.
    """

    tfidf = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        lowercase=True,
        stop_words="english"
    )

    clf = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        use_label_encoder=False,
        random_state=42
    )

    pipeline = Pipeline(
        steps=[
            ("features", tfidf),
            ("clf", clf),
        ]
    )

    return pipeline
