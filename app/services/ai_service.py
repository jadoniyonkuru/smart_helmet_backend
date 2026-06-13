"""
ai_service.py — AI Inference Pipeline
Loads 4 trained models and runs majority-vote ensemble on every sensor reading.
"""

import numpy as np
import joblib
from collections import deque
import os

# TensorFlow for LSTM
try:
    import tensorflow as tf
except Exception:
    tf = None


class AIService:
    def __init__(self, models_dir: str = "smart-helmet-ai-models"):
        self.models_dir = models_dir
        self.models_loaded = False
        self.lstm_buffers = {}  # helmet_id -> deque(maxlen=10)
        self.load_models()

    def load_models(self):
        """Load all 4 trained models + scaler on startup."""
        try:
            self.scaler = joblib.load(os.path.join(self.models_dir, "scaler.pkl"))
            self.feature_cols = joblib.load(
                os.path.join(self.models_dir, "feature_cols.pkl")
            )
            self.isolation_forest = joblib.load(
                os.path.join(self.models_dir, "model1_isolation_forest.pkl")
            )
            self.random_forest = joblib.load(
                os.path.join(self.models_dir, "model2_random_forest.pkl")
            )
            if tf is not None:
                try:
                    import tf_keras
                    self.lstm_model = tf_keras.models.load_model(
                        os.path.join(self.models_dir, "model3_lstm.h5")
                    )
                except Exception:
                    # Fallback: try with compile=False for Keras 3 compatibility
                    self.lstm_model = tf.keras.models.load_model(
                        os.path.join(self.models_dir, "model3_lstm.h5"),
                        compile=False
                    )
            else:
                self.lstm_model = None
            self.svm_model = joblib.load(
                os.path.join(self.models_dir, "model4_svm.pkl")
            )
            self.models_loaded = True
            print("[AI] All 4 models loaded successfully")
        except Exception as e:
            print(f"[AI] Error loading models: {e}")
            self.models_loaded = False

    def build_feature_vector(self, sensor_data: dict) -> np.ndarray:
        """
        Construct the 7-feature vector matching training data column order.
        """
        # Accept both firmware field names and backend field names
        co = sensor_data.get("co_ppm", sensor_data.get("co", 0)) or 0
        ch4 = sensor_data.get("ch4_pct", sensor_data.get("ch4", 0)) or 0
        temp = sensor_data.get("temperature_c", sensor_data.get("temperature", 0)) or 0
        hum = sensor_data.get("humidity_pct", sensor_data.get("humidity", 0)) or 0

        feature_vector = np.array(
            [
                [
                    float(co),  # Sensor1[ppm] — primary gas reading
                    float(co),  # Sensor2[ppm] — same MQ-2 source
                    float(ch4) * 100,  # Sensor3[ppm] — CH4 % → ppm equivalent
                    float(co),  # Sensor4[ppm] — duplicate for schema compat
                    float(temp),  # Temperature[C]
                    float(hum),  # Humidity[%]
                    float(co),  # True_concentration[ppm] — best proxy
                ]
            ]
        )

        return self.scaler.transform(feature_vector)

    def run_inference(self, sensor_data: dict) -> dict:
        """
        Run all 4 models and return majority vote result.
        """
        if not self.models_loaded:
            return {
                "prediction": "unknown",
                "danger_votes": 0,
                "confidence": 0,
                "model_votes": {
                    "isolation_forest": "unknown",
                    "random_forest": "unknown",
                    "lstm": "unknown",
                    "svm": "unknown",
                },
            }

        features = self.build_feature_vector(sensor_data)

        # Model 1: Isolation Forest
        if_pred = self.isolation_forest.predict(features)[0]
        if_vote = 1 if if_pred == -1 else 0  # -1 = anomaly/danger

        # Model 2: Random Forest
        rf_pred = self.random_forest.predict(features)[0]
        rf_proba = self.random_forest.predict_proba(features)[0]
        rf_vote = int(rf_pred)
        confidence = float(max(rf_proba)) * 100

        # Model 3: LSTM (temporal — needs sequence buffer)
        lstm_vote = self._run_lstm(sensor_data, features[0])

        # Model 4: SVM
        svm_pred = self.svm_model.predict(features)[0]
        svm_vote = int(svm_pred)

        # Majority vote with tie-breaking:
        #   3-4 danger votes → always danger
        #   0-1 danger votes → always safe
        #   2-2 tie          → danger only if RF voted danger AND confidence >= 75%
        total_votes = if_vote + rf_vote + lstm_vote + svm_vote

        if total_votes >= 3:
            verdict = "danger"
        elif total_votes <= 1:
            verdict = "safe"
        else:
            # Exact 2-2 tie — RF confidence is the tiebreaker
            rf_danger_prob = float(rf_proba[1]) * 100 if len(rf_proba) > 1 else 0.0
            verdict = "danger" if (rf_vote == 1 and rf_danger_prob >= 75.0) else "safe"

        return {
            "prediction": verdict,
            "danger_votes": int(total_votes),
            "confidence": round(float(confidence), 1),
            "model_votes": {
                "isolation_forest": "danger" if if_vote else "safe",
                "random_forest": "danger" if rf_vote else "safe",
                "lstm": "danger" if lstm_vote else "safe",
                "svm": "danger" if svm_vote else "safe",
            },
        }

    def _run_lstm(self, sensor_data: dict, feature_1d: np.ndarray) -> int:
        """
        LSTM requires a sequence of 10 consecutive readings.
        Maintains a rolling buffer per helmet_id.
        Returns 1 (danger) or 0 (safe).
        """
        helmet_id = str(sensor_data.get("helmet_id", "default"))

        if helmet_id not in self.lstm_buffers:
            self.lstm_buffers[helmet_id] = deque(maxlen=10)

        self.lstm_buffers[helmet_id].append(feature_1d)

        # Need at least 10 readings before LSTM can predict
        if len(self.lstm_buffers[helmet_id]) < 10 or self.lstm_model is None:
            return 0  # Default to safe until buffer is full or model unavailable

        # Shape: (1, 10, 7) — batch=1, timesteps=10, features=7
        sequence = np.array(list(self.lstm_buffers[helmet_id])).reshape(1, 10, 7)
        prediction = self.lstm_model.predict(sequence, verbose=0)[0][0]

        return 1 if prediction >= 0.5 else 0


# ── Singleton instance (initialize on import) ─────────────
ai_service = AIService()
