import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import pandas as pd
import logging
from core.battery_optimizer import BatteryOptimizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContinuousOptimizer:
    def __init__(self, historical_csv="data/historical_solar_data.csv", history_dir="data/history", output_dir="data/output"):
        self.historical_csv = Path(historical_csv)
        self.history_dir = Path(history_dir)
        self.output_dir = Path(output_dir)
        (self.history_dir / "optimizations").mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.optimizer = BatteryOptimizer()
        self.battery_params = {"E_capacity": 100, "P_charge_max": 25, "P_discharge_max": 25, "SOC_min": 0.2, "SOC_max": 0.9, "eta_charge": 0.95, "eta_discharge": 0.95, "SOC_initial": 0.5}
        self.is_auto_optimization_enabled = False
        self.last_optimization_result = None
        logger.info("Continuous optimizer initialized")
    
    def enable_auto_optimization(self):
        self.is_auto_optimization_enabled = True
    
    def disable_auto_optimization(self):
        self.is_auto_optimization_enabled = False
    
    def load_data(self, start_index=0, num_hours=24, window_end_time=None):
        """Load load demand data for the next 24 hours after window_end_time"""
        df = pd.read_csv(self.historical_csv)
        # Normalize datetime column
        if 'datetime' not in df.columns:
            for col in ["timestamp", "time"]:
                if col in df.columns:
                    df["datetime"] = pd.to_datetime(df[col])
                    break
        df["datetime"] = pd.to_datetime(df["datetime"])  # ensure dtype

        # Sanitize load column
        if 'Load_kW' not in df.columns:
            raise ValueError("Column 'Load_kW' not found in historical CSV")
        load = pd.to_numeric(df['Load_kW'], errors='coerce')
        load = load.replace([float('inf'), float('-inf')], pd.NA).ffill().bfill().fillna(0.0)
        df['Load_kW'] = load.clip(lower=0.0)

        # If window_end_time is provided, get load data for next 24 hours after that time
        if window_end_time is not None:
            window_end_dt = pd.to_datetime(window_end_time)
            # Find rows after window_end_time
            future_rows = df[df['datetime'] > window_end_dt].head(num_hours)
            
            if len(future_rows) >= num_hours:
                df_subset = future_rows.copy()
            else:
                # If not enough future data, pad with last available value
                last_val = float(df['Load_kW'].iloc[-1]) if len(df) > 0 else 0.0
                last_time = df['datetime'].iloc[-1] if len(df) > 0 else window_end_dt
                
                pad_count = num_hours - len(future_rows)
                pad_rows = pd.DataFrame({
                    'datetime': [last_time + pd.Timedelta(hours=i+1) for i in range(pad_count)],
                    'Load_kW': [last_val] * pad_count
                })
                df_subset = pd.concat([future_rows, pad_rows], ignore_index=True)
        else:
            # Fallback to old behavior using start_index
            end_index = start_index + num_hours
            if end_index > len(df):
                end_index = len(df)
                start_index = max(0, end_index - num_hours)
            df_subset = df.iloc[start_index:end_index].copy()
            if len(df_subset) < num_hours:
                # pad by repeating last value if necessary
                last_val = float(df_subset['Load_kW'].iloc[-1]) if len(df_subset) > 0 else 0.0
                pad_count = num_hours - len(df_subset)
                pad_rows = pd.DataFrame({
                    'datetime': [df['datetime'].iloc[-1]] * pad_count,
                    'Load_kW': [last_val] * pad_count
                })
                df_subset = pd.concat([df_subset, pad_rows], ignore_index=True)

        return {
            "load_demand_kW": df_subset["Load_kW"].astype(float).tolist(),
            "start_hour": int(pd.to_datetime(df_subset["datetime"].iloc[0]).hour)
        }
    
    def optimize(self, solar_predictions_W, prediction_timestamp, start_index=0, start_hour=None, force=False, window_end_time=None):
        if not force and not self.is_auto_optimization_enabled:
            return {"status": "skipped"}
        
        data = self.load_data(start_index=start_index, num_hours=24, window_end_time=window_end_time)
        start_h = start_hour if start_hour is not None else data["start_hour"]
        
        # Validate prediction vector
        if solar_predictions_W is None or len(solar_predictions_W) < 24:
            raise ValueError(f"Expected 24 predictions, got {0 if solar_predictions_W is None else len(solar_predictions_W)}")

        results = self.optimizer.optimize(
            solar_forecast_W=solar_predictions_W,
            load_demand_kW=data["load_demand_kW"],
            time_horizon=24,
            start_hour=start_h
        )
        
        self.last_optimization_result = results
        logger.info("Optimization complete")
        return results
    
    def on_prediction_update(self, solar_predictions_W, prediction_timestamp, start_index=0, start_hour=None, window_end_time=None):
        if not self.is_auto_optimization_enabled:
            return None
        return self.optimize(
            solar_predictions_W=solar_predictions_W,
            prediction_timestamp=prediction_timestamp,
            start_index=start_index,
            start_hour=start_hour,
            window_end_time=window_end_time,
            force=False
        )
    
    def get_latest_optimization(self):
        return self.last_optimization_result
