import pandas as pd
import numpy as np
import joblib
import tensorflow as tf
import json
from pathlib import Path
from typing import Tuple, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SolarPredictor:
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.model = None
        self.scaler_features = None
        self.scaler_target = None
        self.config = None
        self.selected_feature_indices = None
        self.sequence_length = 48
        
        self.ALL_FEATURES = [
            'relative_humidity_2m ', 'wind_speed_10m', 'wind_direction_10m',
            'cloud_cover_low', 'diffuse_radiation', 'diffuse_radiation_instant',
            'direct_radiation', 'direct_radiation_instant', 'direct_normal_irradiance',
            'direct_normal_irradiance_instant', 'is_day', 'hour_angle',
            'solar_azimuth_rad', 'solar_azimuth_deg', 'is_daylight',
            'solar_potential', 'wind_cooling', 'weather_clarity_index',
            'day', 'year', 'day_of_week', 'hour_sin', 'hour_cos',
            'day_year_sin', 'day_year_cos', 'day_week_sin', 'day_week_cos',
            'month_sin', 'month_cos', 'season', 'season_sin', 'season_cos',
            'is_weekend', 'is_month_start',
            'Power(W)_lag_1h', 'Power(W)_lag_2h', 'Power(W)_lag_3h',
            'Power(W)_lag_6h', 'Power(W)_lag_12h', 'Power(W)_lag_24h', 'Power(W)_lag_48h',
            'Power(W)_diff_1h', 'Power(W)_diff_24h', 'Power(W)_diff_7d',
            'Power(W)_roll_mean_3h', 'Power(W)_roll_std_3h', 'Power(W)_roll_max_3h',
            'Power(W)_roll_min_3h', 'Power(W)_roll_range_3h',
            'Power(W)_roll_mean_6h', 'Power(W)_roll_std_6h', 'Power(W)_roll_max_6h',
            'Power(W)_roll_min_6h', 'Power(W)_roll_range_6h',
            'Power(W)_roll_mean_12h', 'Power(W)_roll_std_12h', 'Power(W)_roll_max_12h',
            'Power(W)_roll_min_12h', 'Power(W)_roll_range_12h',
            'Power(W)_ewm_6h', 'Power(W)_ewm_12h', 'Power(W)_ewm_24h'
        ]
        
        self.load_models()
    
    def load_models(self):
        try:
            model_files = list(self.models_dir.glob("final_model_*.keras"))
            config_files = list(self.models_dir.glob("model_config_*.json"))
            scaler_f_files = list(self.models_dir.glob("scaler_features_*.pkl"))
            scaler_t_files = list(self.models_dir.glob("scaler_target_*.pkl"))
            
            if not all([model_files, config_files, scaler_f_files, scaler_t_files]):
                logger.warning("Model files not found - using demo mode with mock predictions")
                # Set default configuration for demo mode
                self.config = {"sequence_length": 48, "selected_feature_indices": list(range(len(self.ALL_FEATURES)))}
                self.selected_feature_indices = self.config["selected_feature_indices"]
                self.sequence_length = 48
                return
            
            self.model = tf.keras.models.load_model(str(model_files[0]))
            self.scaler_features = joblib.load(str(scaler_f_files[0]))
            self.scaler_target = joblib.load(str(scaler_t_files[0]))
            
            with open(str(config_files[0]), 'r') as f:
                self.config = json.load(f)
            
            self.selected_feature_indices = self.config["selected_feature_indices"]
            self.sequence_length = self.config.get("sequence_length", 48)
            
            logger.info(f"Models loaded. Sequence: {self.sequence_length}h")
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            logger.warning("Continuing in demo mode")
    
    def create_features(self, df: pd.DataFrame, latitude: float = 9.67) -> pd.DataFrame:
        df = df.copy()
        
        if 'datetime' not in df.columns:
            if 'timestamp' in df.columns:
                df['datetime'] = pd.to_datetime(df['timestamp'])
            elif 'time' in df.columns:
                df['datetime'] = pd.to_datetime(df['time'])
        
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['hour'] = df['datetime'].dt.hour
        df['day_of_year'] = df['datetime'].dt.dayofyear
        lat_rad = np.radians(latitude)
        
        df['solar_declination'] = 23.45 * np.sin(np.radians(360 * (284 + df['day_of_year']) / 365))
        df['hour_angle'] = 15 * (df['hour'] - 12)
        
        sin_elevation = (np.sin(np.radians(df['solar_declination'])) * np.sin(lat_rad) +
                        np.cos(np.radians(df['solar_declination'])) * np.cos(lat_rad) * 
                        np.cos(np.radians(df['hour_angle'])))
        
        df['solar_elevation_rad'] = np.arcsin(np.clip(sin_elevation, -1, 1))
        df['solar_elevation_deg'] = np.degrees(df['solar_elevation_rad'])
        df['solar_elevation_deg'] = np.maximum(0, df['solar_elevation_deg'])
        
        cos_azimuth = ((np.sin(np.radians(df['solar_declination'])) * np.cos(lat_rad) -
                       np.cos(np.radians(df['solar_declination'])) * np.sin(lat_rad) * 
                       np.cos(np.radians(df['hour_angle']))) / 
                      (np.cos(df['solar_elevation_rad']) + 1e-10))
        
        df['solar_azimuth_rad'] = np.arccos(np.clip(cos_azimuth, -1, 1))
        df['solar_azimuth_deg'] = np.degrees(df['solar_azimuth_rad'])
        df.loc[df['hour'] > 12, 'solar_azimuth_deg'] = 360 - df.loc[df['hour'] > 12, 'solar_azimuth_deg']
        
        df['is_daylight'] = (df['solar_elevation_deg'] > 0).astype(int)
        df['solar_potential'] = df['solar_elevation_deg'] / 90.0
        
        if 'relative_humidity_2m' in df.columns and 'relative_humidity_2m ' not in df.columns:
            df['relative_humidity_2m '] = df['relative_humidity_2m']
        
        if 'wind_speed_10m' in df.columns:
            df['wind_cooling'] = df['wind_speed_10m'] * 0.1
        
        df['weather_clarity_index'] = 1.0
        
        df['day'] = df['datetime'].dt.day
        df['month'] = df['datetime'].dt.month
        df['year'] = df['datetime'].dt.year
        df['day_of_week'] = df['datetime'].dt.dayofweek
        
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_year_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
        df['day_year_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
        df['day_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        season_map = {12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3}
        df['season'] = df['month'].map(season_map)
        df['season_sin'] = np.sin(2 * np.pi * df['season'] / 4)
        df['season_cos'] = np.cos(2 * np.pi * df['season'] / 4)
        
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        df['is_month_start'] = (df['day'] <= 7).astype(int)
        
        if 'Power(W)' in df.columns:
            for lag in [1, 2, 3, 6, 12, 24, 48]:
                df[f'Power(W)_lag_{lag}h'] = df['Power(W)'].shift(lag)
            
            df['Power(W)_diff_1h'] = df['Power(W)'].diff(1)
            df['Power(W)_diff_24h'] = df['Power(W)'].diff(24)
            df['Power(W)_diff_7d'] = df['Power(W)'].diff(24 * 7)
            
            for window in [3, 6, 12]:
                df[f'Power(W)_roll_mean_{window}h'] = df['Power(W)'].rolling(window, min_periods=1).mean()
                df[f'Power(W)_roll_std_{window}h'] = df['Power(W)'].rolling(window, min_periods=1).std()
                df[f'Power(W)_roll_max_{window}h'] = df['Power(W)'].rolling(window, min_periods=1).max()
                df[f'Power(W)_roll_min_{window}h'] = df['Power(W)'].rolling(window, min_periods=1).min()
                df[f'Power(W)_roll_range_{window}h'] = df[f'Power(W)_roll_max_{window}h'] - df[f'Power(W)_roll_min_{window}h']
            
            for span in [6, 12, 24]:
                df[f'Power(W)_ewm_{span}h'] = df['Power(W)'].ewm(span=span, adjust=False).mean()
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isnull().any():
                df[col] = df[col].interpolate(method='linear', limit_direction='both')
                df[col] = df[col].ffill().bfill().fillna(0)
        
        for feature in self.ALL_FEATURES:
            if feature not in df.columns:
                df[feature] = 0
        
        return df
    
    def predict_next_24h(self, historical_csv_path: str, start_index: int = 0) -> Tuple[List[float], pd.DataFrame]:
        try:
            df = pd.read_csv(historical_csv_path)
            df_subset = df.iloc[start_index:start_index + self.sequence_length].copy()
            
            if len(df_subset) < self.sequence_length:
                raise ValueError(f"Need {self.sequence_length} hours. Found {len(df_subset)}")
            
            # If model is not loaded (demo mode), generate mock predictions
            if self.model is None:
                logger.warning("Using demo mode - generating mock solar predictions")
                last_time = pd.to_datetime(df_subset['datetime'].iloc[-1])
                pred_timestamps = [last_time + pd.Timedelta(hours=i+1) for i in range(24)]
                
                # Generate realistic-looking solar pattern (sine wave for day/night)
                hours = np.array([t.hour for t in pred_timestamps])
                # Solar production: 0 at night (0-6, 18-24), peak around noon
                mock_predictions = np.where(
                    (hours >= 6) & (hours < 18),
                    np.maximum(0, 500 * np.sin((hours - 6) * np.pi / 12) + np.random.randn(24) * 50),
                    np.zeros(24)
                )
                mock_predictions = np.maximum(0, mock_predictions)  # Ensure non-negative
                
                pred_df = pd.DataFrame({
                    'timestamp': pred_timestamps,
                    'predicted_power_W': mock_predictions
                })
                
                logger.info(f"Demo prediction (24h): Mean={np.mean(mock_predictions):.1f}W (MOCK DATA)")
                return mock_predictions.tolist(), pred_df
            
            df_subset = self.create_features(df_subset)
            
            X_all = np.zeros((len(df_subset), len(self.ALL_FEATURES)))
            for i, feature_name in enumerate(self.ALL_FEATURES):
                if feature_name in df_subset.columns:
                    X_all[:, i] = df_subset[feature_name].values
            
            X_scaled = self.scaler_features.transform(X_all)
            X_selected = X_scaled[:, self.selected_feature_indices]
            X_seq = X_selected[-self.sequence_length:].reshape(1, self.sequence_length, len(self.selected_feature_indices))
            
            pred_scaled = self.model.predict(X_seq, verbose=0)
            predictions = self.scaler_target.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
            predictions = np.maximum(0, predictions)
            
            last_time = pd.to_datetime(df_subset['datetime'].iloc[-1])
            pred_timestamps = [last_time + pd.Timedelta(hours=i+1) for i in range(len(predictions))]
            
            pred_df = pd.DataFrame({
                'timestamp': pred_timestamps,
                'predicted_power_W': predictions
            })
            
            logger.info(f"Predicted 24h: Mean={np.mean(predictions):.1f}W")
            return predictions.tolist(), pred_df
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise