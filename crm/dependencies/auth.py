# app/dependencies/auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from crm.models.auth_models import TokenData
from crm.services.auth_services import auth_service
from crm.utils.logger import logger

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Description: FastAPI dependency to extract and validate user_id from JWT access token without database calls
    
    args:
        credentials (HTTPAuthorizationCredentials): Bearer token credentials from HTTP Authorization header
    
    returns:
        TokenData: Validated token data containing user information, raises HTTPException if invalid
    """
    logger.info(f"Credential Input : {credentials}")
    token = auth_service.get_token_from_credentials(credentials)
    logger.info(f"Credential Input : {token}")
    token_data = auth_service.verify_access_token(token)
    logger.info(f"Token Data : {token_data}")
 
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return token_data
