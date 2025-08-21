"""
Epic 1 Integration Helper Functions
==================================

Provides helper functions for integrating Epic 1 features
with the existing trading system architecture.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

# Import Epic 1 components with fallback
try:
    from indicators.stoch_rsi_enhanced import StochRSIIndicator
    from indicators.volume_analysis import VolumeConfirmationSystem
    from src.services.timeframe.MultiTimeframeValidator import MultiTimeframeValidator
    from src.components.signal_integration_enhanced import EnhancedSignalIntegration
    EPIC1_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Epic 1 components not available: {e}")
    EPIC1_AVAILABLE = False

logger = logging.getLogger(__name__)

# Global Epic 1 component instances
epic1_components = {
    'multi_timeframe_validator': None,
    'volume_confirmation_system': None,
    'enhanced_signal_integration': None,
    'initialized': False
}


def initialize_epic1_components() -> bool:
    """Initialize Epic 1 components with proper error handling."""
    global epic1_components
    
    if not EPIC1_AVAILABLE:
        logger.warning("Epic 1 components not available, using Epic 0 compatibility mode")
        return False
    
    try:
        # Initialize Multi-timeframe Validator
        epic1_components['multi_timeframe_validator'] = MultiTimeframeValidator({
            'timeframes': ['15m', '1h', '1d'],
            'enableRealTimeValidation': True,
            'consensusThreshold': 0.75,
            'enablePerformanceTracking': True
        })
        
        # Initialize Volume Confirmation System
        epic1_components['volume_confirmation_system'] = VolumeConfirmationSystem({
            'confirmation_threshold': 1.2,
            'volume_ma_period': 20,
            'enable_relative_volume': True
        })
        
        # Initialize Enhanced Signal Integration
        epic1_components['enhanced_signal_integration'] = EnhancedSignalIntegration({
            'enableMultiTimeframeValidation': True,
            'requireTimeframeConsensus': True,
            'adaptiveSignalStrength': True
        })
        
        epic1_components['initialized'] = True
        logger.info("✅ Epic 1 components initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Epic 1 components: {e}")
        logger.warning("Continuing with Epic 0 compatibility mode")
        return False


def calculate_enhanced_signal_data(symbol: str, data: pd.DataFrame, data_manager) -> Dict[str, Any]:
    """Calculate enhanced signal data using Epic 1 features."""
    try:
        result = {
            'epic1_features': {
                'dynamic_stochrsi': {},
                'volume_confirmation': {},
                'signal_quality': {},
                'multi_timeframe': {}
            },
            'legacy_compatibility': {},
            'integration_status': {
                'epic1_enabled': EPIC1_AVAILABLE,
                'components_initialized': epic1_components['initialized']
            }
        }
        
        # Enhanced StochRSI with dynamic bands
        try:
            if EPIC1_AVAILABLE:
                stoch_rsi = StochRSIIndicator()
                current_signals = stoch_rsi.get_current_signals(data['close'])
                
                # Calculate adaptive bands based on volatility
                volatility = data['close'].rolling(window=20).std().iloc[-1] if len(data) >= 20 else 0
                base_volatility = data['close'].rolling(window=min(100, len(data))).std().mean()
                volatility_ratio = volatility / base_volatility if base_volatility > 0 else 1.0
                
                # Adjust bands dynamically
                adaptive_lower = max(10, min(30, 20 * volatility_ratio))
                adaptive_upper = min(90, max(70, 80 * (2 - volatility_ratio)))
                
                result['epic1_features']['dynamic_stochrsi'] = {
                    **current_signals['stochRSI'],
                    'adaptive_lower_band': adaptive_lower,
                    'adaptive_upper_band': adaptive_upper,
                    'volatility_ratio': volatility_ratio,
                    'band_adjustment': 'dynamic',
                    'enhancement_active': True
                }
            else:
                result['epic1_features']['dynamic_stochrsi'] = {
                    'enhancement_active': False,
                    'fallback_mode': 'epic0_compatibility'
                }
                
        except Exception as e:
            logger.warning(f"Enhanced StochRSI calculation failed: {e}")
            result['epic1_features']['dynamic_stochrsi'] = {'error': str(e), 'enhancement_active': False}
        
        # Volume confirmation analysis
        try:
            volume_analysis = calculate_volume_confirmation(data, symbol)
            result['epic1_features']['volume_confirmation'] = volume_analysis
        except Exception as e:
            logger.warning(f"Volume confirmation failed: {e}")
            result['epic1_features']['volume_confirmation'] = {'error': str(e)}
        
        # Multi-timeframe validation
        try:
            timeframes_data = get_basic_timeframe_data(symbol, data_manager)
            result['epic1_features']['multi_timeframe'] = timeframes_data
        except Exception as e:
            logger.warning(f"Multi-timeframe analysis failed: {e}")
            result['epic1_features']['multi_timeframe'] = {'error': str(e)}
        
        # Signal quality metrics
        try:
            quality_metrics = calculate_signal_quality_metrics(symbol, data_manager)
            result['epic1_features']['signal_quality'] = quality_metrics
        except Exception as e:
            logger.warning(f"Signal quality calculation failed: {e}")
            result['epic1_features']['signal_quality'] = {'error': str(e)}
        
        # Legacy compatibility layer
        if result['epic1_features']['dynamic_stochrsi'].get('enhancement_active'):
            stoch_data = result['epic1_features']['dynamic_stochrsi']
            result['legacy_compatibility'] = {
                'signal': stoch_data.get('signal', 0),
                'strength': stoch_data.get('strength', 0),
                'status': stoch_data.get('condition', 'NEUTRAL'),
                'k': stoch_data.get('k'),
                'd': stoch_data.get('d')
            }
        else:
            # Fallback to basic calculation
            result['legacy_compatibility'] = calculate_basic_stochrsi_signals(data)
        
        return result
        
    except Exception as e:
        logger.error(f"Error calculating enhanced signal data: {e}")
        return {
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'epic1_features': {},
            'legacy_compatibility': {}
        }


def calculate_basic_stochrsi_signals(data: pd.DataFrame) -> Dict[str, Any]:
    """Calculate basic StochRSI signals for Epic 0 compatibility."""
    try:
        from indicator import StochRSI  # Assuming this is the original indicator
        
        # Basic StochRSI calculation
        k, d = StochRSI(data['close'], 14, 14, 3, 3)
        
        if len(k) > 0 and len(d) > 0:
            latest_k = k.iloc[-1] if not pd.isna(k.iloc[-1]) else 50
            latest_d = d.iloc[-1] if not pd.isna(d.iloc[-1]) else 50
            
            # Basic signal logic
            signal = 1 if (latest_k > latest_d and latest_k < 20) else 0
            strength = min(abs(latest_k - 20) / 20, 1.0) if latest_k < 20 else 0
            status = 'OVERSOLD' if latest_k < 20 else 'NORMAL'
            
            return {
                'signal': signal,
                'strength': strength,
                'status': status,
                'k': latest_k,
                'd': latest_d,
                'fallback_mode': True
            }
    except Exception as e:
        logger.warning(f"Basic StochRSI calculation failed: {e}")
    
    return {
        'signal': 0,
        'strength': 0,
        'status': 'UNKNOWN',
        'k': None,
        'd': None,
        'fallback_mode': True,
        'error': 'calculation_failed'
    }


def calculate_volume_confirmation(data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """Calculate volume confirmation analysis."""
    try:
        if 'volume' not in data.columns or data['volume'].isna().all():
            return {
                'volume_confirmed': False,
                'reason': 'Volume data not available',
                'volume_ratio': 0,
                'analysis_quality': 'poor'
            }
        
        # Calculate volume metrics
        current_volume = data['volume'].iloc[-1]
        if pd.isna(current_volume) or current_volume == 0:
            return {
                'volume_confirmed': False,
                'reason': 'Current volume data invalid',
                'volume_ratio': 0,
                'analysis_quality': 'poor'
            }
        
        # Volume moving average
        volume_ma_period = min(20, len(data))
        volume_ma = data['volume'].rolling(window=volume_ma_period).mean().iloc[-1]
        volume_ratio = current_volume / volume_ma if volume_ma > 0 else 0
        
        # Enhanced volume analysis
        volume_std = data['volume'].rolling(window=volume_ma_period).std().iloc[-1]
        relative_volume = (current_volume - volume_ma) / volume_std if volume_std > 0 else 0
        
        # Volume strength classification
        if relative_volume > 2:
            volume_strength = 'very_high'
        elif relative_volume > 1:
            volume_strength = 'high'
        elif relative_volume > 0:
            volume_strength = 'normal'
        elif relative_volume > -1:
            volume_strength = 'low'
        else:
            volume_strength = 'very_low'
        
        # Volume confirmation logic
        confirmation_threshold = 1.2
        volume_confirmed = bool(volume_ratio >= confirmation_threshold)  # Convert np.bool_ to Python bool
        
        # Volume trend analysis
        volume_trend = 'neutral'
        if len(data) >= 5:
            recent_volumes = data['volume'].tail(5)
            if len(recent_volumes) >= 3:
                volume_slope = (recent_volumes.iloc[-1] - recent_volumes.iloc[0]) / len(recent_volumes)
                if volume_slope > volume_ma * 0.1:
                    volume_trend = 'increasing'
                elif volume_slope < -volume_ma * 0.1:
                    volume_trend = 'decreasing'
        
        # Analysis quality assessment
        valid_volume_data = data['volume'].dropna()
        data_completeness = len(valid_volume_data) / len(data) if len(data) > 0 else 0
        
        if data_completeness > 0.95:
            analysis_quality = 'excellent'
        elif data_completeness > 0.9:
            analysis_quality = 'good'
        elif data_completeness > 0.8:
            analysis_quality = 'fair'
        else:
            analysis_quality = 'poor'
        
        return {
            'volume_confirmed': volume_confirmed,
            'volume_ratio': float(volume_ratio),
            'current_volume': int(current_volume),
            'volume_ma': float(volume_ma),
            'relative_volume': float(relative_volume),
            'volume_strength': volume_strength,
            'volume_trend': volume_trend,
            'confirmation_threshold': confirmation_threshold,
            'analysis_quality': analysis_quality,
            'data_completeness': float(data_completeness),
            'analysis_timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error calculating volume confirmation: {e}")
        return {
            'volume_confirmed': False,
            'error': str(e),
            'analysis_quality': 'failed',
            'analysis_timestamp': datetime.now().isoformat()
        }


def get_basic_timeframe_data(symbol: str, data_manager) -> Dict[str, Any]:
    """Get basic multi-timeframe data for analysis."""
    try:
        timeframes = ['15m', '1h', '1d']
        timeframe_data = {}
        
        for tf in timeframes:
            try:
                tf_data = data_manager.get_historical_data(symbol, tf, limit=50)
                if not tf_data.empty:
                    latest_price = tf_data['close'].iloc[-1]
                    price_change = tf_data['close'].pct_change().iloc[-1]
                    volatility = tf_data['close'].pct_change().std()
                    
                    # Simple trend analysis
                    sma_period = min(20, len(tf_data))
                    sma_20 = tf_data['close'].rolling(window=sma_period).mean().iloc[-1]
                    trend_direction = 'bullish' if latest_price > sma_20 else 'bearish'
                    trend_strength = abs(latest_price - sma_20) / sma_20 if sma_20 > 0 else 0
                    
                    timeframe_data[tf] = {
                        'latest_price': float(latest_price),
                        'price_change': float(price_change * 100) if not pd.isna(price_change) else 0,
                        'volatility': float(volatility) if not pd.isna(volatility) else 0,
                        'trend_direction': trend_direction,
                        'trend_strength': float(trend_strength),
                        'data_points': len(tf_data),
                        'sma_20': float(sma_20)
                    }
            except Exception as e:
                logger.warning(f"Could not get data for {tf}: {e}")
                timeframe_data[tf] = {'error': str(e)}
        
        # Calculate alignment score
        valid_timeframes = [tf for tf, data in timeframe_data.items() if 'error' not in data]
        if len(valid_timeframes) >= 2:
            bullish_count = sum(1 for tf in valid_timeframes 
                              if timeframe_data[tf].get('trend_direction') == 'bullish')
            alignment_score = bullish_count / len(valid_timeframes)
            
            if alignment_score >= 0.75:
                alignment_status = 'strong_bullish'
            elif alignment_score >= 0.5:
                alignment_status = 'weak_bullish'
            elif alignment_score >= 0.25:
                alignment_status = 'weak_bearish'
            else:
                alignment_status = 'strong_bearish'
        else:
            alignment_score = 0.5
            alignment_status = 'insufficient_data'
        
        return {
            'timeframes': timeframe_data,
            'alignment_score': float(alignment_score),
            'alignment_status': alignment_status,
            'valid_timeframes': len(valid_timeframes),
            'analysis_timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting timeframe data: {e}")
        return {
            'error': str(e),
            'analysis_timestamp': datetime.now().isoformat()
        }


def calculate_signal_quality_metrics(symbol: str, data_manager) -> Dict[str, Any]:
    """Calculate comprehensive signal quality metrics."""
    try:
        # Get recent data for quality analysis
        recent_data = data_manager.get_historical_data(symbol, '1Min', limit=100)
        if recent_data.empty:
            return {'error': 'No data for quality analysis'}
        
        # Price analysis
        price_changes = recent_data['close'].pct_change().dropna()
        price_volatility = price_changes.std() if len(price_changes) > 0 else 0
        price_trend_consistency = abs(price_changes.mean()) if len(price_changes) > 0 else 0
        
        # Volume analysis (if available)
        volume_consistency = 0
        if 'volume' in recent_data.columns and not recent_data['volume'].isna().all():
            volume_mean = recent_data['volume'].mean()
            volume_std = recent_data['volume'].std()
            volume_consistency = 1 - (volume_std / volume_mean) if volume_mean > 0 else 0
            volume_consistency = max(0, min(1, volume_consistency))  # Clamp to [0,1]
        
        # Data quality assessment
        data_completeness = len(recent_data.dropna()) / len(recent_data)
        data_freshness = 1.0  # Assume fresh data for now
        
        # Signal reliability estimation
        base_reliability = 0.75
        
        # Adjust reliability based on volatility
        volatility_penalty = min(price_volatility * 5, 0.3)  # Cap penalty at 30%
        
        # Adjust reliability based on volume consistency
        volume_bonus = volume_consistency * 0.1 if volume_consistency > 0.5 else 0
        
        signal_reliability = max(0.1, base_reliability - volatility_penalty + volume_bonus)
        
        # Calculate overall quality score
        quality_score = (
            (1 - min(price_volatility * 10, 1)) * 0.25 +  # Volatility (25%)
            volume_consistency * 0.20 +                    # Volume consistency (20%)
            data_completeness * 0.25 +                     # Data completeness (25%)
            signal_reliability * 0.20 +                    # Signal reliability (20%)
            data_freshness * 0.10                          # Data freshness (10%)
        )
        
        return {
            'overall_quality_score': float(quality_score),
            'quality_grade': get_quality_grade(quality_score),
            'components': {
                'price_volatility': float(price_volatility),
                'price_trend_consistency': float(price_trend_consistency),
                'volume_consistency': float(volume_consistency),
                'data_completeness': float(data_completeness),
                'data_freshness': float(data_freshness),
                'signal_reliability': float(signal_reliability)
            },
            'recommendations': generate_quality_recommendations(quality_score, price_volatility, volume_consistency),
            'analysis_timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error calculating signal quality metrics: {e}")
        return {
            'error': str(e),
            'analysis_timestamp': datetime.now().isoformat()
        }


def get_quality_grade(score: float) -> str:
    """Convert quality score to letter grade."""
    if score >= 0.9:
        return 'A+'
    elif score >= 0.8:
        return 'A'
    elif score >= 0.7:
        return 'B'
    elif score >= 0.6:
        return 'C'
    elif score >= 0.5:
        return 'D'
    else:
        return 'F'


def generate_quality_recommendations(quality_score: float, volatility: float, volume_consistency: float) -> List[str]:
    """Generate recommendations based on signal quality analysis."""
    recommendations = []
    
    if quality_score < 0.6:
        recommendations.append("Consider waiting for higher quality signals")
    
    if volatility > 0.05:
        recommendations.append("High volatility detected - use smaller position sizes")
    
    if volume_consistency < 0.5:
        recommendations.append("Volume patterns are inconsistent - verify with additional indicators")
    
    if quality_score >= 0.8:
        recommendations.append("High quality signal - good entry opportunity")
    
    if quality_score < 0.4:
        recommendations.append("Very low signal quality - avoid trading")
    
    return recommendations


def integrate_epic1_with_websocket(websocket_data: Dict[str, Any], data_manager) -> Dict[str, Any]:
    """Integrate Epic 1 enhancements with WebSocket data streams."""
    try:
        enhanced_data = websocket_data.copy()
        
        # Enhance ticker signals with Epic 1 features
        if 'ticker_signals' in enhanced_data:
            for symbol, signal_data in enhanced_data['ticker_signals'].items():
                try:
                    # Get recent data for Epic 1 analysis
                    recent_data = data_manager.get_historical_data(symbol, '1Min', limit=50)
                    
                    if not recent_data.empty:
                        # Add Epic 1 enhancements
                        epic1_enhancements = calculate_enhanced_signal_data(symbol, recent_data, data_manager)
                        
                        # Merge Epic 1 features with existing signal data
                        signal_data['epic1_enhancements'] = epic1_enhancements['epic1_features']
                        signal_data['signal_quality'] = epic1_enhancements['epic1_features']['signal_quality']
                        
                        # Update signal strength if Epic 1 validation is available
                        if epic1_enhancements['epic1_features']['dynamic_stochrsi'].get('enhancement_active'):
                            enhanced_strength = epic1_enhancements['epic1_features']['dynamic_stochrsi'].get('strength', 0)
                            if enhanced_strength > signal_data.get('strength', 0):
                                signal_data['strength'] = enhanced_strength
                                signal_data['enhancement_applied'] = True
                
                except Exception as e:
                    logger.debug(f"Could not enhance signal for {symbol}: {e}")
                    signal_data['epic1_enhancements'] = {'error': str(e)}
        
        # Add Epic 1 metadata
        enhanced_data['epic1_metadata'] = {
            'integration_active': EPIC1_AVAILABLE and epic1_components['initialized'],
            'enhancement_timestamp': datetime.now().isoformat(),
            'features_enabled': {
                'dynamic_stochrsi': True,
                'volume_confirmation': True,
                'multi_timeframe_validation': True,
                'signal_quality_metrics': True
            }
        }
        
        return enhanced_data
        
    except Exception as e:
        logger.error(f"Error integrating Epic 1 with WebSocket data: {e}")
        # Return original data if enhancement fails
        websocket_data['epic1_integration_error'] = str(e)
        return websocket_data


def get_epic1_status() -> Dict[str, Any]:
    """Get current Epic 1 integration status."""
    return {
        'epic1_available': EPIC1_AVAILABLE,
        'components_initialized': epic1_components['initialized'],
        'components': {
            'multi_timeframe_validator': epic1_components['multi_timeframe_validator'] is not None,
            'volume_confirmation_system': epic1_components['volume_confirmation_system'] is not None,
            'enhanced_signal_integration': epic1_components['enhanced_signal_integration'] is not None
        },
        'last_check': datetime.now().isoformat()
    }