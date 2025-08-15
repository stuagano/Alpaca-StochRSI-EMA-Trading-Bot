"""
Secure Configuration Loader
Integrates with the existing config system while adding environment variable support
and security enhancements
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict, fields
from datetime import datetime
from pathlib import Path

from utils.auth_manager import get_environment_manager
from config.config_manager import (
    ConfigManager, TradingConfig, IndicatorConfig, AlpacaConfig,
    DatabaseConfig, LoggingConfig, UIConfig, NotificationConfig
)

logger = logging.getLogger(__name__)


class SecureConfigLoader:
    """
    Secure configuration loader that integrates environment variables
    with the existing configuration system
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize secure config loader
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.env_manager = get_environment_manager()
        self.config_manager = ConfigManager(config_dir)
        
        # Environment variable mappings for sensitive data
        self.env_mappings = {
            'alpaca': {
                'api_key': 'APCA_API_KEY_ID',
                'api_secret': 'APCA_API_SECRET_KEY',
                'base_url': 'APCA_BASE_URL'
            },
            'database': {
                'db_path': 'DATABASE_URL'
            },
            'logging': {
                'log_level': 'LOG_LEVEL',
                'log_dir': 'LOG_DIR'
            },
            'ui': {
                'flask_host': 'FLASK_HOST',
                'flask_port': 'FLASK_PORT',
                'flask_debug': 'FLASK_DEBUG'
            },
            'notifications': {
                'email_username': 'EMAIL_USERNAME',
                'email_password': 'EMAIL_PASSWORD',
                'discord_webhook_url': 'DISCORD_WEBHOOK_URL',
                'telegram_bot_token': 'TELEGRAM_BOT_TOKEN',
                'telegram_chat_id': 'TELEGRAM_CHAT_ID'
            }
        }
        
        self._apply_environment_overrides()
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides to configurations"""
        try:
            for config_name, mappings in self.env_mappings.items():
                config = self.config_manager.get_config(config_name)
                updates = {}
                
                for attr_name, env_var in mappings.items():
                    env_value = os.getenv(env_var)
                    if env_value is not None:
                        # Type conversion based on the original attribute type
                        current_value = getattr(config, attr_name, None)
                        if current_value is not None:
                            if isinstance(current_value, bool):
                                env_value = env_value.lower() in ('true', '1', 'yes', 'on')
                            elif isinstance(current_value, int):
                                env_value = int(env_value)
                            elif isinstance(current_value, float):
                                env_value = float(env_value)
                        
                        updates[attr_name] = env_value
                        logger.debug(f"Override {config_name}.{attr_name} from environment")
                
                if updates:
                    self.config_manager.update_config(config_name, updates, save=False)
                    logger.info(f"Applied {len(updates)} environment overrides to {config_name} config")
        
        except Exception as e:
            logger.error(f"Error applying environment overrides: {e}")
    
    def load_secure_alpaca_config(self) -> AlpacaConfig:
        """
        Load Alpaca configuration with secure credential handling
        
        Returns:
            AlpacaConfig with credentials from environment or legacy files
        """
        try:
            # Start with the base configuration
            config = self.config_manager.get_config('alpaca')
            
            # Try to get credentials from environment first
            try:
                credentials = self.env_manager.get_alpaca_credentials()
                config.api_key = credentials["APCA-API-KEY-ID"]
                config.api_secret = credentials["APCA-API-SECRET-KEY"]
                config.base_url = credentials["BASE-URL"]
                logger.info("Loaded Alpaca credentials from secure environment")
            except Exception as e:
                logger.warning(f"Failed to load secure credentials: {e}")
                logger.warning("Using configuration file credentials (less secure)")
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load Alpaca configuration: {e}")
            raise
    
    def create_secure_config_template(self) -> Dict[str, Any]:
        """
        Create a template showing which values should be set via environment variables
        
        Returns:
            Template configuration with security notes
        """
        template = {
            "security_notice": "Sensitive values should be set via environment variables",
            "required_env_vars": {},
            "optional_env_vars": {},
            "config_files": {}
        }
        
        # Required environment variables
        template["required_env_vars"] = {
            "FLASK_SECRET_KEY": "Flask application secret key (min 32 chars)",
            "JWT_SECRET_KEY": "JWT token signing key (min 32 chars)",
            "APCA_API_KEY_ID": "Alpaca API key ID",
            "APCA_API_SECRET_KEY": "Alpaca API secret key"
        }
        
        # Optional environment variables
        template["optional_env_vars"] = {
            "APCA_BASE_URL": "Alpaca API base URL (defaults to paper trading)",
            "DATABASE_URL": "Database connection URL",
            "LOG_LEVEL": "Logging level (DEBUG, INFO, WARNING, ERROR)",
            "FLASK_HOST": "Flask server host",
            "FLASK_PORT": "Flask server port",
            "CORS_ALLOWED_ORIGINS": "Comma-separated CORS origins"
        }
        
        # Configuration file examples (non-sensitive)
        all_configs = self.config_manager.get_config_summary()
        for config_name, config_data in all_configs.items():
            # Remove sensitive fields from template
            clean_config = self._sanitize_config_for_template(config_name, config_data)
            template["config_files"][f"{config_name}.json"] = clean_config
        
        return template
    
    def _sanitize_config_for_template(self, config_name: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive fields from configuration for template
        
        Args:
            config_name: Name of the configuration
            config_data: Configuration data
            
        Returns:
            Sanitized configuration data
        """
        sensitive_fields = {
            'alpaca': ['api_key', 'api_secret'],
            'notifications': ['email_password', 'discord_webhook_url', 'telegram_bot_token']
        }
        
        clean_config = config_data.copy()
        
        if config_name in sensitive_fields:
            for field in sensitive_fields[config_name]:
                if field in clean_config:
                    clean_config[field] = f"<SET_VIA_ENV_VAR_{field.upper()}>"
        
        return clean_config
    
    def validate_security_settings(self) -> Dict[str, Any]:
        """
        Validate security settings across all configurations
        
        Returns:
            Security validation results
        """
        results = {
            'secure': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        try:
            # Check if environment variables are being used for sensitive data
            alpaca_config = self.config_manager.get_config('alpaca')
            
            # Check for hardcoded API keys (security risk)
            if alpaca_config.api_key and not os.getenv('APCA_API_KEY_ID'):
                results['warnings'].append("API key is hardcoded in config file - consider using environment variables")
            
            if alpaca_config.api_secret and not os.getenv('APCA_API_SECRET_KEY'):
                results['warnings'].append("API secret is hardcoded in config file - consider using environment variables")
            
            # Check Flask secret key
            flask_secret = os.getenv('FLASK_SECRET_KEY')
            if not flask_secret:
                results['errors'].append("FLASK_SECRET_KEY environment variable not set")
                results['secure'] = False
            elif len(flask_secret) < 32:
                results['warnings'].append("Flask secret key should be at least 32 characters long")
            
            # Check JWT secret key
            jwt_secret = os.getenv('JWT_SECRET_KEY')
            if not jwt_secret:
                results['errors'].append("JWT_SECRET_KEY environment variable not set")
                results['secure'] = False
            elif len(jwt_secret) < 32:
                results['warnings'].append("JWT secret key should be at least 32 characters long")
            
            # Check if using paper trading
            if not alpaca_config.paper_trading:
                results['warnings'].append("Live trading is enabled - ensure you understand the risks")
            
            # Check CORS configuration
            cors_origins = self.env_manager.get_cors_origins()
            if '*' in cors_origins or 'http://*' in cors_origins:
                results['warnings'].append("CORS allows all origins - consider restricting to specific domains")
            
            # Generate recommendations
            if results['warnings'] or results['errors']:
                results['recommendations'].extend([
                    "Copy .env.example to .env and configure your environment variables",
                    "Use strong, unique secret keys for Flask and JWT",
                    "Restrict CORS origins to trusted domains only",
                    "Use paper trading for development and testing",
                    "Regularly rotate API keys and secrets"
                ])
            
        except Exception as e:
            results['secure'] = False
            results['errors'].append(f"Security validation error: {e}")
        
        return results
    
    def export_secure_config(self, export_path: str = None) -> str:
        """
        Export configuration template with security guidelines
        
        Args:
            export_path: Path to export the template
            
        Returns:
            Path to exported template
        """
        if export_path is None:
            export_path = self.config_dir / "secure_config_template.json"
        
        try:
            template = self.create_secure_config_template()
            security_results = self.validate_security_settings()
            
            export_data = {
                "generated_at": datetime.now().isoformat(),
                "security_status": security_results,
                "configuration_template": template,
                "setup_instructions": [
                    "1. Copy .env.example to .env",
                    "2. Set all required environment variables in .env",
                    "3. Configure optional settings as needed",
                    "4. Run security validation before production use",
                    "5. Regularly update and rotate credentials"
                ]
            }
            
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Secure configuration template exported to {export_path}")
            return str(export_path)
            
        except Exception as e:
            logger.error(f"Failed to export secure configuration: {e}")
            raise
    
    def get_config_manager(self) -> ConfigManager:
        """Get the underlying configuration manager"""
        return self.config_manager
    
    def get_all_configs(self) -> Dict[str, Any]:
        """
        Get all configurations with environment overrides applied
        
        Returns:
            Dictionary of all configuration objects
        """
        return {
            'trading': self.config_manager.get_config('trading'),
            'indicators': self.config_manager.get_config('indicators'),
            'alpaca': self.load_secure_alpaca_config(),
            'database': self.config_manager.get_config('database'),
            'logging': self.config_manager.get_config('logging'),
            'ui': self.config_manager.get_config('ui'),
            'notifications': self.config_manager.get_config('notifications')
        }


# Global secure config loader instance
_secure_config_loader = None


def get_secure_config_loader() -> SecureConfigLoader:
    """Get singleton secure configuration loader instance"""
    global _secure_config_loader
    if _secure_config_loader is None:
        _secure_config_loader = SecureConfigLoader()
    return _secure_config_loader


def get_secure_alpaca_config() -> AlpacaConfig:
    """Get secure Alpaca configuration"""
    return get_secure_config_loader().load_secure_alpaca_config()


def validate_security() -> Dict[str, Any]:
    """Validate security settings across all configurations"""
    return get_secure_config_loader().validate_security_settings()