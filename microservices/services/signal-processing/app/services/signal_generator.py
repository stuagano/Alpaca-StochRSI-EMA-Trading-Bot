#!/usr/bin/env python3
"""
Signal Generator Service
Handles technical analysis and trading signal generation
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ..models import (
    SignalDB, TradingSignal, SignalRequest, TechnicalIndicators, 
    MarketData, SignalType, SignalSummary
)

logger = logging.getLogger(__name__)

class SignalGenerator:
    """Advanced signal generation engine"""
    
    def __init__(self):
        self.strategies = {
            "stoch_rsi_ema": self._stoch_rsi_ema_strategy,
            "momentum_breakout": self._momentum_breakout_strategy,
            "mean_reversion": self._mean_reversion_strategy,
            "volume_surge": self._volume_surge_strategy
        }
    
    async def generate_signal(
        self, 
        db: AsyncSession, 
        request: SignalRequest
    ) -> Optional[TradingSignal]:
        """Generate trading signal for a symbol"""
        try:
            # Get strategy function
            strategy_func = self.strategies.get(request.strategy)
            if not strategy_func:
                raise ValueError(f"Unknown strategy: {request.strategy}")
            
            # Generate signal using strategy
            signal_data = await strategy_func(request)
            
            if not signal_data:
                logger.debug(f"No signal generated for {request.symbol}")
                return None
            
            # Create signal object
            signal = TradingSignal(
                id=str(uuid.uuid4()),
                symbol=request.symbol.upper(),
                signal_type=signal_data["signal_type"],
                strength=signal_data["strength"],
                confidence=signal_data["confidence"],
                strategy=request.strategy,
                timeframe=request.timeframe,
                price=request.market_data.price if request.market_data else signal_data.get("price", 0.0),
                volume=request.market_data.volume if request.market_data else None,
                indicators_used=signal_data.get("indicators_used", []),
                conditions_met=signal_data.get("conditions_met", []),
                suggested_stop_loss=signal_data.get("stop_loss"),
                suggested_take_profit=signal_data.get("take_profit"),
                risk_reward_ratio=signal_data.get("risk_reward_ratio"),
                position_size_pct=signal_data.get("position_size_pct", 2.0),
                generated_at=datetime.now(),
                valid_until=datetime.now() + timedelta(minutes=self._get_validity_minutes(request.timeframe))
            )
            
            # Save to database
            await self._save_signal(db, signal)
            
            logger.info(f"🎯 Generated {signal.signal_type} signal for {signal.symbol}: {signal.strength}% strength")
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {request.symbol}: {e}")
            return None
    
    async def generate_bulk_signals(
        self, 
        db: AsyncSession, 
        symbols: List[str], 
        strategy: str = "stoch_rsi_ema",
        timeframe: str = "5m",
        min_strength: float = 70
    ) -> List[TradingSignal]:
        """Generate signals for multiple symbols"""
        signals = []
        
        # Process symbols in batches
        batch_size = 10
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            # Create tasks for concurrent processing
            tasks = []
            for symbol in batch:
                request = SignalRequest(
                    symbol=symbol,
                    timeframe=timeframe,
                    strategy=strategy
                )
                tasks.append(self.generate_signal(db, request))
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful results
            for result in batch_results:
                if isinstance(result, TradingSignal) and result.strength >= min_strength:
                    signals.append(result)
        
        logger.info(f"📊 Generated {len(signals)} signals from {len(symbols)} symbols")
        return signals
    
    async def _stoch_rsi_ema_strategy(self, request: SignalRequest) -> Optional[Dict[str, Any]]:
        """Stochastic RSI + EMA crossover strategy"""
        if not request.indicators:
            logger.warning(f"No indicators provided for {request.symbol}")
            return None
        
        indicators = request.indicators
        
        # Check for required indicators
        if not all([indicators.stoch_rsi_k, indicators.stoch_rsi_d, indicators.ema_short, indicators.ema_long]):
            logger.warning(f"Missing required indicators for {request.symbol}")
            return None
        
        signal_type = SignalType.HOLD
        strength = 0.0
        confidence = 0.0
        conditions_met = []
        indicators_used = ["stoch_rsi", "ema"]
        
        # EMA trend analysis
        ema_bullish = indicators.ema_short > indicators.ema_long
        ema_distance = abs(indicators.ema_short - indicators.ema_long) / indicators.ema_long * 100
        
        # Stochastic RSI analysis
        stoch_oversold = indicators.stoch_rsi_k < 20 and indicators.stoch_rsi_d < 20
        stoch_overbought = indicators.stoch_rsi_k > 80 and indicators.stoch_rsi_d > 80
        stoch_bullish_cross = indicators.stoch_rsi_k > indicators.stoch_rsi_d
        
        # Generate BUY signal
        if ema_bullish and stoch_oversold and stoch_bullish_cross:
            signal_type = SignalType.BUY
            strength = 75.0
            confidence = 80.0
            
            # Boost strength based on conditions
            if ema_distance > 2.0:  # Strong trend
                strength += 10
                conditions_met.append("strong_uptrend")
            
            if indicators.stoch_rsi_k < 10:  # Very oversold
                strength += 5
                conditions_met.append("deeply_oversold")
            
            conditions_met.extend(["ema_bullish", "stoch_oversold", "stoch_bullish_cross"])
        
        # Generate SELL signal
        elif not ema_bullish and stoch_overbought and not stoch_bullish_cross:
            signal_type = SignalType.SELL
            strength = 75.0
            confidence = 80.0
            
            # Boost strength based on conditions
            if ema_distance > 2.0:  # Strong downtrend
                strength += 10
                conditions_met.append("strong_downtrend")
            
            if indicators.stoch_rsi_k > 90:  # Very overbought
                strength += 5
                conditions_met.append("deeply_overbought")
            
            conditions_met.extend(["ema_bearish", "stoch_overbought", "stoch_bearish_cross"])
        
        # No strong signal
        if signal_type == SignalType.HOLD:
            return None
        
        # Calculate risk management levels
        current_price = request.market_data.price if request.market_data else indicators.ema_short
        
        if signal_type == SignalType.BUY:
            stop_loss = current_price * 0.97  # 3% stop loss
            take_profit = current_price * 1.06  # 6% take profit
        else:  # SELL
            stop_loss = current_price * 1.03  # 3% stop loss
            take_profit = current_price * 0.94  # 6% take profit
        
        risk_reward_ratio = abs(take_profit - current_price) / abs(current_price - stop_loss)
        
        return {
            "signal_type": signal_type,
            "strength": min(strength, 100.0),
            "confidence": min(confidence, 100.0),
            "indicators_used": indicators_used,
            "conditions_met": conditions_met,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": risk_reward_ratio,
            "position_size_pct": 2.0,
            "price": current_price
        }
    
    async def _momentum_breakout_strategy(self, request: SignalRequest) -> Optional[Dict[str, Any]]:
        """Momentum breakout strategy"""
        # Placeholder for momentum breakout logic
        return None
    
    async def _mean_reversion_strategy(self, request: SignalRequest) -> Optional[Dict[str, Any]]:
        """Mean reversion strategy"""
        # Placeholder for mean reversion logic
        return None
    
    async def _volume_surge_strategy(self, request: SignalRequest) -> Optional[Dict[str, Any]]:
        """Volume surge strategy"""
        # Placeholder for volume surge logic
        return None
    
    async def _save_signal(self, db: AsyncSession, signal: TradingSignal) -> None:
        """Save signal to database"""
        try:
            signal_db = SignalDB(
                id=signal.id,
                symbol=signal.symbol,
                signal_type=signal.signal_type.value,
                strength=signal.strength,
                confidence=signal.confidence,
                strategy=signal.strategy,
                timeframe=signal.timeframe,
                price=signal.price,
                volume=signal.volume,
                indicators_used=signal.indicators_used,
                conditions_met=signal.conditions_met,
                suggested_stop_loss=signal.suggested_stop_loss,
                suggested_take_profit=signal.suggested_take_profit,
                risk_reward_ratio=signal.risk_reward_ratio,
                position_size_pct=signal.position_size_pct,
                generated_at=signal.generated_at,
                valid_until=signal.valid_until
            )
            
            db.add(signal_db)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error saving signal to database: {e}")
            await db.rollback()
            raise
    
    def _get_validity_minutes(self, timeframe: str) -> int:
        """Get signal validity duration based on timeframe"""
        timeframe_validity = {
            "1m": 5,
            "5m": 15,
            "15m": 30,
            "1h": 120,
            "1d": 1440
        }
        return timeframe_validity.get(timeframe, 15)
    
    async def get_signal_summary(self, db: AsyncSession) -> SignalSummary:
        """Get signal summary for dashboard"""
        try:
            today = datetime.now().date()
            
            # Get today's signals
            query = select(SignalDB).where(
                SignalDB.generated_at >= datetime.combine(today, datetime.min.time())
            )
            result = await db.execute(query)
            signals = result.scalars().all()
            
            # Calculate metrics
            total_signals = len(signals)
            buy_signals = len([s for s in signals if s.signal_type == "buy"])
            sell_signals = len([s for s in signals if s.signal_type == "sell"])
            hold_signals = total_signals - buy_signals - sell_signals
            
            avg_strength = sum(s.strength for s in signals) / total_signals if total_signals > 0 else 0
            avg_confidence = sum(s.confidence for s in signals) / total_signals if total_signals > 0 else 0
            
            strong_signals = len([s for s in signals if s.strength >= 70])
            executed_signals = len([s for s in signals if s.is_executed])
            execution_rate = executed_signals / total_signals * 100 if total_signals > 0 else 0
            
            # Top symbols
            symbol_counts = {}
            for signal in signals:
                symbol_counts[signal.symbol] = symbol_counts.get(signal.symbol, 0) + 1
            
            top_symbols = [
                {"symbol": symbol, "count": count}
                for symbol, count in sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
            
            # Latest signals
            latest_signals = [
                TradingSignal(
                    id=s.id,
                    symbol=s.symbol,
                    signal_type=SignalType(s.signal_type),
                    strength=s.strength,
                    confidence=s.confidence,
                    strategy=s.strategy,
                    timeframe=s.timeframe,
                    price=s.price,
                    volume=s.volume,
                    generated_at=s.generated_at,
                    is_executed=s.is_executed
                )
                for s in sorted(signals, key=lambda x: x.generated_at, reverse=True)[:10]
            ]
            
            return SignalSummary(
                total_signals_today=total_signals,
                buy_signals=buy_signals,
                sell_signals=sell_signals,
                hold_signals=hold_signals,
                avg_strength=avg_strength,
                avg_confidence=avg_confidence,
                strong_signals=strong_signals,
                executed_signals=executed_signals,
                execution_rate=execution_rate,
                top_symbols=top_symbols,
                latest_signals=latest_signals,
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error generating signal summary: {e}")
            raise