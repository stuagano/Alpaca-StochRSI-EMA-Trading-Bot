"""
Secure Configuration Manager
Handles environment variables, encryption, and secure credential management
"""

import os
import json
import base64
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class SecureConfigManager:
    """Secure configuration manager with encryption support"""
    
    def __init__(self, master_password: Optional[str] = None):
        self.master_password = master_password or os.getenv('MASTER_PASSWORD')
        self._cipher = None
        if self.master_password:
            self._cipher = self._create_cipher()
    
    def _create_cipher(self) -> Fernet:
        """Create encryption cipher from master password"""
        password = self.master_password.encode()
        salt = os.getenv('ENCRYPTION_SALT', 'trading_bot_salt').encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return Fernet(key)
    
    def encrypt_value(self, value: str) -> str:
        """Encrypt a configuration value"""
        if not self._cipher:
            raise ValueError("Master password not set for encryption")
        
        encrypted = self._cipher.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a configuration value"""
        if not self._cipher:
            raise ValueError("Master password not set for decryption")
        
        try:
            decoded = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted = self._cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt value: {e}")
            raise ValueError("Invalid encrypted value")
    
    def get_env_var(self, key: str, default: Any = None, required: bool = False, encrypted: bool = False) -> Any:
        """Get environment variable with validation and optional decryption"""
        value = os.getenv(key, default)
        
        if required and value is None:
            raise ValueError(f"Required environment variable {key} is not set")
        
        if value is None:
            return default
        
        # Handle encrypted values
        if encrypted and value and self._cipher:
            try:
                value = self.decrypt_value(value)
            except Exception as e:
                logger.warning(f"Failed to decrypt {key}, using as plaintext: {e}")
        
        # Type conversion
        if isinstance(default, bool):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(default, int):
            try:
                return int(value)
            except ValueError:
                logger.warning(f"Invalid integer value for {key}: {value}")
                return default
        elif isinstance(default, float):
            try:
                return float(value)
            except ValueError:
                logger.warning(f"Invalid float value for {key}: {value}")
                return default
        
        return value
    
    def validate_credentials(self) -> Dict[str, bool]:
        """Validate all required credentials are present"""
        validations = {
            'database': self._validate_database_config(),
            'alpaca': self._validate_alpaca_config(),
            'flask': self._validate_flask_config(),
            'redis': self._validate_redis_config(),
        }
        
        all_valid = all(validations.values())
        if not all_valid:
            logger.error(f"Configuration validation failed: {validations}")
        
        return validations
    
    def _validate_database_config(self) -> bool:
        """Validate database configuration"""
        required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        return all(os.getenv(var) for var in required_vars)
    
    def _validate_alpaca_config(self) -> bool:
        """Validate Alpaca API configuration"""
        required_vars = ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY', 'ALPACA_BASE_URL']
        return all(os.getenv(var) for var in required_vars)
    
    def _validate_flask_config(self) -> bool:
        """Validate Flask configuration"""
        secret_key = os.getenv('FLASK_SECRET_KEY')
        return secret_key and len(secret_key) >= 32
    
    def _validate_redis_config(self) -> bool:
        """Validate Redis configuration"""
        return bool(os.getenv('REDIS_HOST'))
    
    def get_database_url(self) -> str:
        """Get secure database URL"""
        host = self.get_env_var('DB_HOST', required=True)
        port = self.get_env_var('DB_PORT', default=5432)
        database = self.get_env_var('DB_NAME', required=True)
        username = self.get_env_var('DB_USER', required=True)
        password = self.get_env_var('DB_PASSWORD', required=True, encrypted=True)
        
        return f'postgresql://{username}:{password}@{host}:{port}/{database}'
    
    def get_alpaca_config(self) -> Dict[str, str]:
        """Get Alpaca API configuration"""
        return {
            'api_key': self.get_env_var('ALPACA_API_KEY', required=True, encrypted=True),
            'secret_key': self.get_env_var('ALPACA_SECRET_KEY', required=True, encrypted=True),
            'base_url': self.get_env_var('ALPACA_BASE_URL', required=True),
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration"""
        return {
            'host': self.get_env_var('REDIS_HOST', default='localhost'),
            'port': self.get_env_var('REDIS_PORT', default=6379),
            'password': self.get_env_var('REDIS_PASSWORD', encrypted=True),
            'db': self.get_env_var('REDIS_DB', default=0),
        }
    
    def get_flask_config(self) -> Dict[str, Any]:
        """Get Flask configuration"""
        return {
            'secret_key': self.get_env_var('FLASK_SECRET_KEY', required=True),
            'env': self.get_env_var('FLASK_ENV', default='production'),
            'debug': self.get_env_var('FLASK_DEBUG', default=False),
        }
    
    def export_encrypted_config(self, output_file: str) -> None:
        """Export current configuration as encrypted file"""
        if not self._cipher:
            raise ValueError("Master password required for encryption")
        
        config = {
            'database': {
                'host': self.get_env_var('DB_HOST'),
                'port': self.get_env_var('DB_PORT'),
                'name': self.get_env_var('DB_NAME'),
                'user': self.get_env_var('DB_USER'),
                'password': self.encrypt_value(self.get_env_var('DB_PASSWORD', '')),
            },
            'alpaca': {
                'api_key': self.encrypt_value(self.get_env_var('ALPACA_API_KEY', '')),
                'secret_key': self.encrypt_value(self.get_env_var('ALPACA_SECRET_KEY', '')),
                'base_url': self.get_env_var('ALPACA_BASE_URL'),
            },
            'redis': {
                'host': self.get_env_var('REDIS_HOST'),
                'port': self.get_env_var('REDIS_PORT'),
                'password': self.encrypt_value(self.get_env_var('REDIS_PASSWORD', '')),
                'db': self.get_env_var('REDIS_DB'),
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Encrypted configuration exported to {output_file}")


# Global instance
_config_manager = None

def get_secure_config() -> SecureConfigManager:
    """Get global secure configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = SecureConfigManager()
    return _config_manager

def validate_environment() -> bool:
    """Validate all environment variables are properly set"""
    config = get_secure_config()
    validations = config.validate_credentials()
    
    if not all(validations.values()):
        logger.error("Environment validation failed!")
        for service, valid in validations.items():
            if not valid:
                logger.error(f"  {service}: INVALID")
        return False
    
    logger.info("Environment validation passed")
    return True

# Input validation utilities
def validate_symbol(symbol: str) -> str:
    """Validate trading symbol format"""
    if not isinstance(symbol, str):
        raise ValueError("Symbol must be a string")
    
    symbol = symbol.strip().upper()
    if not symbol or len(symbol) > 10:
        raise ValueError("Symbol must be 1-10 characters")
    
    if not symbol.isalnum():
        raise ValueError("Symbol must contain only alphanumeric characters")
    
    return symbol

def validate_timeframe(timeframe: str) -> str:
    """Validate timeframe format"""
    valid_timeframes = {'1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'}
    
    if not isinstance(timeframe, str):
        raise ValueError("Timeframe must be a string")
    
    timeframe = timeframe.strip().lower()
    if timeframe not in valid_timeframes:
        raise ValueError(f"Invalid timeframe. Must be one of: {valid_timeframes}")
    
    return timeframe

def sanitize_string_input(input_str: str, max_length: int = 255) -> str:
    """Sanitize string input to prevent injection attacks"""
    if not isinstance(input_str, str):
        raise ValueError("Input must be a string")
    
    # Remove null bytes and control characters
    sanitized = ''.join(char for char in input_str if ord(char) >= 32 or char in '\n\r\t')
    
    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()