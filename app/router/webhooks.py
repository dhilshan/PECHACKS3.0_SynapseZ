from fastapi import APIRouter, Request, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import json
import hashlib
import hmac
import logging

from app.database import get_db
from app.models import WebhookLog, PlaidItem, SecurityLog
from app.plaid_client import plaid_client
from app.config import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

async def verify_plaid_webhook(request: Request) -> bool:
    """
    Verify Plaid webhook signature
    """
    try:
        signature = request.headers.get("Plaid-Verification")
        if not signature:
            logger.warning("Missing Plaid-Verification header")
            return False
        
        # In production, verify the JWT signature using Plaid's verification key
        # This is a simplified version - implement full JWT verification
        body = await request.body()
        expected_signature = hmac.new(
            settings.PLAID_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Basic verification - replace with proper JWT verification
        return len(signature) > 0  # Placeholder
        
    except Exception as e:
        logger.error(f"Webhook verification failed: {e}")
        return False

@router.post("/plaid")
async def plaid_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Plaid webhooks
    """
    try:
        # Verify webhook signature
        is_verified = await verify_plaid_webhook(request)
        
        # Parse webhook body
        body = await request.body()
        webhook_data = json.loads(body)
        
        # Log webhook
        webhook_log = WebhookLog(
            webhook_type=webhook_data.get("webhook_type"),
            webhook_code=webhook_data.get("webhook_code"),
            item_id=webhook_data.get("item_id"),
            message=json.dumps(webhook_data),
            signature=request.headers.get("Plaid-Verification", ""),
            verified=is_verified,
            processed=False
        )
        db.add(webhook_log)
        await db.commit()
        
        if not is_verified:
            logger.warning("Unverified webhook received")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook verification failed"
            )
        
        # Process webhook in background
        background_tasks.add_task(process_plaid_webhook, webhook_data, db)
        
        return {"status": "webhook received"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )

async def process_plaid_webhook(webhook_data: Dict[str, Any], db: AsyncSession):
    """
    Process Plaid webhook in background
    """
    try:
        webhook_type = webhook_data.get("webhook_type")
        webhook_code = webhook_data.get("webhook_code")
        item_id = webhook_data.get("item_id")
        
        logger.info(
            f"Processing webhook: {webhook_type}.{webhook_code}",
            extra={"item_id": item_id}
        )
        
        if webhook_type == "TRANSACTIONS":
            await handle_transactions_webhook(webhook_data, db)
        elif webhook_type == "ITEM":
            await handle_item_webhook(webhook_data, db)
        elif webhook_type == "HOLDINGS":
            await handle_holdings_webhook(webhook_data, db)
        
        # Mark webhook as processed
        await db.execute(
            "UPDATE webhook_logs SET processed = True WHERE item_id = :item_id AND webhook_code = :webhook_code",
            {"item_id": item_id, "webhook_code": webhook_code}
        )
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error in background webhook processing: {e}")

async def handle_transactions_webhook(webhook_data: Dict[str, Any], db: AsyncSession):
    """Handle transactions webhooks"""
    webhook_code = webhook_data.get("webhook_code")
    item_id = webhook_data.get("item_id")
    
    if webhook_code == "SYNC_UPDATIONS_AVAILABLE":
        logger.info(f"New transactions available for sync: {item_id}")
        # In production, trigger a sync job here
        
    elif webhook_code == "DEFAULT_UPDATE":
        logger.info(f"Initial transaction data ready: {item_id}")
        
    elif webhook_code == "TRANSACTIONS_REMOVED":
        removed_transactions = webhook_data.get("removed_transactions", [])
        for tx_id in removed_transactions:
            await db.execute(
                "DELETE FROM transactions WHERE transaction_id = :tx_id",
                {"tx_id": tx_id}
            )
        await db.commit()
        logger.info(f"Removed {len(removed_transactions)} transactions for item {item_id}")

async def handle_item_webhook(webhook_data: Dict[str, Any], db: AsyncSession):
    """Handle item webhooks"""
    webhook_code = webhook_data.get("webhook_code")
    item_id = webhook_data.get("item_id")
    
    if webhook_code == "ERROR":
        error = webhook_data.get("error", {})
        logger.error(
            f"Plaid item error: {error}",
            extra={"item_id": item_id}
        )
        
        # Update item status
        await db.execute(
            "UPDATE plaid_items SET status = 'error' WHERE item_id = :item_id",
            {"item_id": item_id}
        )
        await db.commit()
        
    elif webhook_code == "PENDING_EXPIRATION":
        logger.warning(f"Access token pending expiration: {item_id}")
        # Notify user to reconnect their account
        
    elif webhook_code == "USER_PERMISSION_REVOKED":
        logger.info(f"User permission revoked: {item_id}")
        await db.execute(
            "UPDATE plaid_items SET status = 'revoked' WHERE item_id = :item_id",
            {"item_id": item_id}
        )
        await db.commit()

async def handle_holdings_webhook(webhook_data: Dict[str, Any], db: AsyncSession):
    """Handle investments webhooks"""
    webhook_code = webhook_data.get("webhook_code")
    item_id = webhook_data.get("item_id")
    logger.info(f"Holdings webhook received: {webhook_code} for item {item_id}")