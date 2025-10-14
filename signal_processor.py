#!/usr/bin/env python3
"""
Signal Processor
Bridges signal generation with trade execution
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Optional
import pandas as pd
from trading_executor import TradingExecutor, TradingSignal
from core.signal_filters import ensure_signal_filters, minimum_strength_percent, minimum_signal_gap

logger = logging.getLogger(__name__)

class SignalProcessor:
    """Process trading signals and coordinate execution"""
    
    def __init__(self, trading_executor: TradingExecutor, config):
        """
        Initialize signal processor
        
        Args:
            trading_executor: Trading execution engine
            config: Configuration parameters
        """
        self.executor = trading_executor
        self.signal_filters = ensure_signal_filters(config)
        self.last_signals: Dict[str, TradingSignal] = {}
        self.signal_history = []
        self.is_running = False
        
        # Signal filtering parameters
        self.min_signal_gap_seconds = minimum_signal_gap(self.signal_filters)
        self.require_confirmation = self.signal_filters.require_confirmation
        self.confirmation_window = self.signal_filters.confirmation_window
        self.min_signal_strength = minimum_strength_percent(self.signal_filters)
        
        logger.info("Signal Processor initialized")
        
    async def process_signal(self, symbol: str, signal_data: Dict) -> Optional[Dict]:
        """
        Process incoming signal and decide whether to execute
        
        Args:
            symbol: Stock symbol
            signal_data: Signal information from strategy
            
        Returns:
            Execution result if trade was placed
        """
        try:
            # Create TradingSignal object
            signal = TradingSignal(
                symbol=symbol,
                action=signal_data.get('signal', 'HOLD'),
                strength=signal_data.get('strength', 0),
                price=signal_data.get('price', 0),
                timestamp=datetime.now(),
                reason=signal_data.get('reason', ''),
                indicators=signal_data.get('indicators', {})
            )
            
            # Check if we should process this signal
            if not await self.should_process_signal(signal):
                return None
                
            # Apply additional filters
            if self.require_confirmation:
                if not await self.confirm_signal(signal):
                    logger.info(f"Signal for {symbol} not confirmed, skipping")
                    return None
                    
            # Execute the signal
            result = await self.executor.execute_signal(signal)
            
            if result:
                # Store successful signal
                self.last_signals[symbol] = signal
                self.signal_history.append({
                    'timestamp': signal.timestamp,
                    'symbol': symbol,
                    'action': signal.action,
                    'strength': signal.strength,
                    'executed': True,
                    'order_id': result.get('id')
                })
                
                logger.info(f"Signal executed successfully for {symbol}: {signal.action}")
                return result
            else:
                # Store failed signal
                self.signal_history.append({
                    'timestamp': signal.timestamp,
                    'symbol': symbol,
                    'action': signal.action,
                    'strength': signal.strength,
                    'executed': False,
                    'reason': 'Execution failed'
                })
                
                return None
                
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            return None
            
    async def should_process_signal(self, signal: TradingSignal) -> bool:
        """
        Determine if signal should be processed
        
        Args:
            signal: Trading signal to evaluate
            
        Returns:
            True if signal should be processed
        """
        try:
            # Check if signal is actionable
            if signal.action == 'HOLD':
                return False
                
            # Check signal strength
            if signal.strength < max(self.min_signal_strength, self.executor.min_signal_strength):
                logger.debug(f"Signal strength {signal.strength} too low")
                return False
                
            # Check for recent signals (avoid overtrading)
            if signal.symbol in self.last_signals:
                last_signal = self.last_signals[signal.symbol]
                time_diff = (signal.timestamp - last_signal.timestamp).total_seconds()
                
                if time_diff < self.min_signal_gap_seconds:
                    logger.debug(f"Too soon since last signal for {signal.symbol} ({time_diff:.0f}s)")
                    return False
                    
                # Don't repeat same signal
                if last_signal.action == signal.action:
                    logger.debug(f"Duplicate signal for {signal.symbol}: {signal.action}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Error checking signal validity: {e}")
            return False
            
    async def confirm_signal(self, signal: TradingSignal) -> bool:
        """
        Confirm signal with additional checks
        
        Args:
            signal: Trading signal to confirm
            
        Returns:
            True if signal is confirmed
        """
        try:
            # Volume confirmation
            if 'volume_confirmed' in signal.indicators:
                if not signal.indicators['volume_confirmed']:
                    logger.debug(f"Volume not confirmed for {signal.symbol}")
                    return False
                    
            # Multi-timeframe confirmation (if available)
            if 'timeframe_aligned' in signal.indicators:
                if not signal.indicators['timeframe_aligned']:
                    logger.debug(f"Timeframes not aligned for {signal.symbol}")
                    return False
                    
            # RSI extreme check (avoid buying overbought, selling oversold)
            if 'rsi' in signal.indicators:
                rsi = signal.indicators['rsi']
                if signal.action == 'BUY' and rsi > 70:
                    logger.debug(f"RSI too high for BUY signal: {rsi}")
                    return False
                elif signal.action == 'SELL' and rsi < 30:
                    logger.debug(f"RSI too low for SELL signal: {rsi}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Error confirming signal: {e}")
            return False
            
    async def start_monitoring(self):
        """Start monitoring for signals"""
        self.is_running = True
        logger.info("Signal monitoring started")
        
    async def stop_monitoring(self):
        """Stop monitoring for signals"""
        self.is_running = False
        logger.info("Signal monitoring stopped")
        
    def get_signal_statistics(self) -> Dict:
        """
        Get statistics about processed signals
        
        Returns:
            Dictionary with signal statistics
        """
        if not self.signal_history:
            return {
                'total_signals': 0,
                'executed_signals': 0,
                'execution_rate': 0,
                'signals_by_symbol': {}
            }
            
        df = pd.DataFrame(self.signal_history)
        
        stats = {
            'total_signals': len(df),
            'executed_signals': len(df[df['executed'] == True]),
            'execution_rate': len(df[df['executed'] == True]) / len(df) * 100,
            'signals_by_symbol': df.groupby('symbol')['executed'].agg(['count', 'sum']).to_dict(),
            'signals_by_action': df.groupby('action')['executed'].agg(['count', 'sum']).to_dict(),
            'average_strength': df['strength'].mean(),
            'last_signal_time': df['timestamp'].max().isoformat() if not df.empty else None
        }
        
        return stats
