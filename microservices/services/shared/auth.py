"""
JWT Authentication and Authorization for Microservices
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import User, get_db, DatabaseService

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
JWT_REFRESH_EXPIRATION_DAYS = 30

# Security scheme
security = HTTPBearer()


class AuthService:
    """Authentication service for handling JWT tokens and user authentication."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against a hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def create_access_token(user_id: str, username: str, is_admin: bool = False) -> str:
        """Create a JWT access token."""
        payload = {
            "user_id": user_id,
            "username": username,
            "is_admin": is_admin,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create a JWT refresh token."""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(days=JWT_REFRESH_EXPIRATION_DAYS),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def create_service_token(service_name: str) -> str:
        """Create a JWT token for service-to-service communication."""
        payload = {
            "service": service_name,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "type": "service"
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    @staticmethod
    def register_user(
        session: Session,
        username: str,
        email: str,
        password: str,
        is_admin: bool = False
    ) -> User:
        """Register a new user."""
        # Check if user already exists
        existing_user = session.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )
        
        # Create new user
        hashed_password = AuthService.hash_password(password)
        user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            is_admin=is_admin
        )
        
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return user
    
    @staticmethod
    def authenticate_user(session: Session, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password."""
        user = session.query(User).filter(User.username == username).first()
        
        if not user or not AuthService.verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        session.commit()
        
        return user
    
    @staticmethod
    def get_user_by_id(session: Session, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return session.query(User).filter(User.id == user_id).first()


# Dependency injection for FastAPI
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token."""
    token = credentials.credentials
    
    try:
        payload = AuthService.decode_token(token)
        
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        user = AuthService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get the current user and verify they are an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def verify_service_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """Verify a service-to-service JWT token."""
    token = credentials.credentials
    
    try:
        payload = AuthService.decode_token(token)
        
        if payload.get("type") != "service":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type for service authentication"
            )
        
        return payload
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate service credentials: {str(e)}"
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get the current user if authenticated, otherwise return None."""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# Role-based access control decorators
class RequireRole:
    """Decorator for role-based access control."""
    
    def __init__(self, roles: list[str]):
        self.roles = roles
    
    async def __call__(self, current_user: User = Depends(get_current_user)):
        # For now, we only have admin role
        if "admin" in self.roles and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user


# API Key authentication (alternative to JWT)
class APIKeyAuth:
    """API Key authentication for programmatic access."""
    
    @staticmethod
    def generate_api_key() -> tuple[str, str]:
        """Generate a new API key and secret."""
        import secrets
        api_key = f"pk_{secrets.token_urlsafe(32)}"
        api_secret = f"sk_{secrets.token_urlsafe(48)}"
        return api_key, api_secret
    
    @staticmethod
    def verify_api_key(
        session: Session,
        api_key: str,
        api_secret: str
    ) -> Optional[User]:
        """Verify API key and secret."""
        user = session.query(User).filter(User.api_key == api_key).first()
        
        if not user:
            return None
        
        if not AuthService.verify_password(api_secret, user.api_secret_hash):
            return None
        
        if not user.is_active:
            return None
        
        return user


# Rate limiting decorator
class RateLimit:
    """Simple rate limiting decorator."""
    
    def __init__(self, calls: int, period: int):
        self.calls = calls
        self.period = period
        self.cache = {}  # In production, use Redis
    
    async def __call__(self, current_user: User = Depends(get_current_user)):
        # Simple implementation - in production use Redis
        # This is just a placeholder
        return current_user