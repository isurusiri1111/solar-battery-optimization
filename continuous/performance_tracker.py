import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTracker:
    def __init__(self, history_dir="data/history"):
        self.history_dir = Path(history_dir)
        self.performance_dir = self.history_dir / "performance"
        self.performance_dir.mkdir(parents=True, exist_ok=True)
        self.actual_vs_predicted_csv = self.performance_dir / "actual_vs_predicted.csv"
        logger.info("Performance tracker initialized")
    def record_actual_vs_predicted(self, timestamp, predicted_power_W, actual_power_W):
        try:
            error_W = actual_power_W - predicted_power_W
            error_percent = (error_W / (predicted_power_W + 1e-6)) * 100
            record = {"timestamp": timestamp.isoformat(), "predicted_W": predicted_power_W, "actual_W": actual_power_W, "error_W": error_W, "error_percent": error_percent, "absolute_error_W": abs(error_W)}
            df_new = pd.DataFrame([record])
            if self.actual_vs_predicted_csv.exists():
                df_existing = pd.read_csv(self.actual_vs_predicted_csv)
                df = pd.concat([df_existing, df_new], ignore_index=True)
            else:
                df = df_new
            df.to_csv(self.actual_vs_predicted_csv, index=False)
        except Exception as e:
            logger.error(f"Failed: {e}")
    def get_prediction_accuracy(self, hours=24):
        try:
            if not self.actual_vs_predicted_csv.exists():
                return {"error": "No data available"}
            df = pd.read_csv(self.actual_vs_predicted_csv)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            cutoff = datetime.now() - timedelta(hours=hours)
            df_recent = df[df["timestamp"] >= cutoff]
            if len(df_recent) == 0:
                return {"error": "No recent data"}
            return {"total_samples": len(df_recent), "mean_absolute_error_W": float(df_recent["absolute_error_W"].mean()), "mean_error_W": float(df_recent["error_W"].mean()), "mean_absolute_percent_error": float(df_recent["error_percent"].abs().mean()), "rmse_W": float((df_recent["error_W"] ** 2).mean() ** 0.5), "max_absolute_error_W": float(df_recent["absolute_error_W"].max())}
        except Exception as e:
            return {"error": str(e)}
