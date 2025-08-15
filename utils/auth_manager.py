"""
Authentication and Environment Manager for Trading Bot
Provides secure handling of API credentials and environment variables
"""

import os
import json
import logging
from typing import Dict, Optional, Any
from dotenv import load_dotenv
from pathlib import Path
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """Manages environment variables and API credentials securely"""
    
    def __init__(self, env_file: str = '.env'):
        """
        Initialize the environment manager
        
        Args:
            env_file: Path to the .env file
        """
        self.env_file = env_file
        self.load_environment()
    
    def load_environment(self) -> None:
        """Load environment variables from .env file"""
        try:
            # Load from .env file if it exists
            env_path = Path(self.env_file)
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded environment from {self.env_file}")
            else:
                logger.warning(f"Environment file {self.env_file} not found, using system environment")
        except Exception as e:
            logger.error(f"Error loading environment: {e}")
            raise
    
    def get_alpaca_credentials(self) -> Dict[str, str]:
        """
        Get Alpaca API credentials from environment variables
        
        Returns:
            Dictionary containing Alpaca API credentials
            
        Raises:
            ValueError: If required credentials are missing
        """
        try:
            credentials = {
                "APCA-API-KEY-ID": self.get_required_env("APCA_API_KEY_ID"),
                "APCA-API-SECRET-KEY": self.get_required_env("APCA_API_SECRET_KEY"),
                "BASE-URL": self.get_env("APCA_BASE_URL", "https://paper-api.alpaca.markets")
            }
            
            # Validate credentials format
            if not credentials["APCA-API-KEY-ID"] or not credentials["APCA-API-SECRET-KEY"]:
                raise ValueError("Invalid Alpaca API credentials")
            
            logger.info("Successfully loaded Alpaca credentials from environment")
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to load Alpaca credentials: {e}")
            # Fallback to legacy file-based credentials with warning
            return self._load_legacy_credentials()
    
    def _load_legacy_credentials(self) -> Dict[str, str]:
        """
        Fallback method to load credentials from legacy AUTH files
        This should be phased out in favor of environment variables
        """
        logger.warning("Falling back to legacy credential loading from AUTH/authAlpaca.txt")
        logger.warning("SECURITY WARNING: Consider migrating to environment variables")
        
        try:
            auth_file = Path("AUTH/authAlpaca.txt")
            if auth_file.exists():
                with open(auth_file, 'r') as f:
                    credentials = json.load(f)
                return credentials
            else:
                raise FileNotFoundError("Legacy credentials file not found")
        except Exception as e:
            logger.error(f"Failed to load legacy credentials: {e}")
            raise ValueError("No valid API credentials found")
    
    def get_flask_config(self) -> Dict[str, Any]:
        """
        Get Flask application configuration from environment
        
        Returns:
            Dictionary containing Flask configuration
        """
        return {
            'SECRET_KEY': self.get_required_env("FLASK_SECRET_KEY"),
            'ENV': self.get_env("FLASK_ENV", "production"),
            'DEBUG': self.get_env("FLASK_DEBUG", "False").lower() == "true",
            'JWT_SECRET_KEY': self.get_required_env("JWT_SECRET_KEY"),
            'JWT_ACCESS_TOKEN_EXPIRES': int(self.get_env("JWT_ACCESS_TOKEN_EXPIRES", "3600")),
        }
    
    def get_cors_origins(self) -> list:
        """
        Get allowed CORS origins from environment
        
        Returns:
            List of allowed origins
        """
        origins_str = self.get_env("CORS_ALLOWED_ORIGINS", "http://localhost:8765")
        return [origin.strip() for origin in origins_str.split(",") if origin.strip()]
    
    def get_required_env(self, key: str) -> str:
        """
        Get required environment variable
        
        Args:
            key: Environment variable name
            
        Returns:
            Environment variable value
            
        Raises:
            ValueError: If required environment variable is missing
        """
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    def get_env(self, key: str, default: str = None) -> str:
        """
        Get environment variable with optional default
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default
        """
        return os.getenv(key, default)
    
    def validate_environment(self) -> bool:
        """
        Validate that all required environment variables are set
        
        Returns:
            True if all required variables are present
        """
        required_vars = [
            "FLASK_SECRET_KEY",
            "JWT_SECRET_KEY",
            "APCA_API_KEY_ID",
            "APCA_API_SECRET_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            return False
        
        logger.info("Environment validation successful")
        return True


class JWTManager:
    """Manages JWT token creation and validation"""
    
    def __init__(self, secret_key: str, expires_delta: int = 3600):
        """
        Initialize JWT manager
        
        Args:
            secret_key: Secret key for JWT signing
            expires_delta: Token expiration time in seconds
        """
        self.secret_key = secret_key
        self.expires_delta = expires_delta
    
    def generate_token(self, user_data: Dict[str, Any]) -> str:
        """
        Generate JWT token for user
        
        Args:
            user_data: User information to encode in token
            
        Returns:
            JWT token string
        """
        payload = {
            'user_data': user_data,
            'exp': datetime.utcnow() + timedelta(seconds=self.expires_delta),
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None


def require_auth(f):
    """
    Decorator to require JWT authentication for Flask routes
    
    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route():
            return jsonify({'message': 'Access granted'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # DEVELOPMENT MODE: Skip authentication
        if os.getenv('SKIP_AUTH', 'true').lower() == 'true':
            request.current_user = {'id': 'dev_user', 'role': 'admin'}
            return f(*args, **kwargs)
        
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid authorization header format'}), 401
        
        # Check for token in query parameters (fallback)
        if not token:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'error': 'Authentication token is missing'}), 401
        
        try:
            # Get JWT manager from app config
            jwt_secret = current_app.config.get('JWT_SECRET_KEY')
            if not jwt_secret:
                logger.error("JWT_SECRET_KEY not configured")
                return jsonify({'error': 'Authentication system not configured'}), 500
            
            jwt_manager = JWTManager(jwt_secret)
            payload = jwt_manager.verify_token(token)
            
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Add user info to request context
            request.current_user = payload.get('user_data')
            
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return jsonify({'error': 'Token verification failed'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def create_demo_token(env_manager: EnvironmentManager) -> str:
    """
    Create a demo JWT token for development/testing
    
    Args:
        env_manager: Environment manager instance
        
    Returns:
        Demo JWT token
    """
    try:
        flask_config = env_manager.get_flask_config()
        jwt_manager = JWTManager(
            flask_config['JWT_SECRET_KEY'],
            flask_config['JWT_ACCESS_TOKEN_EXPIRES']
        )
        
        demo_user = {
            'user_id': 'demo_user',
            'username': 'demo',
            'role': 'trader',
            'created_at': datetime.utcnow().isoformat()
        }
        
        return jwt_manager.generate_token(demo_user)
    
    except Exception as e:
        logger.error(f"Failed to create demo token: {e}")
        raise


# Global environment manager instance
env_manager = EnvironmentManager()


def get_environment_manager() -> EnvironmentManager:
    """Get the global environment manager instance"""
    return env_manager