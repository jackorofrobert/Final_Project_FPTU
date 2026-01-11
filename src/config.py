from dataclasses import dataclass
from pathlib import Path

@dataclass
class TrainConfig:
    seed: int = 42
    test_size: float = 0.15
    val_size: float = 0.15  # split from remaining train
    text_col: str | None = None
    label_col: str | None = None

    # TF-IDF
    max_features: int = 120_000
    ngram_range: tuple[int, int] = (1, 2)
    min_df: int = 2

    # XGBoost
    n_estimators: int = 600
    learning_rate: float = 0.05
    max_depth: int = 6
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    reg_lambda: float = 1.0
    reg_alpha: float = 0.0

    out_dir: Path = Path("models")
