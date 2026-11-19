from sqlalchemy.orm import Session
from backend.shared.models import User
from backend.shared.security import hash_password, encrypt_data
import hashlib


def get_user_by_email(db: Session, email: str) -> User:
    return db.query(User).filter(User.email_hash == _hash_email(email)).first()


def create_user(db: Session, email: str, password: str) -> User:
    hashed_pw = hash_password(password)
    encrypted_email = encrypt_data(email)
    email_hash = _hash_email(email)
    user = User(email_hash=email_hash, email=encrypted_email, hashed_password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _hash_email(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()
