from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status,Query
from fastapi.security import OAuth2PasswordBearer
from backend.core.config import settings
from backend.database.mongodb import MongoDB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


async def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

import pyodbc
import urllib

def get_user_details(token):
    # Print start of execution
    print("Starting function execution...")
    
    try:
        # Connection string
        conn_str = (
            "Driver={ODBC Driver 17 for SQL Server};"
            "Server=tcp:ems-sql-db.database.windows.net,1433;"
            "Database=GEN_AI_NEW;"
            "Uid=sqladminuser;"
            "Pwd=Password@123a;"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )
        
        print("Attempting to connect to database...")
        
        # Establish connection
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print(f"Connected successfully! Searching for token: {token}")
        
        # Execute query
        query = "SELECT email, name FROM TokensTable WHERE token = ?"
        cursor.execute(query, token)
        
        # Fetch result
        row = cursor.fetchone()
        
        if row:
            print("\nUser found!")
            print(f"Email: {row.email}")
            print(f"Name: {row.name}")
            result = {"email": row.email, "name": row.name}
        else:
            print("\nNo user found with this token")
            result = None
            
        # Close connections
        cursor.close()
        conn.close()
        print("Connection closed successfully")
        
        return result
    
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        print("Error type:", type(e).__name__)
        return None




# async def get_current_user(token: str = Depends(oauth2_scheme)):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )

#     #user = get_user_details(token)
#     user={
#             "id": "12345",
#             "email": "harsh.chandekar@in.ey.com",
#             "name": "Harsh Chandekar",
#              # Include persona in response
#         }
    
#     if user is None:
#         raise credentials_exception
    
#     print(user["name"])
    
#     return user


async def get_current_user(
    uniqueKey: str = Query(..., alias="uniqueKey")
):
    if not uniqueKey:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing uniqueKey",
            headers={"WWW-Authenticate": "Bearer"},
        )
    decoded_uniqueKey = urllib.parse.unquote(uniqueKey)
    #decoded_uniqueKey = urllib.parse.unquote(uniqueKey) 

    # Step 2: Remove all spaces
    sanitized_uniqueKey = decoded_uniqueKey.replace(" ", "")
    user = {"id": sanitized_uniqueKey}
    print(user["id"])  # Debugging

    return user



# New helper that extracts the persona from the currently logged-in user
# backend/core/security.py

# from fastapi import Depends, HTTPException, status

# async def get_current_persona(current_user: dict = Depends(get_current_user)):
#     persona = current_user.get("persona")
#     if not persona:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="User does not have a persona associated."
#         )
#     return persona
