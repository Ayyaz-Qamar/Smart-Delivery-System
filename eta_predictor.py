"""
Supervised ML: Predict delivery time (ETA) from features.

Inputs: distance_km, hour_of_day, traffic_level, package_weight
Output: ETA in minutes

We train two models — Linear Regression (baseline) and XGBoost (production) —
and persist the better one to disk. At inference time we load the saved model.
"""
import os
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

MODEL_DIR = Path(__file__).parent.parent.parent / "ml_models" / "saved"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODEL_DIR / "eta_model.pkl"

FEATURE_COLS = ["distance_km", "hour_of_day", "traffic_level", "package_weight"]


def generate_synthetic_data(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Generate realistic synthetic delivery data for training."""
    rng = np.random.default_rng(seed)
    distance_km = rng.uniform(0.5, 50, n)
    hour = rng.integers(0, 24, n)
    traffic = rng.integers(1, 4, n)         # 1=low, 2=med, 3=high
    weight = rng.uniform(0.1, 20, n)

    # ETA simulation: base = distance / avg_speed, plus traffic + rush-hour effects
    base_speed_kmh = 40 - (traffic - 1) * 8        # heavier traffic → lower speed
    rush_penalty = np.where((hour >= 7) & (hour <= 9), 1.4,
                    np.where((hour >= 17) & (hour <= 19), 1.5, 1.0))
    weight_penalty = 1 + weight / 200              # very small effect
    noise = rng.normal(0, 2, n)

    eta_minutes = (distance_km / base_speed_kmh) * 60 * rush_penalty * weight_penalty + noise
    eta_minutes = np.clip(eta_minutes, 1, None)

    return pd.DataFrame({
        "distance_km": distance_km,
        "hour_of_day": hour,
        "traffic_level": traffic,
        "package_weight": weight,
        "eta_minutes": eta_minutes,
    })


def train_model(save: bool = True):
    """Train both models, pick the best, and persist it."""
    df = generate_synthetic_data()
    X, y = df[FEATURE_COLS], df["eta_minutes"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Baseline
    lr = LinearRegression().fit(X_train, y_train)
    lr_mae = mean_absolute_error(y_test, lr.predict(X_test))
    print(f"[ETA] Linear Regression MAE: {lr_mae:.2f} min")

    best_model, best_name, best_mae = lr, "LinearRegression", lr_mae

    if HAS_XGB:
        xgb = XGBRegressor(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42)
        xgb.fit(X_train, y_train)
        xgb_mae = mean_absolute_error(y_test, xgb.predict(X_test))
        print(f"[ETA] XGBoost MAE: {xgb_mae:.2f} min")
        if xgb_mae < lr_mae:
            best_model, best_name, best_mae = xgb, "XGBoost", xgb_mae

    print(f"[ETA] Best model: {best_name} (MAE={best_mae:.2f})")
    if save:
        joblib.dump({"model": best_model, "name": best_name, "features": FEATURE_COLS}, MODEL_PATH)
        print(f"[ETA] Saved to {MODEL_PATH}")
    return best_model


def load_model():
    """Load the persisted model, training one on the fly if it doesn't exist."""
    if not MODEL_PATH.exists():
        print("[ETA] No saved model found, training now...")
        train_model()
    bundle = joblib.load(MODEL_PATH)
    return bundle["model"]


def predict_eta(distance_km: float, hour_of_day: int,
                traffic_level: int, package_weight: float = 1.0) -> float:
    """Predict ETA in minutes for a single delivery."""
    model = load_model()
    X = pd.DataFrame([[distance_km, hour_of_day, traffic_level, package_weight]],
                     columns=FEATURE_COLS)
    return float(max(1.0, model.predict(X)[0]))


if __name__ == "__main__":
    # Allow running this file directly to (re)train the model
    train_model()
