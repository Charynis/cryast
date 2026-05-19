import json
import joblib
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, Dict, List

from config import MODELS_DIR
from utils.logger import get_logger

logger = get_logger(__name__)

MODELS_DIR.mkdir(parents=True, exist_ok=True)
METADATA_PATH = MODELS_DIR / "metadata.json"


def save_model(name: str, model: Any, feature_names: List[str], metrics: Dict):
    path = MODELS_DIR / f"{name}.joblib"
    joblib.dump(model, path)

    meta = load_metadata()
    meta[name] = {
        "trained_at": datetime.utcnow().isoformat(),
        "feature_names": feature_names,
        "metrics": metrics,
        "version": meta.get(name, {}).get("version", 0) + 1,
        "path": str(path),
    }
    _save_metadata(meta)
    logger.info(f"Model '{name}' saved to {path}")


def load_model(name: str) -> Optional[Any]:
    path = MODELS_DIR / f"{name}.joblib"
    if not path.exists():
        return None
    try:
        model = joblib.load(path)
        logger.info(f"Model '{name}' loaded from {path}")
        return model
    except Exception as e:
        logger.error(f"Failed to load model '{name}': {e}")
        return None


def get_feature_names(name: str) -> Optional[List[str]]:
    meta = load_metadata()
    return meta.get(name, {}).get("feature_names")


def model_exists(name: str) -> bool:
    return (MODELS_DIR / f"{name}.joblib").exists()


def all_models_exist(names: List[str]) -> bool:
    return all(model_exists(n) for n in names)


def load_metadata() -> Dict:
    if METADATA_PATH.exists():
        try:
            with open(METADATA_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_metadata(meta: Dict):
    with open(METADATA_PATH, "w") as f:
        json.dump(meta, f, indent=2)


def get_model_age_days(name: str) -> Optional[float]:
    meta = load_metadata()
    if name not in meta:
        return None
    trained_at = meta[name].get("trained_at")
    if not trained_at:
        return None
    try:
        dt = datetime.fromisoformat(trained_at)
        return (datetime.utcnow() - dt).total_seconds() / 86400
    except Exception:
        return None
