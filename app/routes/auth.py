from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.schemas.user import LoginRequest, TokenResponse
from app.services.user_service import UserService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login endpoint - returns JWT token"""

    # Find user by email
    user = UserService.get_user_by_email(db, login_data.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not AuthService.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = AuthService.create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email
    }


@router.post("/verify-token")
async def verify_token(token: str):
    """Verify if a token is valid"""

    payload = AuthService.verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "valid": True,
        "user_id": payload.get("sub"),
        "email": payload.get("email")
    }
