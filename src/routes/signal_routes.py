"""
Enhanced Signal Routes for Epic 1 Integration
============================================

Provides API endpoints for:
- Epic 1 enhanced signal data streaming
- Dynamic StochRSI with adaptive bands
- Volume confirmation system
- Multi-timeframe validation
- Signal quality metrics
- Historical signal data
- Performance metrics
- Signal filtering and export
- Real-time signal updates
"""

from flask import Flask, request, jsonify, render_template, Blueprint
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import Epic 1 components
try:
    from indicators.stoch_rsi_enhanced import calculate_stoch_rsi_for_chart, StochRSIIndicator
    from indicators.volume_analysis import VolumeConfirmationSystem
    from src.services.timeframe.MultiTimeframeValidator import MultiTimeframeValidator
    from src.components.signal_integration_enhanced import EnhancedSignalIntegration
    EPIC1_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Epic 1 components not available: {e}")
    EPIC1_AVAILABLE = False

logger = logging.getLogger(__name__)

# Create blueprint for enhanced signal routes
signal_bp = Blueprint('enhanced_signals', __name__, url_prefix='/api/signals')

# Thread pool for async operations
thread_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="SignalWorker")

# Global Epic 1 instances
epic1_components = {
    'multi_timeframe_validator': None,
    'volume_confirmation_system': None,
    'enhanced_signal_integration': None
}

