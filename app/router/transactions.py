from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.plaid_client import plaid_client
from app.encryption import encryption_service
from app.models import Transaction, SecurityLog
from app.utils.security import get_current_user
from app.middleware.rate_limiter import rate_limit

router = APIRouter(prefix="/transactions", tags=["transactions"])
logger = logging.getLogger(__name__)

@router.get("/sync/{item_id}")
@rate_limit("30/minute")
async def sync_transactions(
    item_id: str,
    cursor: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Sync transactions for a Plaid item using the sync API
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
        
        # Sync transactions
        sync_response = await plaid_client.get_transactions_sync(access_token, cursor)
        
        # Store new transactions in database
        added_transactions = sync_response.get("added", [])
        for tx_data in added_transactions:
            transaction = Transaction(
                transaction_id=tx_data["transaction_id"],
                plaid_item_id=item_id,
                user_id=current_user.get("user_id"),
                amount=tx_data["amount"],
                currency=tx_data["iso_currency_code"],
                name=tx_data["name"],
                merchant_name=tx_data.get("merchant_name"),
                date=tx_data["date"],
                category=tx_data.get("category", []),
                pending=tx_data["pending"],
                payment_channel=tx_data["payment_channel"]
            )
            db.add(transaction)
        
        modified_transactions = sync_response.get("modified", [])
        for tx_data in modified_transactions:
            # Update existing transactions
            await db.execute(
                """UPDATE transactions 
                   SET amount = :amount, name = :name, merchant_name = :merchant_name,
                       category = :category, pending = :pending
                   WHERE transaction_id = :transaction_id""",
                {
                    "amount": tx_data["amount"],
                    "name": tx_data["name"],
                    "merchant_name": tx_data.get("merchant_name"),
                    "category": tx_data.get("category", []),
                    "pending": tx_data["pending"],
                    "transaction_id": tx_data["transaction_id"]
                }
            )
        
        removed_transactions = sync_response.get("removed", [])
        for tx_data in removed_transactions:
            # Remove transactions
            await db.execute(
                "DELETE FROM transactions WHERE transaction_id = :transaction_id",
                {"transaction_id": tx_data["transaction_id"]}
            )
        
        await db.commit()
        
        logger.info(
            f"Transactions synced for item {item_id}",
            extra={
                "added": len(added_transactions),
                "modified": len(modified_transactions),
                "removed": len(removed_transactions)
            }
        )
        
        return {
            "added": len(added_transactions),
            "modified": len(modified_transactions),
            "removed": len(removed_transactions),
            "next_cursor": sync_response.get("next_cursor"),
            "has_more": sync_response.get("has_more", False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync transactions"
        )

@router.get("/{item_id}")
@rate_limit("30/minute")
async def get_transactions(
    item_id: str,
    start_date: str = Query(..., regex=r'^\d{4}-\d{2}-\d{2}$'),
    end_date: str = Query(..., regex=r'^\d{4}-\d{2}-\d{2}$'),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get transactions from database with date range
    """
    try:
        # Validate date range
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        if (end - start).days > 730:  # ~2 years
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range cannot exceed 730 days"
            )
        
        if start > end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        # Get transactions from database
        result = await db.execute(
            """SELECT * FROM transactions 
               WHERE plaid_item_id = :item_id 
               AND user_id = :user_id
               AND date BETWEEN :start_date AND :end_date
               ORDER BY date DESC
               LIMIT :limit OFFSET :offset""",
            {
                "item_id": item_id,
                "user_id": current_user.get("user_id"),
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
                "offset": offset
            }
        )
        transactions = result.fetchall()
        
        # Get total count
        count_result = await db.execute(
            """SELECT COUNT(*) FROM transactions 
               WHERE plaid_item_id = :item_id 
               AND user_id = :user_id
               AND date BETWEEN :start_date AND :end_date""",
            {
                "item_id": item_id,
                "user_id": current_user.get("user_id"),
                "start_date": start_date,
                "end_date": end_date
            }
        )
        total_count = count_result.scalar()
        
        return {
            "transactions": [
                {
                    "id": tx.id,
                    "transaction_id": tx.transaction_id,
                    "amount": tx.amount,
                    "currency": tx.currency,
                    "name": tx.name,
                    "merchant_name": tx.merchant_name,
                    "date": tx.date,
                    "category": tx.category,
                    "pending": tx.pending,
                    "payment_channel": tx.payment_channel
                } for tx in transactions
            ],
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(transactions)) < total_count
            }
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format"
        )
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch transactions"
        )