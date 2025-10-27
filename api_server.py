"""
Complete Continuous API Server
SIMPLIFIED: Single CSV, Fixed Battery Params, Fixed Tariff
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

from core.continuous_predictor import ContinuousSolarPredictor
from core.data_validator import DataValidator
from continuous.continuous_optimizer import ContinuousOptimizer
from continuous.scheduler import TaskScheduler
from continuous.performance_tracker import PerformanceTracker
from continuous.history_manager import HistoryManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

Path("logs").mkdir(exist_ok=True)

# Initialize FastAPI
app = FastAPI(
    title="Continuous Solar + Battery Optimization API",
    description="Simplified system with single CSV and fixed parameters",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
predictor = ContinuousSolarPredictor()
optimizer = ContinuousOptimizer()
scheduler = TaskScheduler()
tracker = PerformanceTracker()
history = HistoryManager()
validator = DataValidator()

# Try to load previous state
if predictor.load_state():
    logger.info("✓ Loaded previous session state")

# Global state
system_state = {
    'initialized': False,
    'auto_optimization_enabled': False,
    'last_measurement_time': None,
    'total_measurements': 0,
    'total_optimizations': 0
}

# ==================== PYDANTIC MODELS ====================

class InitializeRequest(BaseModel):
    historical_csv: str = "data/historical_solar_data.csv"
    start_index: int = 0
    enable_auto_optimization: bool = True

class MeasurementRequest(BaseModel):
    timestamp: str
    power_W: float
    weather_data: Optional[Dict] = None
    trigger_optimization: bool = True

class BatchMeasurementRequest(BaseModel):
    measurements: List[Dict]
    trigger_optimization: bool = True

class OptimizationRequest(BaseModel):
    start_index: int = 0
    force: bool = False

class AutoOptimizationConfig(BaseModel):
    enabled: bool

# ==================== CALLBACK FUNCTIONS ====================

def on_prediction_updated(predictions_W: List[float], timestamp, start_index: int = 0):
    """Called when predictions are updated"""
    logger.info(f"Predictions updated at {timestamp}")
    
    # Save to history
    pred_data = {
        'predictions_W': predictions_W,
        'predictions_kW': [p/1000 for p in predictions_W],
        'timestamp': timestamp.isoformat(),
        'mean_W': float(pd.Series(predictions_W).mean()),
        'max_W': float(pd.Series(predictions_W).max())
    }
    history.save_prediction(pred_data, timestamp)
    
    # Trigger optimization if enabled
    if optimizer.is_auto_optimization_enabled:
        try:
            # Get start hour from the current window
            window_data = predictor.get_window_data()
            start_hour = pd.to_datetime(window_data['datetime'].iloc[0]).hour
            
            result = optimizer.on_prediction_update(
                solar_predictions_W=predictions_W,
                prediction_timestamp=timestamp,
                start_index=start_index,
                start_hour=start_hour
            )
            
            if result:
                system_state['total_optimizations'] += 1
                logger.info(f"✓ Auto-optimization complete. Cost: Rs.{result['total_cost']:.2f}")
        except Exception as e:
            logger.error(f"Auto-optimization failed: {e}")

# ==================== API ENDPOINTS ====================

@app.get("/")
def home():
    return {
        "message": "Continuous Solar + Battery Optimization System",
        "version": "2.1.0",
        "status": "online",
        "mode": "simplified_single_csv",
        "features": [
            "Single CSV with solar + load + weather",
            "Fixed battery: 100kWh, 25kW, 20-90% SOC",
            "Fixed tariff: Peak/Day/Off-peak",
            "48h sliding window → 24h predictions",
            "Automatic optimization"
        ],
        "battery": "100kWh, 25kW charge/discharge, 20-90% SOC",
        "tariff": "Peak(54/45.80), Day(25/25), Off-peak(13/13) Rs./kWh"
    }

@app.post("/initialize")
async def initialize_system(request: InitializeRequest):
    """Initialize the continuous system"""
    try:
        logger.info(f"Initializing system from {request.historical_csv}")
        
        # Validate data
        is_valid, validation = validator.validate_historical_data(request.historical_csv)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid data: {validation['issues']}")
        
        # Initialize predictor
        result = predictor.initialize_from_historical(
            historical_csv=request.historical_csv,
            start_index=request.start_index
        )
        
        # Enable auto-optimization
        if request.enable_auto_optimization:
            optimizer.enable_auto_optimization()
            system_state['auto_optimization_enabled'] = True
        
        system_state['initialized'] = True
        
        logger.info("✓ System initialized successfully")
        
        return {
            "status": "initialized",
            "predictor": result,
            "auto_optimization": request.enable_auto_optimization,
            "system_state": system_state
        }
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/measurement/add")
async def add_measurement(request: MeasurementRequest, background_tasks: BackgroundTasks):
    """Add new measurement"""
    try:
        # Capture current predictions BEFORE updating the window so we can
        # compare this actual measurement with the previously predicted value
        prior_predictions = None
        try:
            prior_predictions = predictor.get_current_predictions()
        except Exception:
            prior_predictions = None

        result = predictor.add_measurement(
            timestamp=request.timestamp,
            power_W=request.power_W,
            weather_data=request.weather_data
        )
        
        if result['status'] == 'updated':
            system_state['last_measurement_time'] = request.timestamp
            system_state['total_measurements'] += 1
            
            predictions = predictor.get_current_predictions()

            # If we had prior predictions, try to record performance for this timestamp
            try:
                if prior_predictions and 'timestamps' in prior_predictions:
                    ts_list = prior_predictions.get('timestamps', [])
                    preds = prior_predictions.get('predictions_W', [])
                    if ts_list and preds and len(ts_list) == len(preds):
                        # Build a lookup of timestamp -> predicted value
                        pred_map = {str(ts): float(val) for ts, val in zip(ts_list, preds)}
                        # Normalize request timestamp to the same string format as in ts_list
                        req_ts_str = pd.to_datetime(request.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        if req_ts_str in pred_map:
                            tracker.record_actual_vs_predicted(
                                timestamp=pd.to_datetime(request.timestamp),
                                predicted_power_W=pred_map[req_ts_str],
                                actual_power_W=float(request.power_W)
                            )
            except Exception as perf_err:
                logger.warning(f"Failed to record performance: {perf_err}")
            
            if request.trigger_optimization and optimizer.is_auto_optimization_enabled:
                start_index = system_state['total_measurements']
                background_tasks.add_task(
                    on_prediction_updated,
                    predictions['predictions_W'],
                    pd.to_datetime(request.timestamp),
                    start_index
                )
            
            logger.info(f"✓ Measurement added: {request.timestamp} = {request.power_W}W")
        
        return {
            "status": result['status'],
            "measurement": {"timestamp": request.timestamp, "power_W": request.power_W},
            "result": result,
            "system_state": system_state
        }
        
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add measurement: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/measurement/batch")
async def add_batch_measurements(request: BatchMeasurementRequest, background_tasks: BackgroundTasks):
    """Add multiple measurements at once"""
    try:
        results = []
        
        for meas in request.measurements:
            result = predictor.add_measurement(
                timestamp=meas['timestamp'],
                power_W=meas['power_W'],
                weather_data=meas.get('weather_data')
            )
            results.append(result)
            
            if result['status'] == 'updated':
                system_state['total_measurements'] += 1
        
        predictions = predictor.get_current_predictions()
        
        if request.trigger_optimization and optimizer.is_auto_optimization_enabled:
            start_index = system_state['total_measurements']
            background_tasks.add_task(
                on_prediction_updated,
                predictions['predictions_W'],
                pd.to_datetime(request.measurements[-1]['timestamp']),
                start_index
            )
        
        successful = sum(1 for r in results if r['status'] == 'updated')
        
        return {
            "status": "batch_complete",
            "total": len(request.measurements),
            "successful": successful,
            "details": results
        }
        
    except Exception as e:
        logger.error(f"Batch update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/predictions/current")
async def get_current_predictions():
    """Get current 24-hour predictions"""
    try:
        predictions = predictor.get_current_predictions()
        
        predictions['summary'] = {
            'mean_W': float(pd.Series(predictions['predictions_W']).mean()),
            'max_W': float(pd.Series(predictions['predictions_W']).max()),
            'min_W': float(pd.Series(predictions['predictions_W']).min()),
            'total_kWh': float(sum(predictions['predictions_W']) / 1000)
        }
        
        return predictions
        
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/predictions/history")
async def get_prediction_history(limit: int = 10):
    """Get recent prediction history"""
    try:
        history_data = history.get_recent_predictions(limit=limit)
        return {"count": len(history_data), "predictions": history_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize")
async def run_optimization(request: OptimizationRequest):
    """Manually run optimization"""
    try:
        predictions = predictor.get_current_predictions()
        window_data = predictor.get_window_data()
        start_hour = pd.to_datetime(window_data['datetime'].iloc[0]).hour
        
        result = optimizer.optimize(
            solar_predictions_W=predictions['predictions_W'],
            prediction_timestamp=pd.to_datetime(predictions['window_end']),
            start_index=request.start_index,
            start_hour=start_hour,
            force=request.force
        )
        
        if result.get('status') != 'skipped':
            system_state['total_optimizations'] += 1
        
        return result
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/optimize/latest")
async def get_latest_optimization():
    """Get latest optimization result"""
    try:
        result = optimizer.get_latest_optimization()
        
        if result is None:
            raise HTTPException(status_code=404, detail="No optimization results available")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auto-optimization/config")
async def configure_auto_optimization(config: AutoOptimizationConfig):
    """Enable or disable automatic optimization"""
    try:
        if config.enabled:
            optimizer.enable_auto_optimization()
            system_state['auto_optimization_enabled'] = True
            message = "Auto-optimization ENABLED"
        else:
            optimizer.disable_auto_optimization()
            system_state['auto_optimization_enabled'] = False
            message = "Auto-optimization DISABLED"
        
        logger.info(message)
        
        return {
            "status": "updated",
            "auto_optimization_enabled": config.enabled,
            "message": message
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auto-optimization/status")
async def get_auto_optimization_status():
    """Get auto-optimization status"""
    return {
        "enabled": optimizer.is_auto_optimization_enabled
    }

@app.get("/window/current")
async def get_current_window():
    """Get current 48-hour sliding window data"""
    try:
        window_df = predictor.get_window_data()
        
        return {
            'window_size': len(window_df),
            'start': window_df['datetime'].iloc[0].isoformat(),
            'end': window_df['datetime'].iloc[-1].isoformat(),
            'data': window_df[['datetime', 'Power(W)']].to_dict(orient='records')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
def get_status():
    """Get complete system status"""
    try:
        predictor_status = predictor.get_status()
        
        return {
            "api_status": "online",
            "version": "2.1.0",
            "mode": "continuous_sliding_window",
            "system_state": system_state,
            "predictor": predictor_status,
            "optimizer": {
                "auto_enabled": optimizer.is_auto_optimization_enabled
            }
        }
    except Exception as e:
        return {
            "api_status": "online",
            "system_state": system_state,
            "error": str(e)
        }

@app.get("/performance/accuracy")
async def get_prediction_accuracy(hours: int = 24):
    """Get prediction accuracy metrics"""
    try:
        metrics = tracker.get_prediction_accuracy(hours=hours)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/validate/all")
async def validate_all_data():
    """Validate all data files"""
    try:
        results = validator.validate_all_files()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/measurement/feed-from-historical")
async def feed_from_historical(num_hours: int = 1, background_tasks: BackgroundTasks = None):
    """Feed next rows from historical dataset into sliding window"""
    try:
        if not predictor.is_initialized:
            raise HTTPException(status_code=400, detail="System not initialized")
        
        # Get current window end time
        window_data = predictor.get_window_data()
        current_end = pd.to_datetime(window_data['datetime'].iloc[-1])
        
        # Load historical data
        df = pd.read_csv("data/historical_solar_data.csv")
        
        # Normalize datetime column
        if 'datetime' not in df.columns:
            for col in ["timestamp", "time"]:
                if col in df.columns:
                    df["datetime"] = pd.to_datetime(df[col])
                    break
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Find rows after current window end
        next_rows = df[df['datetime'] > current_end].head(num_hours)
        
        if len(next_rows) == 0:
            return {
                "status": "no_more_data",
                "message": "No more historical data available after current window",
                "current_end": current_end.isoformat()
            }
        
        # Add measurements one by one
        results = []
        for _, row in next_rows.iterrows():
            result = predictor.add_measurement(
                timestamp=row['datetime'].isoformat(),
                power_W=float(row['Power(W)']),
                weather_data=None
            )
            results.append(result)
            
            if result['status'] == 'updated':
                system_state['total_measurements'] += 1
        
        successful = sum(1 for r in results if r['status'] == 'updated')
        
        # Get updated predictions
        predictions = predictor.get_current_predictions()
        
        # Trigger optimization if enabled
        if optimizer.is_auto_optimization_enabled and background_tasks:
            start_index = system_state['total_measurements']
            background_tasks.add_task(
                on_prediction_updated,
                predictions['predictions_W'],
                pd.to_datetime(next_rows.iloc[-1]['datetime']),
                start_index
            )
        
        logger.info(f"✓ Fed {successful} rows from historical data")
        
        return {
            "status": "success",
            "rows_added": successful,
            "total_attempted": len(next_rows),
            "new_window_end": predictor.get_window_data()['datetime'].iloc[-1].isoformat(),
            "details": results
        }
        
    except Exception as e:
        logger.error(f"Failed to feed from historical: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset")
def reset_system():
    """Reset system"""
    try:
        predictor.reset()
        optimizer.disable_auto_optimization()
        
        system_state['initialized'] = False
        system_state['auto_optimization_enabled'] = False
        system_state['last_measurement_time'] = None
        system_state['total_measurements'] = 0
        system_state['total_optimizations'] = 0
        
        logger.info("System reset complete")
        
        return {"status": "reset_complete"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Run on API startup"""
    logger.info("="*70)
    logger.info("  Continuous Solar + Battery Optimization API")
    logger.info("  Version 2.1.0 - Simplified Structure")
    logger.info("="*70)
    logger.info("✓ Fixed battery: 100kWh, 25kW, 20-90% SOC")
    logger.info("✓ Fixed tariff: Peak/Day/Off-peak")
    logger.info("✓ Single CSV: data/historical_solar_data.csv")
    logger.info("="*70)
    
    scheduler.start()
    logger.info("✓ Scheduler started")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on API shutdown"""
    logger.info("API server shutting down...")
    
    scheduler.stop()
    
    if predictor.is_initialized:
        predictor._save_state()
        logger.info("✓ State saved")
    
    logger.info("Goodbye!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)