class SignalRoutesHandler:
    """Handles all signal-related API routes"""
    
    def __init__(self, app: Flask, data_manager, bot_manager=None, websocket_service=None):
        self.app = app
        self.data_manager = data_manager
        self.bot_manager = bot_manager
        self.websocket_service = websocket_service
        
        # Signal storage
        self.signal_history = []
        self.signal_performance = {}
        self.signal_cache = {}
        
        # Configuration
        self.max_history_size = 10000
        self.cache_ttl = 300  # 5 minutes
        
        self.register_routes()
        logger.info("Signal routes handler initialized")
    
    def register_routes(self):
        """Register all signal-related routes"""
        
        # Main dashboard route
        @self.app.route('/signals/dashboard')
        def signal_dashboard():
            """Render the enhanced signal dashboard"""
            return render_template('enhanced_signal_dashboard.html')
        
        # Signal data endpoints
        @self.app.route('/api/signals/current')
        def get_current_signals():
            """Get current signals for all active symbols"""
            try:
                signals = self.get_current_signal_data()
                return jsonify({
                    'success': True,
                    'signals': signals,
                    'timestamp': datetime.now().isoformat(),
                    'count': len(signals)
                })
            except Exception as e:
                logger.error(f"Error getting current signals: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/signals/history')
        def get_signal_history():
            """Get historical signal data with filtering"""
            try:
                # Parse query parameters
                symbol = request.args.get('symbol', 'all')
                signal_type = request.args.get('type', 'all')
                limit = int(request.args.get('limit', 100))
                start_date = request.args.get('start_date')
                end_date = request.args.get('end_date')
                min_strength = float(request.args.get('min_strength', 0))
                
                # Filter signal history
                filtered_signals = self.filter_signal_history(
                    symbol=symbol,
                    signal_type=signal_type,
                    limit=limit,
                    start_date=start_date,
                    end_date=end_date,
                    min_strength=min_strength
                )
                
                return jsonify({
                    'success': True,
                    'signals': filtered_signals,
                    'count': len(filtered_signals),
                    'filters': {
                        'symbol': symbol,
                        'type': signal_type,
                        'limit': limit,
                        'min_strength': min_strength
                    }
                })
                
            except Exception as e:
                logger.error(f"Error getting signal history: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/signals/performance')
        def get_signal_performance():
            """Get signal performance metrics"""
            try:
                performance = self.calculate_signal_performance()
                return jsonify({
                    'success': True,
                    'performance': performance,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error getting signal performance: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/signals/export')
        def export_signals():
            """Export signal history as CSV"""
            try:
                # Get filtering parameters
                symbol = request.args.get('symbol', 'all')
                signal_type = request.args.get('type', 'all')
                start_date = request.args.get('start_date')
                end_date = request.args.get('end_date')
                
                # Generate CSV data
                csv_data = self.export_signal_data(
                    symbol=symbol,
                    signal_type=signal_type,
                    start_date=start_date,
                    end_date=end_date
                )
                
                from flask import Response
                return Response(
                    csv_data,
                    mimetype='text/csv',
                    headers={
                        'Content-Disposition': f'attachment; filename=signal_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                    }
                )
                
            except Exception as e:
                logger.error(f"Error exporting signals: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # Signal analysis endpoints
        @self.app.route('/api/signals/analyze/<symbol>')
        def analyze_symbol_signals(symbol):
            """Analyze signals for a specific symbol"""
            try:
                analysis = self.analyze_symbol_performance(symbol)
                return jsonify({
                    'success': True,
                    'symbol': symbol,
                    'analysis': analysis,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error analyzing symbol {symbol}: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/signals/strategies')
        def get_strategy_performance():
            """Get performance metrics by strategy type"""
            try:
                strategies = self.analyze_strategy_performance()
                return jsonify({
                    'success': True,
                    'strategies': strategies,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error getting strategy performance: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # Real-time signal management
        @self.app.route('/api/signals/live', methods=['POST'])
        def add_live_signal():
            """Add a new live signal (for testing or external integration)"""
            try:
                signal_data = request.get_json()
                
                # Validate signal data
                required_fields = ['symbol', 'type', 'strength', 'price']
                for field in required_fields:
                    if field not in signal_data:
                        return jsonify({
                            'success': False,
                            'error': f'Missing required field: {field}'
                        }), 400
                
                # Process and store signal
                processed_signal = self.process_new_signal(signal_data)
                
                # Broadcast via WebSocket if available
                if self.websocket_service:
                    self.websocket_service.websocket_server.broadcast_signal(
                        signal_data['symbol'], 
                        processed_signal
                    )
                
                return jsonify({
                    'success': True,
                    'signal': processed_signal,
                    'message': 'Signal added successfully'
                })
                
            except Exception as e:
                logger.error(f"Error adding live signal: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/signals/batch', methods=['POST'])
        def add_batch_signals():
            """Add multiple signals at once"""
            try:
                signals_data = request.get_json()
                
                if not isinstance(signals_data, list):
                    return jsonify({
                        'success': False,
                        'error': 'Expected list of signals'
                    }), 400
                
                processed_signals = []
                for signal_data in signals_data:
                    try:
                        processed_signal = self.process_new_signal(signal_data)
                        processed_signals.append(processed_signal)
                    except Exception as e:
                        logger.warning(f"Error processing signal: {e}")
                        continue
                
                return jsonify({
                    'success': True,
                    'signals': processed_signals,
                    'count': len(processed_signals),
                    'message': f'Processed {len(processed_signals)} signals'
                })
                
            except Exception as e:
                logger.error(f"Error adding batch signals: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # Signal configuration endpoints
        @self.app.route('/api/signals/config', methods=['GET', 'POST'])
        def signal_config():
            """Get or update signal configuration"""
            if request.method == 'GET':
                return jsonify({
                    'success': True,
                    'config': {
                        'max_history_size': self.max_history_size,
                        'cache_ttl': self.cache_ttl,
                        'websocket_enabled': self.websocket_service is not None,
                        'bot_connected': self.bot_manager is not None
                    }
                })
            else:
                try:
                    config_data = request.get_json()
                    
                    if 'max_history_size' in config_data:
                        self.max_history_size = int(config_data['max_history_size'])
                    
                    if 'cache_ttl' in config_data:
                        self.cache_ttl = int(config_data['cache_ttl'])
                    
                    return jsonify({
                        'success': True,
                        'message': 'Configuration updated successfully'
                    })
                    
                except Exception as e:
                    logger.error(f"Error updating signal config: {e}")
                    return jsonify({
                        'success': False,
                        'error': str(e)
                    }), 500
        
        # Signal statistics endpoint
        @self.app.route('/api/signals/stats')
        def get_signal_stats():
            """Get comprehensive signal statistics"""
            try:
                stats = self.calculate_signal_statistics()
                return jsonify({
                    'success': True,
                    'statistics': stats,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error getting signal stats: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def get_current_signal_data(self) -> List[Dict]:
        """Get current signal data from the trading system"""
        try:
            signals = []
            
            if self.bot_manager:
                # Get tickers from bot manager
                tickers = getattr(self.bot_manager, 'load_tickers', lambda: [])()
                config = getattr(self.bot_manager, 'load_config', lambda: None)()
                
                for symbol in tickers:
                    try:
                        # Get market data
                        data = self.data_manager.get_historical_data(symbol, '1Min', limit=50)
                        if data.empty:
                            continue
                        
                        # Calculate indicators
                        config_dict = self._convert_config_for_indicators(config) if config else {}
                        indicators = self.data_manager.calculate_indicators(data, config_dict)
                        
                        if indicators:
                            # Generate signal
                            signal = self._generate_signal_from_indicators(symbol, indicators)
                            if signal:
                                signals.append(signal)
                                
                    except Exception as e:
                        logger.debug(f"Error getting signal for {symbol}: {e}")
                        continue
            
            return signals
            
        except Exception as e:
            logger.error(f"Error getting current signal data: {e}")
            return []
    
    def _convert_config_for_indicators(self, config) -> Dict:
        """Convert unified config to legacy format"""
        try:
            return {
                'indicators': {
                    'stochRSI': "True" if config.indicators.stochRSI.enabled else "False",
                    'stochRSI_params': {
                        'rsi_length': config.indicators.stochRSI.rsi_length,
                        'stoch_length': config.indicators.stochRSI.stoch_length,
                        'K': config.indicators.stochRSI.K,
                        'D': config.indicators.stochRSI.D,
                        'lower_band': config.indicators.stochRSI.lower_band,
                        'upper_band': config.indicators.stochRSI.upper_band
                    },
                    'EMA': "True" if config.indicators.EMA.enabled else "False",
                    'EMA_params': {
                        'ema_period': config.indicators.EMA.ema_period
                    }
                }
            }
        except Exception:
            return {'indicators': {}}
    
    def _generate_signal_from_indicators(self, symbol: str, indicators: Dict) -> Optional[Dict]:
        """Generate signal data from indicators"""
        try:
            signal_data = {
                'id': f'signal_{symbol}_{int(datetime.now().timestamp())}',
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'type': 'NEUTRAL',
                'strength': 0.5,
                'price': self.data_manager.get_latest_price(symbol) or 0,
                'reason': 'No significant signals',
                'indicators': indicators,
                'metadata': {
                    'source': 'signal_routes',
                    'strategies': []
                }
            }
            
            # Analyze StochRSI
            if 'StochRSI_K' in indicators and 'StochRSI_D' in indicators:
                k = indicators['StochRSI_K']
                d = indicators['StochRSI_D']
                
                if k > d and k < 20:
                    signal_data['type'] = 'BUY'
                    signal_data['strength'] = 0.8
                    signal_data['reason'] = 'StochRSI oversold signal'
                    signal_data['metadata']['strategies'].append('StochRSI')
                elif k < 20:
                    signal_data['type'] = 'OVERSOLD'
                    signal_data['strength'] = 0.6
                    signal_data['reason'] = 'StochRSI oversold condition'
                    signal_data['metadata']['strategies'].append('StochRSI')
            
            # Analyze EMA
            if 'EMA' in indicators and signal_data['price'] > 0:
                ema = indicators['EMA']
                if signal_data['price'] > ema * 1.01:  # Price 1% above EMA
                    if signal_data['type'] == 'BUY':
                        signal_data['strength'] = min(signal_data['strength'] + 0.2, 1.0)
                        signal_data['reason'] += ', EMA bullish'
                    elif signal_data['type'] == 'NEUTRAL':
                        signal_data['type'] = 'BUY'
                        signal_data['strength'] = 0.6
                        signal_data['reason'] = 'EMA bullish signal'
                    signal_data['metadata']['strategies'].append('EMA')
            
            # Only return signal if it's actionable
            if signal_data['type'] != 'NEUTRAL' and signal_data['strength'] > 0.5:
                return signal_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return None
    
    def process_new_signal(self, signal_data: Dict) -> Dict:
        """Process and store a new signal"""
        # Add timestamp if not present
        if 'timestamp' not in signal_data:
            signal_data['timestamp'] = datetime.now().isoformat()
        
        # Add unique ID if not present
        if 'id' not in signal_data:
            signal_data['id'] = f"signal_{signal_data['symbol']}_{int(datetime.now().timestamp())}"
        
        # Add metadata if not present
        if 'metadata' not in signal_data:
            signal_data['metadata'] = {
                'source': 'api',
                'confidence': signal_data.get('strength', 0.5),
                'strategies': []
            }
        
        # Store in history
        self.signal_history.append(signal_data)
        
        # Trim history if needed
        if len(self.signal_history) > self.max_history_size:
            self.signal_history = self.signal_history[-self.max_history_size:]
        
        # Update performance tracking
        self._update_signal_performance(signal_data)
        
        logger.info(f"Processed new signal: {signal_data['symbol']} {signal_data['type']}")
        
        return signal_data
    
    def filter_signal_history(self, symbol='all', signal_type='all', limit=100, 
                             start_date=None, end_date=None, min_strength=0) -> List[Dict]:
        """Filter signal history based on criteria"""
        filtered_signals = list(self.signal_history)
        
        # Filter by symbol
        if symbol != 'all':
            filtered_signals = [s for s in filtered_signals if s.get('symbol') == symbol]
        
        # Filter by signal type
        if signal_type != 'all':
            filtered_signals = [s for s in filtered_signals if s.get('type') == signal_type]
        
        # Filter by strength
        if min_strength > 0:
            filtered_signals = [s for s in filtered_signals if s.get('strength', 0) >= min_strength]
        
        # Filter by date range
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                filtered_signals = [s for s in filtered_signals 
                                  if datetime.fromisoformat(s.get('timestamp', '')) >= start_dt]
            except ValueError:
                logger.warning(f"Invalid start_date format: {start_date}")
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                filtered_signals = [s for s in filtered_signals 
                                  if datetime.fromisoformat(s.get('timestamp', '')) <= end_dt]
            except ValueError:
                logger.warning(f"Invalid end_date format: {end_date}")
        
        # Sort by timestamp (newest first) and limit
        filtered_signals.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return filtered_signals[:limit]
    
    def calculate_signal_performance(self) -> Dict:
        """Calculate overall signal performance metrics"""
        if not self.signal_history:
            return {
                'total_signals': 0,
                'win_rate': 0,
                'avg_strength': 0,
                'best_strategy': None,
                'strategy_performance': {}
            }
        
        total_signals = len(self.signal_history)
        
        # Calculate average strength
        avg_strength = sum(s.get('strength', 0) for s in self.signal_history) / total_signals
        
        # Analyze by strategy
        strategy_stats = {}
        for signal in self.signal_history:
            strategies = signal.get('metadata', {}).get('strategies', [])
            for strategy in strategies:
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = {'count': 0, 'total_strength': 0}
                strategy_stats[strategy]['count'] += 1
                strategy_stats[strategy]['total_strength'] += signal.get('strength', 0)
        
        # Calculate strategy performance
        strategy_performance = {}
        best_strategy = None
        best_avg_strength = 0
        
        for strategy, stats in strategy_stats.items():
            avg_str = stats['total_strength'] / stats['count']
            strategy_performance[strategy] = {
                'count': stats['count'],
                'avg_strength': avg_str,
                'percentage': (stats['count'] / total_signals) * 100
            }
            
            if avg_str > best_avg_strength:
                best_avg_strength = avg_str
                best_strategy = strategy
        
        return {
            'total_signals': total_signals,
            'win_rate': 0,  # Would need position tracking for actual win rate
            'avg_strength': avg_strength,
            'best_strategy': best_strategy,
            'strategy_performance': strategy_performance
        }
    
    def analyze_symbol_performance(self, symbol: str) -> Dict:
        """Analyze performance for a specific symbol"""
        symbol_signals = [s for s in self.signal_history if s.get('symbol') == symbol]
        
        if not symbol_signals:
            return {
                'total_signals': 0,
                'avg_strength': 0,
                'signal_types': {},
                'recent_signals': []
            }
        
        # Calculate statistics
        total_signals = len(symbol_signals)
        avg_strength = sum(s.get('strength', 0) for s in symbol_signals) / total_signals
        
        # Analyze signal types
        signal_types = {}
        for signal in symbol_signals:
            signal_type = signal.get('type', 'UNKNOWN')
            if signal_type not in signal_types:
                signal_types[signal_type] = 0
            signal_types[signal_type] += 1
        
        # Get recent signals
        recent_signals = sorted(symbol_signals, 
                               key=lambda x: x.get('timestamp', ''), 
                               reverse=True)[:10]
        
        return {
            'total_signals': total_signals,
            'avg_strength': avg_strength,
            'signal_types': signal_types,
            'recent_signals': recent_signals
        }
    
    def analyze_strategy_performance(self) -> Dict:
        """Analyze performance by strategy type"""
        strategy_data = {}
        
        for signal in self.signal_history:
            strategies = signal.get('metadata', {}).get('strategies', [])
            timestamp = signal.get('timestamp', '')
            strength = signal.get('strength', 0)
            
            for strategy in strategies:
                if strategy not in strategy_data:
                    strategy_data[strategy] = {
                        'signals': [],
                        'total_strength': 0,
                        'count': 0
                    }
                
                strategy_data[strategy]['signals'].append({
                    'timestamp': timestamp,
                    'strength': strength,
                    'symbol': signal.get('symbol'),
                    'type': signal.get('type')
                })
                strategy_data[strategy]['total_strength'] += strength
                strategy_data[strategy]['count'] += 1
        
        # Calculate performance metrics for each strategy
        strategy_performance = {}
        for strategy, data in strategy_data.items():
            strategy_performance[strategy] = {
                'count': data['count'],
                'avg_strength': data['total_strength'] / data['count'] if data['count'] > 0 else 0,
                'recent_signals': sorted(data['signals'], 
                                       key=lambda x: x['timestamp'], 
                                       reverse=True)[:5]
            }
        
        return strategy_performance
    
    def export_signal_data(self, symbol='all', signal_type='all', 
                          start_date=None, end_date=None) -> str:
        """Export signal data as CSV"""
        # Get filtered signals
        filtered_signals = self.filter_signal_history(
            symbol=symbol,
            signal_type=signal_type,
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Large limit for export
        )
        
        if not filtered_signals:
            return "timestamp,symbol,type,strength,price,reason\n"
        
        # Convert to CSV
        csv_rows = ["timestamp,symbol,type,strength,price,reason"]
        
        for signal in filtered_signals:
            row = [
                signal.get('timestamp', ''),
                signal.get('symbol', ''),
                signal.get('type', ''),
                str(signal.get('strength', 0)),
                str(signal.get('price', 0)),
                signal.get('reason', '').replace(',', ';')  # Replace commas to avoid CSV issues
            ]
            csv_rows.append(','.join(row))
        
        return '\n'.join(csv_rows)
    
    def calculate_signal_statistics(self) -> Dict:
        """Calculate comprehensive signal statistics"""
        if not self.signal_history:
            return {
                'total_signals': 0,
                'signals_today': 0,
                'avg_strength': 0,
                'type_distribution': {},
                'hourly_distribution': {},
                'symbol_distribution': {}
            }
        
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        total_signals = len(self.signal_history)
        signals_today = 0
        total_strength = 0
        type_counts = {}
        hourly_counts = [0] * 24
        symbol_counts = {}
        
        for signal in self.signal_history:
            # Count today's signals
            try:
                signal_time = datetime.fromisoformat(signal.get('timestamp', ''))
                if signal_time >= today_start:
                    signals_today += 1
                
                # Hourly distribution
                hourly_counts[signal_time.hour] += 1
                
            except ValueError:
                pass
            
            # Strength accumulation
            total_strength += signal.get('strength', 0)
            
            # Type distribution
            signal_type = signal.get('type', 'UNKNOWN')
            type_counts[signal_type] = type_counts.get(signal_type, 0) + 1
            
            # Symbol distribution
            symbol = signal.get('symbol', 'UNKNOWN')
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        
        return {
            'total_signals': total_signals,
            'signals_today': signals_today,
            'avg_strength': total_strength / total_signals if total_signals > 0 else 0,
            'type_distribution': type_counts,
            'hourly_distribution': {str(i): hourly_counts[i] for i in range(24)},
            'symbol_distribution': symbol_counts
        }
    
    def _update_signal_performance(self, signal: Dict):
        """Update performance tracking for a signal"""
        symbol = signal.get('symbol')
        if symbol:
            if symbol not in self.signal_performance:
                self.signal_performance[symbol] = {
                    'total_signals': 0,
                    'total_strength': 0,
                    'last_signal': None
                }
            
            perf = self.signal_performance[symbol]
            perf['total_signals'] += 1
            perf['total_strength'] += signal.get('strength', 0)
            perf['last_signal'] = signal.get('timestamp')
    
    def get_signal_summary(self) -> Dict:
        """Get a summary of recent signal activity"""
        recent_signals = self.signal_history[-10:] if self.signal_history else []
        
        return {
            'recent_count': len(recent_signals),
            'total_count': len(self.signal_history),
            'recent_signals': recent_signals,
            'performance_summary': self.signal_performance
        }

def register_signal_routes(app: Flask, data_manager, bot_manager=None, websocket_service=None):
    """
    Register signal routes with the Flask app
    
    Args:
        app: Flask application instance
        data_manager: Data manager instance
        bot_manager: Bot manager instance (optional)
        websocket_service: WebSocket service instance (optional)
    
    Returns:
        SignalRoutesHandler instance
    """
    handler = SignalRoutesHandler(app, data_manager, bot_manager, websocket_service)
    logger.info("Signal routes registered successfully")
    return handler