"""
Data Validator - Single CSV Only
"""

import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataValidator:
    """Validates the single CSV file"""
    
    def validate_historical_data(self, csv_path: str = "data/historical_solar_data.csv") -> tuple:
        """Validate CSV file"""
        try:
            df = pd.read_csv(csv_path)
            issues = []
            
            # Check datetime
            datetime_cols = ['timestamp', 'datetime', 'time']
            if not any(col in df.columns for col in datetime_cols):
                issues.append(f"Missing datetime column. Need one of: {datetime_cols}")
            
            # Check Power(W)
            if 'Power(W)' not in df.columns:
                issues.append("Missing 'Power(W)' column")
            
            # Check Load_kW
            if 'Load_kW' not in df.columns:
                issues.append("Missing 'Load_kW' column")
            
            # Check minimum rows
            if len(df) < 48:
                issues.append(f"Need at least 48 hours. Found {len(df)} rows")
            
            if issues:
                return False, {'valid': False, 'issues': issues}
            
            return True, {
                'valid': True,
                'rows': len(df),
                'mean_solar_W': round(df['Power(W)'].mean(), 2),
                'mean_load_kW': round(df['Load_kW'].mean(), 2)
            }
            
        except Exception as e:
            return False, {'valid': False, 'issues': [str(e)]}
    
    def validate_all_files(self) -> dict:
        """Validate all files"""
        print("\n" + "="*70)
        print("  DATA VALIDATION REPORT")
        print("="*70 + "\n")
        
        valid, info = self.validate_historical_data()
        
        if valid:
            print(f"✓ Historical Data: VALID")
            print(f"  Rows: {info['rows']}")
            print(f"  Mean solar: {info['mean_solar_W']} W")
            print(f"  Mean load: {info['mean_load_kW']} kW\n")
        else:
            print(f"✗ Historical Data: INVALID")
            for issue in info['issues']:
                print(f"  - {issue}")
            print()
        
        print("✓ Battery: FIXED (100kWh, 25kW, 20-90%)")
        print("✓ Tariff: FIXED (Peak/Day/Off-peak)\n")
        
        print("="*70)
        print("  ✅ READY" if valid else "  ❌ FIX ISSUES")
        print("="*70 + "\n")
        
        return {'all_valid': valid}


if __name__ == "__main__":
    validator = DataValidator()
    validator.validate_all_files()