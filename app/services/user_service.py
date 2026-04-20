from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from typing import Optional
import hashlib


class UserService:
    """Business logic for user operations"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        """Create new user in database"""
        try:
            # Hash the password
            hashed_password = UserService.hash_password(user.password)

            # Create user object
            db_user = User(
                email=user.email,
                username=user.username,
                hashed_password=hashed_password,
                full_name=user.full_name
            )

            # Save to database
            db.add(db_user)
            db.commit()
            db.refresh(db_user)

            return db_user

        except IntegrityError:
            db.rollback()
            raise ValueError("Email or username already exists")

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 10) -> list:
        """Get all users with pagination"""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Update user"""
        db_user = UserService.get_user_by_id(db, user_id)

        if not db_user:
            return None

        # Update only provided fields
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)

        db.commit()
        db.refresh(db_user)

        return db_user

    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """Delete user"""
        db_user = UserService.get_user_by_id(db, user_id)

        if not db_user:
            return False

        db.delete(db_user)
        db.commit()

        return True

