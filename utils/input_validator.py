"""
Comprehensive Input Validation System
Provides secure validation for all user inputs and API parameters
"""

import re
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class InputValidator:
    """Comprehensive input validation with security focus"""
    
    # Trading symbol patterns
    SYMBOL_PATTERN = re.compile(r'^[A-Z]{1,10}$')
    
    # Timeframe validation
    VALID_TIMEFRAMES = {
        '1m', '2m', '5m', '15m', '30m', 
        '1h', '2h', '4h', '6h', '8h', '12h',
        '1d', '3d', '1w', '1M'
    }
    
    # Order type validation
    VALID_ORDER_TYPES = {'market', 'limit', 'stop', 'stop_limit', 'trailing_stop'}
    VALID_ORDER_SIDES = {'buy', 'sell'}
    VALID_TIME_IN_FORCE = {'day', 'gtc', 'ioc', 'fok'}
    
    # Risk limits
    MAX_POSITION_SIZE = Decimal('1000000')  # $1M
    MIN_POSITION_SIZE = Decimal('1')        # $1
    MAX_STOP_LOSS_PERCENT = Decimal('50')   # 50%
    MIN_STOP_LOSS_PERCENT = Decimal('0.1')  # 0.1%
    
    @staticmethod
    def validate_symbol(symbol: Any) -> str:
        """Validate trading symbol"""
        if not isinstance(symbol, str):
            raise ValidationError("Symbol must be a string")
        
        symbol = symbol.strip().upper()
        
        if not symbol:
            raise ValidationError("Symbol cannot be empty")
        
        if not InputValidator.SYMBOL_PATTERN.match(symbol):
            raise ValidationError("Symbol must be 1-10 uppercase letters only")
        
        # Additional security check for common injection patterns
        if any(char in symbol for char in "';\"\\`<>(){}[]"):
            raise ValidationError("Symbol contains invalid characters")
        
        return symbol
    
    @staticmethod
    def validate_timeframe(timeframe: Any) -> str:
        """Validate timeframe"""
        if not isinstance(timeframe, str):
            raise ValidationError("Timeframe must be a string")
        
        timeframe = timeframe.strip().lower()
        
        if not timeframe:
            raise ValidationError("Timeframe cannot be empty")
        
        if timeframe not in InputValidator.VALID_TIMEFRAMES:
            raise ValidationError(f"Invalid timeframe. Must be one of: {InputValidator.VALID_TIMEFRAMES}")
        
        return timeframe
    
    @staticmethod
    def validate_date_range(start_date: Any, end_date: Any) -> Tuple[datetime, datetime]:
        """Validate date range"""
        # Convert to datetime if string
        if isinstance(start_date, str):
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError("Invalid start_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
        
        if isinstance(end_date, str):
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError("Invalid end_date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
        
        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            raise ValidationError("Dates must be datetime objects or ISO format strings")
        
        # Validate date logic
        if start_date >= end_date:
            raise ValidationError("Start date must be before end date")
        
        # Prevent excessive date ranges (> 5 years)
        if (end_date - start_date).days > 1825:
            raise ValidationError("Date range cannot exceed 5 years")
        
        # Prevent future dates beyond reasonable limits
        max_future = datetime.now() + timedelta(days=1)
        if end_date > max_future:
            raise ValidationError("End date cannot be more than 1 day in the future")
        
        return start_date, end_date
    
    @staticmethod
    def validate_quantity(quantity: Any) -> Decimal:
        """Validate trading quantity"""
        try:
            if isinstance(quantity, str):
                quantity = Decimal(quantity)
            elif isinstance(quantity, (int, float)):
                quantity = Decimal(str(quantity))
            elif not isinstance(quantity, Decimal):
                raise ValidationError("Quantity must be a number")
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid quantity format")
        
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        
        if quantity > InputValidator.MAX_POSITION_SIZE:
            raise ValidationError(f"Quantity cannot exceed ${InputValidator.MAX_POSITION_SIZE:,}")
        
        if quantity < InputValidator.MIN_POSITION_SIZE:
            raise ValidationError(f"Quantity must be at least ${InputValidator.MIN_POSITION_SIZE}")
        
        # Check for reasonable precision (max 8 decimal places)
        if quantity.as_tuple().exponent < -8:
            raise ValidationError("Quantity precision cannot exceed 8 decimal places")
        
        return quantity
    
    @staticmethod
    def validate_price(price: Any) -> Decimal:
        """Validate price"""
        try:
            if isinstance(price, str):
                price = Decimal(price)
            elif isinstance(price, (int, float)):
                price = Decimal(str(price))
            elif not isinstance(price, Decimal):
                raise ValidationError("Price must be a number")
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid price format")
        
        if price <= 0:
            raise ValidationError("Price must be positive")
        
        if price > Decimal('1000000'):  # $1M per share
            raise ValidationError("Price cannot exceed $1,000,000 per share")
        
        # Check for reasonable precision (max 4 decimal places for most stocks)
        if price.as_tuple().exponent < -4:
            raise ValidationError("Price precision cannot exceed 4 decimal places")
        
        return price
    
    @staticmethod
    def validate_order_type(order_type: Any) -> str:
        """Validate order type"""
        if not isinstance(order_type, str):
            raise ValidationError("Order type must be a string")
        
        order_type = order_type.strip().lower()
        
        if order_type not in InputValidator.VALID_ORDER_TYPES:
            raise ValidationError(f"Invalid order type. Must be one of: {InputValidator.VALID_ORDER_TYPES}")
        
        return order_type
    
    @staticmethod
    def validate_order_side(side: Any) -> str:
        """Validate order side"""
        if not isinstance(side, str):
            raise ValidationError("Order side must be a string")
        
        side = side.strip().lower()
        
        if side not in InputValidator.VALID_ORDER_SIDES:
            raise ValidationError(f"Invalid order side. Must be one of: {InputValidator.VALID_ORDER_SIDES}")
        
        return side
    
    @staticmethod
    def validate_time_in_force(tif: Any) -> str:
        """Validate time in force"""
        if not isinstance(tif, str):
            raise ValidationError("Time in force must be a string")
        
        tif = tif.strip().lower()
        
        if tif not in InputValidator.VALID_TIME_IN_FORCE:
            raise ValidationError(f"Invalid time in force. Must be one of: {InputValidator.VALID_TIME_IN_FORCE}")
        
        return tif
    
    @staticmethod
    def validate_stop_loss_percent(percent: Any) -> Decimal:
        """Validate stop loss percentage"""
        try:
            if isinstance(percent, str):
                percent = Decimal(percent)
            elif isinstance(percent, (int, float)):
                percent = Decimal(str(percent))
            elif not isinstance(percent, Decimal):
                raise ValidationError("Stop loss percent must be a number")
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid stop loss percent format")
        
        if percent < InputValidator.MIN_STOP_LOSS_PERCENT:
            raise ValidationError(f"Stop loss percent must be at least {InputValidator.MIN_STOP_LOSS_PERCENT}%")
        
        if percent > InputValidator.MAX_STOP_LOSS_PERCENT:
            raise ValidationError(f"Stop loss percent cannot exceed {InputValidator.MAX_STOP_LOSS_PERCENT}%")
        
        return percent
    
    @staticmethod
    def validate_json_payload(payload: Any, max_size: int = 10240) -> Dict[str, Any]:
        """Validate JSON payload"""
        if isinstance(payload, str):
            if len(payload) > max_size:
                raise ValidationError(f"JSON payload too large (max {max_size} characters)")
            
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON format: {e}")
        
        if not isinstance(payload, dict):
            raise ValidationError("Payload must be a JSON object")
        
        # Check for nested depth (prevent DoS)
        if InputValidator._get_nested_depth(payload) > 10:
            raise ValidationError("JSON payload too deeply nested (max 10 levels)")
        
        return payload
    
    @staticmethod
    def _get_nested_depth(obj: Any, depth: int = 0) -> int:
        """Calculate nested depth of object"""
        if depth > 20:  # Prevent infinite recursion
            return depth
        
        if isinstance(obj, dict):
            return max([InputValidator._get_nested_depth(v, depth + 1) for v in obj.values()], default=depth)
        elif isinstance(obj, list):
            return max([InputValidator._get_nested_depth(item, depth + 1) for item in obj], default=depth)
        else:
            return depth
    
    @staticmethod
    def sanitize_string(input_str: Any, max_length: int = 255, allow_html: bool = False) -> str:
        """Sanitize string input"""
        if not isinstance(input_str, str):
            raise ValidationError("Input must be a string")
        
        # Remove null bytes and control characters (except basic whitespace)
        sanitized = ''.join(char for char in input_str if ord(char) >= 32 or char in '\n\r\t')
        
        # Remove HTML if not allowed
        if not allow_html:
            sanitized = re.sub(r'<[^>]*>', '', sanitized)
        
        # Remove potential script injection patterns
        dangerous_patterns = [
            r'javascript:', r'data:', r'vbscript:', r'onload=', r'onerror=',
            r'<script', r'</script>', r'eval\(', r'setTimeout\(', r'setInterval\('
        ]
        
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # Truncate to max length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_order_request(order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete order request"""
        validated = {}
        
        # Required fields
        validated['symbol'] = InputValidator.validate_symbol(order_data.get('symbol'))
        validated['side'] = InputValidator.validate_order_side(order_data.get('side'))
        validated['type'] = InputValidator.validate_order_type(order_data.get('type'))
        validated['qty'] = InputValidator.validate_quantity(order_data.get('qty'))
        
        # Optional fields
        if 'limit_price' in order_data:
            validated['limit_price'] = InputValidator.validate_price(order_data['limit_price'])
        
        if 'stop_price' in order_data:
            validated['stop_price'] = InputValidator.validate_price(order_data['stop_price'])
        
        if 'time_in_force' in order_data:
            validated['time_in_force'] = InputValidator.validate_time_in_force(order_data['time_in_force'])
        
        # Validate price relationships for limit/stop orders
        if validated['type'] in ['limit', 'stop_limit'] and 'limit_price' not in validated:
            raise ValidationError("Limit orders require limit_price")
        
        if validated['type'] in ['stop', 'stop_limit'] and 'stop_price' not in validated:
            raise ValidationError("Stop orders require stop_price")
        
        return validated
    
    @staticmethod
    def validate_api_pagination(page: Any = None, limit: Any = None) -> Tuple[int, int]:
        """Validate API pagination parameters"""
        # Validate page
        if page is not None:
            try:
                page = int(page)
            except (ValueError, TypeError):
                raise ValidationError("Page must be an integer")
            
            if page < 1:
                raise ValidationError("Page must be positive")
            
            if page > 10000:
                raise ValidationError("Page cannot exceed 10,000")
        else:
            page = 1
        
        # Validate limit
        if limit is not None:
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                raise ValidationError("Limit must be an integer")
            
            if limit < 1:
                raise ValidationError("Limit must be positive")
            
            if limit > 1000:
                raise ValidationError("Limit cannot exceed 1,000")
        else:
            limit = 100
        
        return page, limit

# Decorator for automatic validation
def validate_inputs(**validators):
    """Decorator to automatically validate function inputs"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Validate kwargs
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    try:
                        kwargs[param_name] = validator(kwargs[param_name])
                    except ValidationError as e:
                        logger.error(f"Validation error for {param_name}: {e}")
                        raise
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Validation decorators for common use cases
symbol_validator = validate_inputs(symbol=InputValidator.validate_symbol)
timeframe_validator = validate_inputs(timeframe=InputValidator.validate_timeframe)
quantity_validator = validate_inputs(quantity=InputValidator.validate_quantity)
price_validator = validate_inputs(price=InputValidator.validate_price)