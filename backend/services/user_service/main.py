from sqlalchemy.orm import Session
from backend.shared.models import User
from backend.shared.security import hash_password, encrypt_data


def get_user_by_email(db: Session, email: str) -> User:
    # Email is stored encrypted; we need to decrypt and compare (not efficient, but for small scale)
    # For production, use hashed email or deterministic encryption. Here we'll decrypt each user? Actually we store encrypted, but we need to find by email.
    # A better approach: store hashed email as index. We'll adjust: store email_hash = sha256(email) as separate indexed column, and encrypted_email.
    # But for now, we'll just iterate (only for Phase 0).
    # Let's implement email_hash for lookup.
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
    import hashlib

    return hashlib.sha256(email.lower().encode()).hexdigest()
