from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Query, Header
from fastapi.security import OAuth2PasswordBearer
from backend.core.config import settings
from backend.database.mongodb import MongoDB
import urllib

# Using the tokenUrl parameter even though we'll handle token generation differently
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token", auto_error=False)

async def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user_from_uniqueKey(uniqueKey: str):
    """Create a user object from uniqueKey parameter"""
    if not uniqueKey:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing uniqueKey",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    decoded_uniqueKey = urllib.parse.unquote(uniqueKey)
    sanitized_uniqueKey = decoded_uniqueKey.replace(" ", "")
    
    # Here we return basic user info - in production, you might fetch this from a database
    user = {"id": sanitized_uniqueKey, "type": "uniqueKey"}
    
    return user

async def get_current_user_from_token(token: str):
    """Validate JWT token and return user info"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
        # In production, you might fetch more user details from the database here
        return {"id": user_id, "type": "token"}
        
    except JWTError:
        raise credentials_exception

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None)
):
    """
    Strict token-based authentication that only accepts JWT tokens.
    Does NOT accept uniqueKey parameter.
    """
    # Extract token from Authorization header if present (preferred method)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    
    # If we have a token (either from Authorization header or OAuth2), use it
    if token:
        return await get_current_user_from_token(token)
    
    # If no token is provided, authentication failed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed. Bearer token required.",
        headers={"WWW-Authenticate": "Bearer"},
    )

# This function is only used for the token generation endpoint
async def get_user_for_token_endpoint(uniqueKey: str = Query(...)):
    """
    Dedicated authentication method for the token endpoint only.
    This function specifically only accepts a uniqueKey parameter.
    """
    return await get_current_user_from_uniqueKey(uniqueKey)