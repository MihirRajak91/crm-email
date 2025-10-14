from fastapi import APIRouter, Depends
from crm.services.auth_services import auth_service
from crm.dependencies.auth import get_current_user
from crm.models.auth_models import TokenData
from datetime import datetime, timezone

router = APIRouter()

@router.get("/token")
def login_for_access_token():
    """
    Description: Generate a JWT access token with demo user data for authentication testing
    
    args:
        None (uses hardcoded demo data)
    
    returns:
        dict: Dictionary containing access_token and token_type for bearer authentication
    """
    data = {
        "user_id" : "39e4f218-0e14-4ca3-a6c7-6ada85ac069f",
        "email" : "demo@example.com",
        "organization_id" : "afbc1992-4994-4210-88ae-4becde0cb8e1",
        "role_id": "admin",
    }

    # Generate the token
    token = auth_service.create_access_token(data=data)

    # Return the token in a response
    return {"access_token": token, "token_type": "bearer"}


@router.get("/user-info")
async def get_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Description: Retrieve user information from decoded JWT token with formatted timestamps
    
    args:
        current_user (TokenData): Validated token data from JWT dependency injection
    
    returns:
        dict: User information including ID, email, organization, role, and formatted timestamps
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "organization_id": current_user.organization_id,
        "role_id": current_user.role_id,
        "exp": datetime.fromtimestamp(current_user.exp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "iat": datetime.fromtimestamp(current_user.iat, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
    }