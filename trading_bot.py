from utils.logging_config import logger
import pandas_ta as ta
from config_params import config
import time
import os
import pandas as pd
from datetime import datetime
from risk_management.enhanced_risk_manager import get_enhanced_risk_manager, RiskValidationResult
from risk_management.risk_config import get_risk_config
from typing import Optional, Dict, Any

class TradingBot:
    def __init__(self, data_manager, strategy):
        self.data_manager = data_manager
        self.strategy = strategy
        self.api = data_manager.api
        self.tickers = self.load_tickers()
        self.orders_file = 'ORDERS/Orders.csv'
        self.time_and_coins_file = 'ORDERS/Time and Coins.csv'
        self.risk_management_params = config.risk_management.model_dump()
        
        # Initialize enhanced risk management
        self.enhanced_risk_manager = get_enhanced_risk_manager()
        self.risk_config = get_risk_config()
        self.enable_enhanced_risk_management = True
        
        logger.info("Trading bot initialized with enhanced risk management")

    def load_tickers(self):
        try:
            with open('AUTH/Tickers.txt', 'r') as f:
                return f.read().strip().split()
        except Exception as e:
            logger.error(f"Error loading tickers: {e}")
            return []

    def run(self):
        logger.info("Trading bot started...")
        while True:
            if config.extended_hours or self.is_market_open():
                logger.info("Checking for trading opportunities...")
                self.check_open_positions()
                self.run_strategy()
            else:
                logger.info("Market is closed and extended hours are disabled. Waiting for market open...")
            
            time.sleep(config.sleep_time_between_trades)

    def is_market_open(self):
        return self.api.get_clock().is_open

    def run_strategy(self):
        if not self.can_place_new_trade():
            logger.info("Maximum number of trades reached. No new trades will be placed.")
            return

        for ticker in self.tickers:
            if not self.can_place_new_trade():
                break
            
            df = self.data_manager.get_historical_data(ticker, timeframe=config.timeframe, limit=config.candle_lookback_period)
            if df.empty:
                continue

            signal = self.strategy.generate_signal(df)
            if signal == 1:
                self.enter_position(ticker, df)

    def can_place_new_trade(self):
        open_positions = len(self.api.list_positions())
        return open_positions < config.max_trades_active

    def enter_position(self, ticker, df):
        try:
            price = self.data_manager.get_latest_price(ticker)
            if not price:
                return

            # Enhanced risk management: Calculate optimal position size
            if self.enable_enhanced_risk_management:
                optimal_size_recommendation = self.enhanced_risk_manager.calculate_optimal_position_size(
                    symbol=ticker,
                    entry_price=price
                )
                
                # Use portfolio value to convert percentage to shares
                portfolio_value = self._get_portfolio_value()
                quantity = (optimal_size_recommendation.risk_adjusted_size * portfolio_value) / price
                
                # Additional validation
                stop_loss_price = self.calculate_stop_loss(price, df)
                validation_result = self.enhanced_risk_manager.validate_position_size(
                    symbol=ticker,
                    proposed_size=quantity,
                    entry_price=price,
                    stop_loss_price=stop_loss_price
                )
                
                if not validation_result.approved:
                    logger.warning(f"Position rejected by risk manager for {ticker}: {validation_result.violations}")
                    return
                
                # Apply position size adjustment if recommended
                if validation_result.position_size_adjustment:
                    quantity = validation_result.position_size_adjustment
                    logger.info(f"Position size adjusted for {ticker}: {quantity:.2f} shares")
                
                # Log warnings
                for warning in validation_result.warnings:
                    logger.warning(f"Risk warning for {ticker}: {warning}")
                
            else:
                # Legacy position sizing
                quantity = self.calculate_position_size(price, df)
                stop_loss_price = self.calculate_stop_loss(price, df)

            if quantity <= 0:
                logger.warning(f"Invalid quantity calculated for {ticker}: {quantity}")
                return

            time_in_force = "ext" if config.extended_hours else "day"
            target_price = price * (1 + (config.limit_price * 0.01))
            
            client_order_id = f"sl_{stop_loss_price:.4f}_tp_{target_price:.4f}"
            
            # Execute the trade
            self.api.submit_order(
                symbol=ticker,
                qty=quantity,
                side="buy",
                type="market",
                time_in_force=time_in_force,
                client_order_id=client_order_id
            )
            
            logger.info(f"BUY order placed for {quantity} of {ticker} at {price}")
            
            # Add position to risk tracking
            if self.enable_enhanced_risk_management:
                self.enhanced_risk_manager.add_position(
                    symbol=ticker,
                    entry_price=price,
                    position_size=quantity,
                    stop_loss_price=stop_loss_price
                )
                
                # Create trailing stop
                self.enhanced_risk_manager.create_trailing_stop(
                    symbol=ticker,
                    entry_price=price,
                    position_size=quantity
                )
            
            self.record_order(ticker, price, quantity)
            
        except Exception as e:
            logger.error(f"Error placing buy order for {ticker}: {e}")

    def calculate_position_size(self, price, df):
        cash_to_use = config.investment_amount
        
        if self.risk_management_params.get('use_atr_position_sizing', False):
            atr_period = self.risk_management_params.get('atr_period', 14)
            df.ta.atr(length=atr_period, append=True)
            atr_value = df[f'ATRr_{atr_period}'].iloc[-1]

            if atr_value > 0:
                risk_per_share = atr_value
                risk_amount = cash_to_use * (config.trade_capital_percent * 0.01)
                return risk_amount / risk_per_share

        return (cash_to_use * (config.trade_capital_percent * 0.01)) / price

    def calculate_stop_loss(self, price, df):
        if self.risk_management_params.get('use_atr_stop_loss', False):
            atr_period = self.risk_management_params.get('atr_period', 14)
            atr_multiplier = self.risk_management_params.get('atr_multiplier', 2.0)
            
            df.ta.atr(length=atr_period, append=True)
            atr_value = df[f'ATRr_{atr_period}'].iloc[-1]
            
            if atr_value > 0:
                return price - (atr_value * atr_multiplier)
        
        return price * (1 - (config.stop_loss * 0.01))

    def sell(self, ticker, quantity, buy_price, highest_price, reason: str = "manual"):
        try:
            price = self.data_manager.get_latest_price(ticker)
            if not price:
                return

            self.api.submit_order(ticker, quantity, "sell", "market", "day")
            logger.info(f"SELL order placed for {quantity} of {ticker} at {price} (reason: {reason})")
            
            # Remove position from risk tracking
            if self.enable_enhanced_risk_management:
                self.enhanced_risk_manager.remove_position(ticker)
            
            self.record_sell(ticker, quantity, buy_price, price, highest_price)
        except Exception as e:
            logger.error(f"Error placing sell order for {ticker}: {e}")

    def check_open_positions(self):
        positions = self.api.list_positions()
        if not positions:
            return

        for position in positions:
            ticker = position.symbol
            curr_price = self.data_manager.get_latest_price(ticker)
            if not curr_price:
                continue

            # Update enhanced risk manager with current price
            if self.enable_enhanced_risk_management:
                trailing_stop_trigger = self.enhanced_risk_manager.update_position_price(ticker, curr_price)
                
                # Check if trailing stop was triggered
                if trailing_stop_trigger:
                    logger.info(f"Trailing stop triggered for {ticker}: {trailing_stop_trigger}")
                    self.sell(
                        ticker, 
                        position.qty, 
                        float(position.avg_entry_price), 
                        curr_price,
                        reason="trailing_stop"
                    )
                    continue

            try:
                order = self.api.get_order_by_client_order_id(position.client_order_id)
                client_order_id = order.client_order_id
                parts = client_order_id.split('_')
                stop_loss_price = float(parts[1])
                target_price = float(parts[3])

                if curr_price <= stop_loss_price or curr_price >= target_price:
                    reason = "stop_loss" if curr_price <= stop_loss_price else "target_price"
                    self.sell(ticker, position.qty, float(position.avg_entry_price), curr_price, reason=reason)

            except Exception as e:
                logger.error(f"Could not parse client_order_id for {ticker}: {e}")
                # Fallback or logging for orders placed without the new client_order_id format
                pass



    def record_order(self, ticker, price, quantity):
        stop_loss_price = price * (1 - (config.stop_loss * 0.01))
        target_price = price * (1 + (config.limit_price * 0.01))
        
        new_order = {
            'Time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Ticker': ticker,
            'Type': 'buy',
            'Buy Price': price,
            'Sell Price': '-',
            'Highest Price': price,
            'Quantity': quantity,
            'Total': quantity * price,
            'Acc Balance': self.api.get_account().cash,
            'Target Price': target_price,
            'Stop Loss Price': stop_loss_price,
            'ActivateTrailingStopAt': price * (1 + (config.activate_trailing_stop_loss_at * 0.01))
        }
        
        self.append_to_csv(self.orders_file, new_order)
        # Removed writing to open orders file
        self.append_to_csv(self.time_and_coins_file, {'Time': new_order['Time'], 'Ticker': ticker})

    def record_sell(self, ticker, quantity, buy_price, sell_price, highest_price):
        sell_record = {
            'Time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Ticker': ticker,
            'Type': 'sell',
            'Buy Price': buy_price,
            'Sell Price': sell_price,
            'Highest Price': highest_price,
            'Quantity': quantity,
            'Total': quantity * sell_price,
            'Acc Balance': self.api.get_account().cash,
            'Target Price': '-',
            'Stop Loss Price': '-',
            'ActivateTrailingStopAt': '-'
        }
        self.append_to_csv(self.orders_file, sell_record)

    def append_to_csv(self, filename, data):
        df = pd.DataFrame([data])
        if not os.path.exists(filename):
            df.to_csv(filename, index=False)
        else:
            df.to_csv(filename, mode='a', header=False, index=False)
    
    def _get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        try:
            account = self.api.get_account()
            return float(account.equity)
        except Exception as e:
            logger.error(f"Error getting portfolio value: {e}")
            return 100000.0  # Default fallback
    
    def get_risk_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive risk dashboard data"""
        try:
            if not self.enable_enhanced_risk_management:
                return {"message": "Enhanced risk management disabled"}
            
            # Get portfolio risk summary
            portfolio_summary = self.enhanced_risk_manager.get_portfolio_risk_summary()
            
            # Get validation statistics
            validation_stats = self.enhanced_risk_manager.get_validation_statistics()
            
            # Get trailing stop status
            trailing_stops = self.enhanced_risk_manager.trailing_stop_manager.get_all_stops_status()
            
            return {
                'portfolio_summary': portfolio_summary,
                'validation_statistics': validation_stats,
                'trailing_stops': trailing_stops,
                'risk_config': {
                    'max_daily_loss': self.risk_config.max_daily_loss * 100,
                    'max_position_size': self.risk_config.max_position_size * 100,
                    'max_positions': self.risk_config.max_positions,
                    'risk_level': self.risk_config.get_risk_level().value
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating risk dashboard: {e}")
            return {"error": str(e)}
    
    def enable_emergency_override(self, reason: str, duration_minutes: int = 60) -> bool:
        """Enable emergency risk override"""
        try:
            if not self.enable_enhanced_risk_management:
                return False
            
            success = self.enhanced_risk_manager.enable_emergency_override(reason, duration_minutes)
            if success:
                logger.warning(f"Emergency risk override enabled: {reason}")
            return success
        except Exception as e:
            logger.error(f"Error enabling emergency override: {e}")
            return False
    
    def disable_emergency_override(self) -> bool:
        """Disable emergency risk override"""
        try:
            if not self.enable_enhanced_risk_management:
                return False
            
            success = self.enhanced_risk_manager.disable_emergency_override()
            if success:
                logger.info("Emergency risk override disabled")
            return success
        except Exception as e:
            logger.error(f"Error disabling emergency override: {e}")
            return False
    
    def get_risk_validation_summary(self) -> Dict[str, Any]:
        """Get risk validation summary"""
        try:
            if not self.enable_enhanced_risk_management:
                return {"message": "Enhanced risk management disabled"}
            
            return self.enhanced_risk_manager.get_validation_statistics()
        except Exception as e:
            logger.error(f"Error getting validation summary: {e}")
            return {"error": str(e)}
    
    def validate_proposed_trade(self, ticker: str, proposed_size: float, 
                              entry_price: float) -> RiskValidationResult:
        """Validate a proposed trade before execution"""
        try:
            if not self.enable_enhanced_risk_management:
                # Return approval for legacy mode
                return RiskValidationResult(
                    approved=True,
                    confidence_score=1.0,
                    risk_score=0.0,
                    recommendations=["Enhanced risk management disabled"]
                )
            
            # Calculate stop loss for validation
            df = self.data_manager.get_historical_data(ticker, timeframe=config.timeframe, limit=config.candle_lookback_period)
            stop_loss_price = self.calculate_stop_loss(entry_price, df) if not df.empty else entry_price * 0.95
            
            return self.enhanced_risk_manager.validate_position_size(
                symbol=ticker,
                proposed_size=proposed_size,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price
            )
        except Exception as e:
            logger.error(f"Error validating proposed trade: {e}")
            return RiskValidationResult(
                approved=False,
                confidence_score=0.0,
                risk_score=100.0,
                violations=[f"Validation error: {str(e)}"]
            )
    
    def toggle_enhanced_risk_management(self, enable: bool) -> bool:
        """Toggle enhanced risk management on/off"""
        try:
            self.enable_enhanced_risk_management = enable
            logger.info(f"Enhanced risk management {'enabled' if enable else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Error toggling risk management: {e}")
            return False
