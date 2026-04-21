from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication and authorization service"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify plain password against hashed password"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)

        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[int]:
        """Extract user_id from token"""
        payload = AuthService.verify_token(token)

        if payload is None:
            return None

        user_id = payload.get("sub")

        if user_id is None:
            return None

        try:
            return int(user_id)
        except (ValueError, TypeError):
            return None
