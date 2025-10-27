"""Test individual components"""

print("="*70)
print("  COMPONENT TEST")
print("="*70)

# Test 1: Import modules
print("\n1. Testing imports...")
try:
    import tensorflow as tf
    print(f"   ✓ TensorFlow {tf.__version__}")
except Exception as e:
    print(f"   ✗ TensorFlow: {e}")

try:
    import pandas as pd
    print(f"   ✓ Pandas {pd.__version__}")
except Exception as e:
    print(f"   ✗ Pandas: {e}")

try:
    from pulp import *
    print(f"   ✓ PuLP")
except Exception as e:
    print(f"   ✗ PuLP: {e}")

# Test 2: Load CSV
print("\n2. Testing CSV load...")
try:
    df = pd.read_csv("data/historical_solar_data.csv")
    print(f"   ✓ CSV loaded: {len(df)} rows")
    print(f"   ✓ Columns: {list(df.columns[:5])}...")
    
    # Check required columns
    required = ['Power(W)', 'Load_kW']
    for col in required:
        if col in df.columns:
            print(f"   ✓ Column '{col}' found")
        else:
            print(f"   ✗ Column '{col}' MISSING!")
    
except Exception as e:
    print(f"   ✗ CSV load failed: {e}")

# Test 3: Load models
print("\n3. Testing model load...")
try:
    from core.solar_predictor import SolarPredictor
    predictor = SolarPredictor()
    print(f"   ✓ Solar predictor loaded")
except Exception as e:
    print(f"   ✗ Solar predictor failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Battery optimizer
print("\n4. Testing battery optimizer...")
try:
    from core.battery_optimizer import BatteryOptimizer
    optimizer = BatteryOptimizer()
    print(f"   ✓ Battery optimizer loaded")
    print(f"   ✓ Battery capacity: {optimizer.battery_params['E_capacity']} kWh")
except Exception as e:
    print(f"   ✗ Battery optimizer failed: {e}")

# Test 5: Validator
print("\n5. Testing validator...")
try:
    from core.data_validator import DataValidator
    validator = DataValidator()
    is_valid, info = validator.validate_historical_data()
    if is_valid:
        print(f"   ✓ CSV validation passed")
        print(f"   ✓ Rows: {info['rows']}")
        print(f"   ✓ Mean solar: {info['mean_solar_W']} W")
        print(f"   ✓ Mean load: {info['mean_load_kW']} kW")
    else:
        print(f"   ✗ CSV validation failed: {info['issues']}")
except Exception as e:
    print(f"   ✗ Validator failed: {e}")

print("\n" + "="*70)
print("  TEST COMPLETE")
print("="*70)