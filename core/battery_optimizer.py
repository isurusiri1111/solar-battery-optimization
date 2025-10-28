import pandas as pd
import numpy as np
from pathlib import Path
from pulp import LpVariable, LpProblem, LpMinimize, LpMaximize, LpStatus, value, lpSum, PULP_CBC_CMD

from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BatteryOptimizer:
    """Optimizes battery schedule using MILP with fixed parameters"""
    
    def __init__(self):
        # ✅ FIXED BATTERY PARAMETERS
        self.battery_params = {
            "E_capacity": 12.0,      # kWh
            "SOC_min": 20.0,         # %
            "SOC_max": 90.0,         # %
            "SOC_initial": 50.0,     # %
            "P_charge_max": 3.0,     # kW
            "P_discharge_max": 3.0,  # kW
            "eta_charge": 0.95,
            "eta_discharge": 0.95,
        }
        
        logger.info("Battery optimizer initialized")
        logger.info(f"  Capacity: {self.battery_params['E_capacity']} kWh")
        logger.info(f"  Power limits: {self.battery_params['P_charge_max']} kW")
    
    def get_tariff_for_hour(self, hour: int) -> tuple:
        """Get tariff for given hour"""
        # Peak: 18:30-22:30 (hours 18.5 to 22.5)
        if 18 <= hour < 23:
            if hour == 18 or (19 <= hour < 22) or (hour == 22):
                return (54.00, 45.80)
        
        # Off-peak: 22:30-05:30
        if hour >= 23 or hour < 6:
            return (13.00, 13.00)
        
        # Day: 05:30-18:30
        return (25.00, 25.00)
    
    def optimize(
        self,
        solar_forecast_W: List[float],
        load_demand_kW: List[float],
        time_horizon: int = 24,
        start_hour: int = 0
    ) -> Dict:
        """Run MILP optimization"""
        try:
            # Basic validation and sanitization
            if solar_forecast_W is None or load_demand_kW is None:
                raise ValueError("Missing inputs: solar_forecast_W or load_demand_kW is None")
            if len(solar_forecast_W) < time_horizon or len(load_demand_kW) < time_horizon:
                raise ValueError(f"Insufficient horizon: got solar={len(solar_forecast_W)}, load={len(load_demand_kW)}, need {time_horizon}")

            # Convert solar to kW and sanitize inputs (replace NaN/inf)
            solar_series = pd.Series(solar_forecast_W[:time_horizon], dtype='float64')
            load_series = pd.Series(load_demand_kW[:time_horizon], dtype='float64')
            solar_series = solar_series.replace([np.inf, -np.inf], np.nan).fillna(0.0)
            load_series = load_series.replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(0.0)
            solar_forecast_kW = (solar_series / 1000.0).clip(lower=0.0).tolist()
            load_demand_kW = load_series.clip(lower=0.0).tolist()
            
            # Get tariff schedule
            tariff_import = []
            tariff_export = []
            for i in range(time_horizon):
                hour = (start_hour + i) % 24
                imp, exp = self.get_tariff_for_hour(hour)
                tariff_import.append(imp)
                tariff_export.append(exp)
            
            # Battery parameters
            bp = self.battery_params
            E_cap = bp['E_capacity']
            SOC_min = bp['SOC_min']
            SOC_max = bp['SOC_max']
            SOC_init = bp['SOC_initial']
            P_charge_max = bp['P_charge_max']
            P_discharge_max = bp['P_discharge_max']
            eta_charge = bp['eta_charge']
            eta_discharge = bp['eta_discharge']
            
            # Create optimization problem
            prob = LpProblem("Battery_Optimization", LpMinimize)
            T = range(time_horizon)
            
            # Decision variables
            P_charge = LpVariable.dicts("P_charge", T, lowBound=0, upBound=P_charge_max)
            P_discharge = LpVariable.dicts("P_discharge", T, lowBound=0, upBound=P_discharge_max)
            P_import = LpVariable.dicts("P_import", T, lowBound=0)
            P_export = LpVariable.dicts("P_export", T, lowBound=0)
            SOC = LpVariable.dicts("SOC", T, lowBound=SOC_min, upBound=SOC_max)
            b_charge = LpVariable.dicts("b_charge", T, cat='Binary')
            b_discharge = LpVariable.dicts("b_discharge", T, cat='Binary')
            
            # Objective: Minimize cost
            prob += lpSum([
                tariff_import[t] * P_import[t] - tariff_export[t] * P_export[t]
                for t in T
            ])
            
            # Constraints
            for t in T:
                # Power balance
                prob += (solar_forecast_kW[t] + P_discharge[t] - P_charge[t] + P_import[t] 
                        == load_demand_kW[t] + P_export[t])
                
                # Battery SOC
                if t == 0:
                    # Avoid dividing an LpVariable by a float (PuLP doesn't support that) - multiply by reciprocal instead
                    prob += SOC[t] == SOC_init + (eta_charge * P_charge[t] - P_discharge[t] * (1.0 / eta_discharge)) * 100 / E_cap
                else:
                    prob += SOC[t] == SOC[t-1] + (eta_charge * P_charge[t] - P_discharge[t] * (1.0 / eta_discharge)) * 100 / E_cap
                
                # Exclusivity
                prob += b_charge[t] + b_discharge[t] <= 1
                prob += P_charge[t] <= P_charge_max * b_charge[t]
                prob += P_discharge[t] <= P_discharge_max * b_discharge[t]
            
            # Solve (use bundled CBC solver). Enable logs and keep files for debugging.
            logs_dir = Path("logs")
            try:
                logs_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            log_path = str((logs_dir / "cbc_solver.log").resolve())
            solver = PULP_CBC_CMD(msg=1, keepFiles=True, logPath=log_path, threads=1)
            status = prob.solve(solver)

            # Fallback attempt if not solved optimally
            status_str = LpStatus.get(prob.status, str(prob.status))
            if status_str not in ("Optimal",):
                fallback_log = str((logs_dir / "cbc_solver_fallback.log").resolve())
                solver_fb = PULP_CBC_CMD(
                    msg=1,
                    keepFiles=True,
                    logPath=fallback_log,
                    threads=1,
                    presolve=False,
                    cuts=False,
                    timeLimit=60
                )
                status = prob.solve(solver_fb)
            
            # Extract results
            schedule = []
            for t in T:
                schedule.append({
                    'hour': t,
                    'hour_of_day': (start_hour + t) % 24,
                    'solar_kW': round(solar_forecast_kW[t], 3),
                    'load_kW': round(load_demand_kW[t], 3),
                    'P_charge': round(value(P_charge[t]), 3),
                    'P_discharge': round(value(P_discharge[t]), 3),
                    'P_import': round(value(P_import[t]), 3),
                    'P_export': round(value(P_export[t]), 3),
                    'SOC': round(value(SOC[t]), 2),
                    'tariff_import': tariff_import[t],
                    'tariff_export': tariff_export[t]
                })
            
            total_cost = value(prob.objective)
            
            return {
                'status': LpStatus[prob.status],
                'total_cost': round(total_cost, 2),
                'total_import_kWh': round(sum(value(P_import[t]) for t in T), 2),
                'total_export_kWh': round(sum(value(P_export[t]) for t in T), 2),
                'schedule': schedule,
                'battery_params': self.battery_params
            }
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            # Try to surface CBC log if available
            try:
                with open("logs/cbc_solver.log", "r", encoding="utf-8", errors="ignore") as f:
                    tail = f.read()[-4000:]
                logger.error(f"CBC log tail:\n{tail}")
            except Exception:
                pass
            raise