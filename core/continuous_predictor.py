import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging
from core.solar_predictor import SolarPredictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContinuousSolarPredictor:
    def __init__(self, models_dir: str = "models", state_dir: str = "data/state"):
        self.predictor = SolarPredictor(models_dir)
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.sequence_length = 48
        self.prediction_horizon = 24
        self.sliding_window_df = None
        self.current_predictions = None
        self.last_update_time = None
        self.is_initialized = False
        
        self.state_file = self.state_dir / "sliding_window_state.json"
        self.window_csv = self.state_dir / "current_window.csv"
        
        logger.info("Continuous predictor initialized")
    
    def initialize_from_historical(self, historical_csv: str, start_index: int = 0) -> Dict:
        try:
            df = pd.read_csv(historical_csv)
            
            if 'datetime' not in df.columns:
                if 'timestamp' in df.columns:
                    df['datetime'] = pd.to_datetime(df['timestamp'])
                elif 'time' in df.columns:
                    df['datetime'] = pd.to_datetime(df['time'])
            
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.sort_values('datetime').reset_index(drop=True)
            
            window_df = df.iloc[start_index:start_index + self.sequence_length].copy()
            
            if len(window_df) < self.sequence_length:
                raise ValueError(f"Need {self.sequence_length} hours. Found {len(window_df)}")
            
            window_df = self.predictor.create_features(window_df)
            
            self.sliding_window_df = window_df
            self.last_update_time = window_df['datetime'].iloc[-1]
            self.is_initialized = True
            
            self._save_state()
            
            predictions, pred_df = self._predict_from_current_window()
            self.current_predictions = {
                'predictions_W': predictions,
                'predictions_kW': [p/1000 for p in predictions],
                'timestamps': pred_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                'predicted_at': datetime.now().isoformat(),
                'window_end': self.last_update_time.isoformat()
            }
            
            logger.info(f"Initialized. Window: {window_df['datetime'].iloc[0]} to {self.last_update_time}")
            
            return {
                'status': 'initialized',
                'window_size': len(self.sliding_window_df),
                'window_start': window_df['datetime'].iloc[0].isoformat(),
                'window_end': self.last_update_time.isoformat(),
                'prediction_available': True
            }
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise
    
    def add_measurement(self, timestamp: str, power_W: float, weather_data: Optional[Dict] = None) -> Dict:
        if not self.is_initialized:
            raise RuntimeError("System not initialized")
        
        try:
            timestamp_dt = pd.to_datetime(timestamp)
            # Normalize to tz-naive by converting aware→UTC then dropping tz
            if getattr(timestamp_dt, 'tzinfo', None) is not None and timestamp_dt.tzinfo.utcoffset(timestamp_dt) is not None:
                timestamp_dt = timestamp_dt.tz_convert('UTC').tz_localize(None)
            
            if timestamp_dt <= self.last_update_time:
                logger.warning(f"Timestamp not sequential")
                return {'status': 'ignored', 'reason': 'timestamp_not_sequential'}
            
            new_row = {'datetime': timestamp_dt, 'Power(W)': power_W}
            if weather_data:
                new_row.update(weather_data)
            
            new_df = pd.DataFrame([new_row])
            temp_window = pd.concat([self.sliding_window_df, new_df], ignore_index=True)
            temp_window = self.predictor.create_features(temp_window)
            new_row_with_features = temp_window.iloc[-1:].copy()
            
            self.sliding_window_df = pd.concat([
                self.sliding_window_df.iloc[1:],
                new_row_with_features
            ], ignore_index=True)
            
            self.last_update_time = timestamp_dt
            self._save_state()
            
            predictions, pred_df = self._predict_from_current_window()
            self.current_predictions = {
                'predictions_W': predictions,
                'predictions_kW': [p/1000 for p in predictions],
                'timestamps': pred_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                'predicted_at': datetime.now().isoformat(),
                'window_end': self.last_update_time.isoformat()
            }
            
            logger.info(f"Added: {timestamp_dt} = {power_W}W")
            
            return {
                'status': 'updated',
                'timestamp': timestamp_dt.isoformat(),
                'power_W': power_W,
                'window_start': self.sliding_window_df['datetime'].iloc[0].isoformat(),
                'window_end': self.last_update_time.isoformat(),
                'prediction_updated': True,
                'next_expected_time': (self.last_update_time + timedelta(hours=1)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to add measurement: {e}")
            raise
    
    def get_current_predictions(self) -> Dict:
        if not self.is_initialized or self.current_predictions is None:
            raise RuntimeError("No predictions available")
        return self.current_predictions.copy()
    
    def get_window_data(self) -> pd.DataFrame:
        if not self.is_initialized:
            raise RuntimeError("System not initialized")
        return self.sliding_window_df.copy()
    
    def get_status(self) -> Dict:
        if not self.is_initialized:
            return {'initialized': False}
        
        return {
            'initialized': True,
            'window_size': len(self.sliding_window_df),
            'window_start': self.sliding_window_df['datetime'].iloc[0].isoformat(),
            'window_end': self.last_update_time.isoformat(),
            'last_update': self.last_update_time.isoformat(),
            'next_expected': (self.last_update_time + timedelta(hours=1)).isoformat(),
            'predictions_available': self.current_predictions is not None
        }
    
    def _predict_from_current_window(self) -> Tuple[List[float], pd.DataFrame]:
        # If predictor is in demo mode (no model loaded), generate mock predictions
        if self.predictor.model is None or self.predictor.scaler_features is None or self.predictor.scaler_target is None:
            logger.warning("Using demo mode for continuous predictions")
            last_time = self.last_update_time
            pred_timestamps = [last_time + timedelta(hours=i+1) for i in range(24)]
            
            # Generate realistic solar pattern (scaled to ~6000W average)
            hours = np.array([t.hour for t in pred_timestamps])
            mock_predictions = np.where(
                (hours >= 6) & (hours < 18),
                np.maximum(0, 8000 * np.sin((hours - 6) * np.pi / 12) + np.random.randn(24) * 500),
                np.zeros(24)
            )
            mock_predictions = np.maximum(0, mock_predictions)
            
            pred_df = pd.DataFrame({
                'timestamp': pred_timestamps,
                'predicted_power_W': mock_predictions
            })
            
            return mock_predictions.tolist(), pred_df
        
        X_all = np.zeros((len(self.sliding_window_df), len(self.predictor.ALL_FEATURES)))
        
        for i, feature_name in enumerate(self.predictor.ALL_FEATURES):
            if feature_name in self.sliding_window_df.columns:
                X_all[:, i] = self.sliding_window_df[feature_name].values
        
        X_scaled = self.predictor.scaler_features.transform(X_all)
        X_selected = X_scaled[:, self.predictor.selected_feature_indices]
        X_seq = X_selected[-self.sequence_length:].reshape(1, self.sequence_length, len(self.predictor.selected_feature_indices))
        
        pred_scaled = self.predictor.model.predict(X_seq, verbose=0)
        predictions = self.predictor.scaler_target.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
        predictions = np.maximum(0, predictions)
        
        last_time = self.last_update_time
        pred_timestamps = [last_time + timedelta(hours=i+1) for i in range(len(predictions))]
        
        pred_df = pd.DataFrame({
            'timestamp': pred_timestamps,
            'predicted_power_W': predictions
        })
        
        return predictions.tolist(), pred_df
    
    def _save_state(self):
        try:
            self.sliding_window_df.to_csv(self.window_csv, index=False)
            
            state = {
                'is_initialized': self.is_initialized,
                'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
                'window_size': len(self.sliding_window_df) if self.sliding_window_df is not None else 0,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def load_state(self) -> bool:
        try:
            if not self.state_file.exists() or not self.window_csv.exists():
                return False
            
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            self.sliding_window_df = pd.read_csv(self.window_csv)
            self.sliding_window_df['datetime'] = pd.to_datetime(self.sliding_window_df['datetime'])
            
            self.is_initialized = state['is_initialized']
            self.last_update_time = pd.to_datetime(state['last_update_time'])
            
            if self.is_initialized:
                predictions, pred_df = self._predict_from_current_window()
                self.current_predictions = {
                    'predictions_W': predictions,
                    'predictions_kW': [p/1000 for p in predictions],
                    'timestamps': pred_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                    'predicted_at': datetime.now().isoformat(),
                    'window_end': self.last_update_time.isoformat()
                }
            
            logger.info(f"State loaded")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return False
    
    def reset(self):
        self.sliding_window_df = None
        self.current_predictions = None
        self.last_update_time = None
        self.is_initialized = False
        
        if self.state_file.exists():
            self.state_file.unlink()
        if self.window_csv.exists():
            self.window_csv.unlink()
        
        logger.info("System reset")