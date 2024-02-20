# deal with tokens
from datetime import timedelta, timezone
from datetime import datetime
from pydantic import BaseModel
from timelink.app.models.user import User
from timelink.app.models.user_database import UserDatabase
from passlib.context import CryptContext
from jose import JWTError, jwt

SECRET_KEY = "cd02c76b7bb2911c8eda7ca38f2a8b1bd15551515cd6341d92ba8cf4e8925b8d"
ALGORITHM = "HS256"


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create an access token

    Args:
        data (dict): The data to encode in the token
        expires_delta (timedelta, optional): The time delta for the token to expire. Defaults to None."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def decode_token(token):
    """Decode a token"""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def fake_hash_password(password):
    return password + "hashed"


def authenticate_user(users_db: UserDatabase, username: str, password: str):
    with users_db.session() as session:
        user = users_db.get_user_by_name(username, session=session)
        if not user:
            return False
        if not verify_password(password, user.hashed_password):
            return False
        return user
