from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.services.ai_service import ai_service
from app.models import Transaction, SecurityLog
from app.utils.security import get_current_user
from app.middleware.rate_limiter import rate_limit

router = APIRouter(prefix="/ai", tags=["ai-insights"])
logger = logging.getLogger(__name__)

@router.get("/wellness-analysis/{item_id}")
@rate_limit("20/minute")
async def get_wellness_analysis(
    item_id: str,
    days: int = Query(90, ge=7, le=365),
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get AI-powered wellness analysis combining financial and health insights
    """
    try:
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get transactions from database
        result = await db.execute(
            """SELECT * FROM transactions 
               WHERE plaid_item_id = :item_id 
               AND user_id = :user_id
               AND date BETWEEN :start_date AND :end_date""",
            {
                "item_id": item_id,
                "user_id": current_user.get("user_id"),
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            }
        )
        transactions = result.fetchall()
        
        if not transactions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No transaction data found for analysis"
            )
        
        # Convert to list of dicts for AI processing
        transactions_list = [
            {
                "transaction_id": tx.transaction_id,
                "amount": float(tx.amount),
                "date": tx.date,
                "category": tx.category,
                "name": tx.name,
                "merchant_name": tx.merchant_name,
                "pending": tx.pending
            } for tx in transactions
        ]
        
        # Get health data (mock for now - integrate with wearables later)
        health_data = await get_mock_health_data(current_user.get("user_id"), start_date, end_date)
        
        # Perform AI analysis
        analysis = await ai_service.analyze_financial_health_correlations(
            transactions_list, 
            health_data
        )
        
        # Log AI analysis event
        security_log = SecurityLog(
            event_type="ai_wellness_analysis",
            user_id=current_user.get("user_id"),
            details=f"AI wellness analysis for item {item_id}",
            severity="info"
        )
        db.add(security_log)
        await db.commit()
        
        logger.info(f"AI wellness analysis completed for user {current_user.get('user_id')}")
        
        return {
            "analysis_id": f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timeframe": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "days": days
            },
            "data_summary": {
                "transaction_count": len(transactions),
                "health_data_points": len(health_data) if health_data else 0
            },
            **analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI wellness analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI analysis failed"
        )

@router.get("/spending-patterns/{item_id}")
@rate_limit("30/minute")
async def analyze_spending_patterns(
    item_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    AI-powered spending pattern analysis
    """
    try:
        # Get recent transactions (last 60 days)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=60)
        
        result = await db.execute(
            """SELECT * FROM transactions 
               WHERE plaid_item_id = :item_id 
               AND user_id = :user_id
               AND date BETWEEN :start_date AND :end_date""",
            {
                "item_id": item_id,
                "user_id": current_user.get("user_id"),
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            }
        )
        transactions = result.fetchall()
        
        if not transactions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No transaction data found for pattern analysis"
            )
        
        # Convert for analysis
        transactions_list = [
            {
                "amount": float(tx.amount),
                "date": tx.date,
                "category": tx.category,
                "name": tx.name
            } for tx in transactions
        ]
        
        # Analyze patterns using AI service
        features = ai_service._extract_financial_features(pd.DataFrame(transactions_list))
        patterns = ai_service._detect_spending_patterns(features)
        
        return {
            "timeframe": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            },
            "detected_patterns": patterns,
            "pattern_count": len(patterns),
            "primary_concern": patterns[0]["type"] if patterns else "NO_PATTERNS_DETECTED"
        }
        
    except Exception as e:
        logger.error(f"Spending pattern analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pattern analysis failed"
        )

@router.get("/recommendations/{item_id}")
@rate_limit("25/minute")
async def get_ai_recommendations(
    item_id: str,
    category: Optional[str] = Query(None, description="Filter by category: FINANCIAL, HEALTH, LIFESTYLE"),
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get personalized AI recommendations for improving financial and health wellness
    """
    try:
        # Get analysis data first
        analysis = await get_wellness_analysis(item_id, 90, current_user, db)
        
        # Extract recommendations from analysis
        all_recommendations = analysis.get("recommendations", [])
        
        # Filter by category if specified
        if category:
            filtered_recommendations = [
                rec for rec in all_recommendations 
                if rec.get("category") == category
            ]
        else:
            filtered_recommendations = all_recommendations
        
        # Prioritize recommendations
        high_priority = [r for r in filtered_recommendations if r.get("priority") == "high"]
        medium_priority = [r for r in filtered_recommendations if r.get("priority") == "medium"]
        low_priority = [r for r in filtered_recommendations if r.get("priority") == "low"]
        
        prioritized_recommendations = high_priority + medium_priority + low_priority
        
        return {
            "total_recommendations": len(prioritized_recommendations),
            "by_priority": {
                "high": len(high_priority),
                "medium": len(medium_priority),
                "low": len(low_priority)
            },
            "recommendations": prioritized_recommendations,
            "wellness_score": analysis.get("wellness_score", {}),
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"AI recommendations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations"
        )

@router.get("/health-correlations/{item_id}")
@rate_limit("15/minute")
async def get_health_correlations(
    item_id: str,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed health-financial correlation analysis
    """
    try:
        analysis = await get_wellness_analysis(item_id, 90, current_user, db)
        
        correlations = analysis.get("correlations", {})
        insights = analysis.get("ai_insights", [])
        
        return {
            "correlation_analysis": correlations,
            "key_insights": insights,
            "strongest_correlation": self._find_strongest_correlation(correlations),
            "health_impact_summary": self._summarize_health_impact(correlations)
        }
        
    except Exception as e:
        logger.error(f"Health correlation analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Correlation analysis failed"
        )

def _find_strongest_correlation(self, correlations: Dict[str, Any]) -> Dict[str, Any]:
    """Find the strongest correlation in the analysis"""
    strongest = {"correlation": 0, "factor": "Unknown", "impact": "No significant correlations"}
    
    for category, items in correlations.items():
        if isinstance(items, list):
            for item in items:
                corr_value = abs(item.get("correlation", 0))
                if corr_value > strongest["correlation"]:
                    strongest = {
                        "correlation": corr_value,
                        "factor": item.get("factor", "Unknown"),
                        "impact": item.get("impact", "Unknown"),
                        "category": category
                    }
    
    return strongest

def _summarize_health_impact(self, correlations: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize overall health impact"""
    sleep_impact = len(correlations.get("sleep_quality_correlations", []))
    stress_impact = correlations.get("financial_stress_impact", 0)
    activity_impact = len(correlations.get("activity_level_correlations", []))
    nutrition_impact = len(correlations.get("nutrition_impact", []))
    
    return {
        "sleep_quality_risks": sleep_impact,
        "stress_level_impact": stress_impact,
        "physical_activity_risks": activity_impact,
        "nutrition_concerns": nutrition_impact,
        "overall_health_risk": min(100, (sleep_impact * 20 + stress_impact * 30 + activity_impact * 15 + nutrition_impact * 15))
    }

async def get_mock_health_data(user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Mock health data - in production, integrate with Fitbit/Google Fit/Apple Health
    """
    # This would be replaced with real health API integrations
    health_data = []
    current_date = start_date
    
    while current_date <= end_date:
        # Mock sleep data
        health_data.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "sleep_hours": np.random.normal(7, 1.2),  # Average 7 hours, some variance
            "sleep_quality": np.random.randint(60, 95),  # Quality score 60-95
            "steps": np.random.randint(4000, 12000),  # Daily steps
            "stress_level": np.random.randint(1, 10),  # Stress 1-10 scale
            "active_minutes": np.random.randint(20, 90)  # Active minutes
        })
        current_date += timedelta(days=1)
    
    return health_data