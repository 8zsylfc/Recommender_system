from __future__ import annotations

import json
import os
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np

from movies.recommender.mf import MFModel

MODEL_DIR = Path(__file__).parent.parent.parent / "models"
MODEL_FILE = MODEL_DIR / "mf_model.pkl"
META_FILE = MODEL_DIR / "mf_model_meta.json"


def ensure_model_dir():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def save_model(model: MFModel, training_info: dict | None = None) -> None:
    ensure_model_dir()
    
    model_data = {
        "user_ids": model.user_ids,
        "movie_ids": model.movie_ids,
        "P": model.P,
        "Q": model.Q,
        "bu": model.bu,
        "bi": model.bi,
        "mu": model.mu,
    }
    
    with open(MODEL_FILE, "wb") as f:
        pickle.dump(model_data, f)
    
    meta = {
        "version": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "updated_at": datetime.now().isoformat(),
        "n_users": len(model.user_ids),
        "n_movies": len(model.movie_ids),
        "training_info": training_info or {},
    }
    
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def load_model() -> MFModel | None:
    if not MODEL_FILE.exists():
        return None
    
    try:
        with open(MODEL_FILE, "rb") as f:
            model_data = pickle.load(f)
        
        return MFModel(
            user_ids=model_data["user_ids"],
            movie_ids=model_data["movie_ids"],
            P=model_data["P"],
            Q=model_data["Q"],
            bu=model_data["bu"],
            bi=model_data["bi"],
            mu=model_data["mu"],
        )
    except Exception:
        return None


def get_model_meta() -> dict | None:
    if not META_FILE.exists():
        return None
    
    try:
        with open(META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def model_exists() -> bool:
    return MODEL_FILE.exists()


def delete_model() -> bool:
    deleted = False
    if MODEL_FILE.exists():
        MODEL_FILE.unlink()
        deleted = True
    if META_FILE.exists():
        META_FILE.unlink()
        deleted = True
    return deleted
