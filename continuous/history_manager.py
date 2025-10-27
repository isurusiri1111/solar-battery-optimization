"""
History Manager
Manages historical records of predictions and optimizations
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoryManager:
    """Manages historical data storage and retrieval"""
    
    def __init__(self, history_dir: str = "data/history"):
        self.history_dir = Path(history_dir)
        self.pred_dir = self.history_dir / "predictions"
        self.opt_dir = self.history_dir / "optimizations"
        
        self.pred_dir.mkdir(parents=True, exist_ok=True)
        self.opt_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("History manager initialized")
    
    def save_prediction(self, predictions: Dict, timestamp: datetime):
        """Save prediction to history"""
        try:
            filename = f"pred_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.json"
            filepath = self.pred_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(predictions, f, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Failed to save prediction: {e}")
    
    def get_recent_predictions(self, limit: int = 10) -> List[Dict]:
        """Get recent predictions"""
        try:
            files = sorted(self.pred_dir.glob("pred_*.json"), reverse=True)[:limit]
            
            predictions = []
            for filepath in files:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    predictions.append(data)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Failed to get predictions: {e}")
            return []