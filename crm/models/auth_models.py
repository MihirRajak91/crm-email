from pydantic import BaseModel
from typing import Optional

class TokenData(BaseModel):
    """
    Description: Pydantic model for JWT token data containing user authentication information
    
    args:
        id (str): A unique identifier for the user
        email (str): User's email address
        organization_id (str): Organization ID
        role_id (Optional[str]): Role ID (string or integer as per your design)
        exp (Optional[int]): Expiration time (UNIX timestamp)
        iat (Optional[int]): Issued-at time (UNIX timestamp)
    
    returns:
        TokenData: Validated token data instance
    """
    id: str  # A unique identifier for the user
    email: str  # User's email address
    organization_id: str  # Organization ID
    role_id: Optional[str]  # Role ID (string or integer as per your design)
    exp: Optional[int]  # Expiration time (UNIX timestamp)
    iat: Optional[int]  # Issued-at time (UNIX timestamp)
