import yaml
from pydantic import BaseModel, Field
from typing import Dict, Any

class StochRSIParams(BaseModel):
    enabled: bool
    lower_band: int
    upper_band: int
    K: int
    D: int
    rsi_length: int
    stoch_length: int
    source: str
    dynamic_bands_enabled: bool = True
    atr_period: int = 14
    atr_sensitivity: float = 0.7
    band_adjustment_factor: float = 0.3
    min_band_width: int = 10
    max_band_width: int = 50

class StochParams(BaseModel):
    enabled: bool
    lower_band: int
    upper_band: int
    K_Length: int
    smooth_K: int
    smooth_D: int

class EMAParams(BaseModel):
    enabled: bool
    ema_period: int
    fast_period: int
    slow_period: int
    source: str
    smoothing: int

class Indicators(BaseModel):
    stochRSI: StochRSIParams
    stoch: StochParams
    EMA: EMAParams

class RiskManagement(BaseModel):
    use_atr_stop_loss: bool
    atr_period: int
    atr_multiplier: float
    use_atr_position_sizing: bool

class VolumeConfirmation(BaseModel):
    enabled: bool = True
    volume_period: int = 20
    relative_volume_period: int = 50
    volume_confirmation_threshold: float = 1.2
    min_volume_ratio: float = 1.0
    profile_periods: int = 100
    require_volume_confirmation: bool = True

class Config(BaseModel):
    start_date: str
    end_date: str
    timeframe: str
    candle_lookback_period: int
    investment_amount: int
    max_trades_active: int
    trade_capital_percent: int
    stop_loss: float
    trailing_stop: float
    activate_trailing_stop_loss_at: float
    limit_price: float
    exchange: str
    sleep_time_between_trades: int
    extended_hours: bool
    strategy: str
    indicators: Indicators
    risk_management: RiskManagement
    volume_confirmation: VolumeConfirmation = VolumeConfirmation()

def load_config(path: str = 'config/config.yml') -> Config:
    with open(path, 'r') as f:
        config_data = yaml.safe_load(f)
    return Config(**config_data)

config = load_config()