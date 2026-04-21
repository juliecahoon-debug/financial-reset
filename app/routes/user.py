from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService
from app.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user account"""
    try:
        db_user = UserService.create_user(db, user)
        return db_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID"""
    db_user = UserService.get_user_by_id(db, user_id)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return db_user


@router.get("/email/{email}", response_model=UserResponse)
async def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """Get user by email"""
    db_user = UserService.get_user_by_email(db, email)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return db_user


@router.get("", response_model=list[UserResponse])
async def list_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Get all users"""
    users = UserService.get_all_users(db, skip=skip, limit=limit)
    return users


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    """Update user"""
    db_user = UserService.update_user(db, user_id, user_update)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return db_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete user"""
    success = UserService.delete_user(db, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return None
