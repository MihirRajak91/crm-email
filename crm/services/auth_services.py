from datetime import datetime, timedelta
import jwt  # from PyJWT
from jwt.exceptions import PyJWTError, ExpiredSignatureError, InvalidTokenError
# from passlib.context import CryptContext
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging
import os
from dotenv import load_dotenv
from crm.utils.logger import logger

from crm.models.auth_models import TokenData
from crm.core.settings import get_settings

settings = get_settings()
# Load environment variables from .env
# load_dotenv()


# logger = logging.getLogger(__name__)
security = HTTPBearer()

class AuthService:
    """
    Description: JWT authentication service for creating and verifying access tokens with configurable expiration
    
    args:
        secret_key (str): Secret key for JWT token signing and verification
        algorithm (str): JWT algorithm for token encoding, defaults to "HS256"
        access_token_expire_minutes (int): Token expiration time in minutes, defaults to 30
    
    returns:
        AuthService: Instance for handling JWT token operations and user authentication
    """
    def __init__(self, secret_key: str, algorithm: str = "HS256", access_token_expire_minutes: int = 30):
        """
        Description: Initialize the authentication service with JWT configuration parameters
        
        args:
            secret_key (str): Secret key for JWT token operations
            algorithm (str): JWT signing algorithm
            access_token_expire_minutes (int): Token expiration duration in minutes
        
        returns:
            None
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = int(access_token_expire_minutes)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Description: Create a JWT access token with user data and configurable expiration time
        
        args:
            data (dict): User data to encode in the JWT token
            expires_delta (Optional[timedelta]): Custom expiration time, defaults to configured minutes
        
        returns:
            str: Encoded JWT access token with user data and expiration information
        """
        to_encode = data.copy()
        now = datetime.utcnow()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=self.access_token_expire_minutes))
        to_encode.update({
            "exp": expire,
            "iat": now,
        })
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_access_token(self, token: str) -> Optional[TokenData]:
        """
        Description: Verify JWT access token and return decoded TokenData with error handling for expired/invalid tokens
        
        args:
            token (str): JWT access token to verify and decode
        
        returns:
            Optional[TokenData]: Decoded token data with user information, None if token is invalid, raises HTTPException for auth errors
        """
        try:
            # Decode the token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            logger.info(f"Payload : {payload}")
            
            # Extract necessary fields from the payload
            user_id = payload.get("id") or payload.get("user_id")  # Match the correct field name
            email = payload.get("email")
            organization_id = payload.get("organization_id")
            role_id = payload.get("role_id")
            exp = payload.get("exp")
            iat = payload.get("iat")

            # Ensure that the required fields exist
            if user_id is None or email is None or exp is None or iat is None:
                logger.warning(f"Token is missing required fields. Token payload: {payload}")
                return None

            # Return TokenData with necessary claims
            return TokenData(
                id=user_id,  # Set the correct field here
                email=email,
                organization_id=organization_id,
                role_id=role_id,
                exp=exp,  # Expiration time (UNIX timestamp)
                iat=iat   # Issued-at time (UNIX timestamp)
            )
        except ExpiredSignatureError:
            logger.warning("Token has expired.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired.")
        except InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
        except PyJWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token verification failed.")

    def get_token_from_credentials(self, credentials: HTTPAuthorizationCredentials) -> str:
        """
        Description: Extract JWT token from HTTP Authorization credentials with Bearer scheme validation
        
        args:
            credentials (HTTPAuthorizationCredentials): HTTP authorization credentials containing Bearer token
        
        returns:
            str: Extracted JWT token string, raises HTTPException for invalid authentication scheme
        """
        if credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme"
            )
        return credentials.credentials

# Load config from environment
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# SECRET_KEY = os.getenv("JWT_ACCESS_SECRET", "default_secret")
# ALGORITHM = os.getenv("ALGORITHM", "HS256")
# ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "300")

# Create global auth service instance
auth_service = AuthService(
    secret_key=SECRET_KEY,
    algorithm=ALGORITHM,
    access_token_expire_minutes=ACCESS_TOKEN_EXPIRE_MINUTES
)