from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging

from app.database import get_db
from app.plaid_client import plaid_client
from app.encryption import encryption_service
from app.models import PlaidItem, SecurityLog
from app.utils.security import get_current_user
from app.middleware.rate_limiter import rate_limit

router = APIRouter(prefix="/plaid", tags=["plaid"])
logger = logging.getLogger(__name__)

class PlaidLinkRequest:
    def __init__(self, user_id: str):
        self.user_id = user_id

@router.post("/create_link_token")
@rate_limit("10/minute")
async def create_link_token(
    request: PlaidLinkRequest,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a Plaid Link token for frontend
    """
    try:
        link_token = await plaid_client.create_link_token(request.user_id)
        
        # Log security event
        security_log = SecurityLog(
            event_type="plaid_link_token_created",
            user_id=current_user.get("user_id"),
            ip_address="",  # Would come from request
            details=f"Link token created for user {request.user_id}",
            severity="info"
        )
        db.add(security_log)
        
        return link_token
        
    except Exception as e:
        logger.error(f"Error creating link token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create link token"
        )

@router.post("/exchange_public_token")
@rate_limit("5/minute")
async def exchange_public_token(
    public_token: str,
    user_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Exchange public token for access token and store securely
    """
    try:
        # Exchange public token
        exchange_response = await plaid_client.exchange_public_token(public_token)
        access_token = exchange_response["access_token"]
        item_id = exchange_response["item_id"]
        
        # Encrypt access token
        access_token_enc = encryption_service.encrypt_token(access_token)
        
        # Get item information
        item_info = await plaid_client.get_item_info(access_token)
        institution_id = item_info["item"]["institution_id"]
        
        # Store in database
        plaid_item = PlaidItem(
            item_id=item_id,
            access_token_enc=access_token_enc,
            user_id=user_id,
            institution_id=institution_id,
            status="active"
        )
        
        db.add(plaid_item)
        await db.commit()
        
        # Log security event
        security_log = SecurityLog(
            event_type="plaid_item_linked",
            user_id=user_id,
            details=f"Plaid item {item_id} linked successfully",
            severity="info"
        )
        db.add(security_log)
        await db.commit()
        
        logger.info(f"Plaid item linked successfully for user {user_id}")
        
        return {
            "item_id": item_id,
            "message": "Account linked successfully"
        }
        
    except Exception as e:
        logger.error(f"Error exchanging public token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to link account"
        )

@router.get("/accounts/{item_id}")
@rate_limit("30/minute")
async def get_accounts(
    item_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get accounts for a Plaid item
    """
    try:
        # Get access token from database
        result = await db.execute(
            "SELECT access_token_enc FROM plaid_items WHERE item_id = :item_id AND user_id = :user_id",
            {"item_id": item_id, "user_id": current_user.get("user_id")}
        )
        item = result.fetchone()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plaid item not found"
            )
        
        # Decrypt access token
        access_token = encryption_service.decrypt_token(item[0])
        
        # Get accounts from Plaid
        accounts = await plaid_client.get_accounts(access_token)
        
        return accounts
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch accounts"
        )

@router.delete("/items/{item_id}")
@rate_limit("10/minute")
async def remove_plaid_item(
    item_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Remove a Plaid item and revoke access
    """
    try:
        # Get access token from database
        result = await db.execute(
            "SELECT access_token_enc FROM plaid_items WHERE item_id = :item_id AND user_id = :user_id",
            {"item_id": item_id, "user_id": current_user.get("user_id")}
        )
        item = result.fetchone()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plaid item not found"
            )
        
        # Decrypt access token
        access_token = encryption_service.decrypt_token(item[0])
        
        # Remove from Plaid
        await plaid_client.remove_item(access_token)
        
        # Remove from database
        await db.execute(
            "DELETE FROM plaid_items WHERE item_id = :item_id",
            {"item_id": item_id}
        )
        await db.commit()
        
        # Log security event
        security_log = SecurityLog(
            event_type="plaid_item_removed",
            user_id=current_user.get("user_id"),
            details=f"Plaid item {item_id} removed",
            severity="info"
        )
        db.add(security_log)
        await db.commit()
        
        return {"message": "Account unlinked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing Plaid item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlink account"
        )