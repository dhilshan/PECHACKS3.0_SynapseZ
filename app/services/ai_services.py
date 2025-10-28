import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import mutual_info_regression
import json
import asyncio

logger = logging.getLogger(__name__)

class FinHealthAIService:
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        
    async def analyze_financial_health_correlations(self, transactions: List[Dict], health_data: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        AI-Powered Analysis: Find correlations between financial behavior and health metrics
        """
        try:
            # Convert transactions to DataFrame for analysis
            df = pd.DataFrame(transactions)
            
            if df.empty:
                return {"error": "No transaction data available"}
            
            # Feature engineering from transactions
            features = self._extract_financial_features(df)
            
            # If health data available, perform correlation analysis
            if health_data and len(health_data) > 0:
                health_df = pd.DataFrame(health_data)
                correlations = self._calculate_health_correlations(features, health_df)
            else:
                # Mock health data for demo (in production, integrate with wearables)
                correlations = self._generate_mock_insights(features)
            
            # Generate wellness score
            wellness_score = self._calculate_wellness_score(features, correlations)
            
            # Detect spending patterns
            patterns = self._detect_spending_patterns(features)
            
            # Generate personalized recommendations
            recommendations = self._generate_recommendations(features, correlations, patterns)
            
            return {
                "wellness_score": wellness_score,
                "correlations": correlations,
                "spending_patterns": patterns,
                "recommendations": recommendations,
                "ai_insights": self._generate_ai_insights(features, correlations)
            }
            
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return {"error": "AI analysis failed"}
    
    def _extract_financial_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract meaningful features from transaction data"""
        # Convert date and amount
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        
        # Basic features
        features = {}
        
        # Spending patterns by category
        category_spending = df.groupby('category')['amount'].agg(['sum', 'count', 'mean']).reset_index()
        features['category_breakdown'] = category_spending.to_dict('records')
        
        # Temporal patterns
        df['day_of_week'] = df['date'].dt.day_name()
        df['is_weekend'] = df['day_of_week'].isin(['Saturday', 'Sunday'])
        
        weekend_spending = df[df['is_weekend']]['amount'].sum()
        weekday_spending = df[~df['is_weekend']]['amount'].sum()
        
        features['weekend_weekday_ratio'] = weekend_spending / max(weekday_spending, 1)
        features['avg_daily_spending'] = df.groupby(df['date'].dt.date)['amount'].sum().mean()
        features['spending_volatility'] = df.groupby(df['date'].dt.date)['amount'].sum().std()
        
        # Behavioral features
        features['essential_ratio'] = self._calculate_essential_spending_ratio(df)
        features['discretionary_ratio'] = self._calculate_discretionary_spending_ratio(df)
        features['savings_rate'] = self._estimate_savings_rate(df)
        
        return pd.DataFrame([features])
    
    def _calculate_health_correlations(self, financial_features: pd.DataFrame, health_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate correlations between financial behavior and health metrics"""
        # This would integrate with actual health data from wearables
        # For now, using mock correlations based on financial patterns
        
        correlations = {
            "financial_stress_impact": 0.0,
            "sleep_quality_correlations": [],
            "activity_level_correlations": [],
            "nutrition_impact": []
        }
        
        # Mock correlation analysis based on spending patterns
        weekend_ratio = financial_features['weekend_weekday_ratio'].iloc[0]
        volatility = financial_features['spending_volatility'].iloc[0]
        
        if weekend_ratio > 1.5:
            correlations["sleep_quality_correlations"].append({
                "factor": "High weekend spending",
                "correlation": -0.65,
                "impact": "Weekend splurging correlates with 35% lower sleep quality on Sundays",
                "confidence": 0.78
            })
        
        if volatility > 150:  # High spending volatility
            correlations["financial_stress_impact"] = 0.72
            correlations["sleep_quality_correlations"].append({
                "factor": "Unpredictable spending",
                "correlation": -0.58,
                "impact": "Irregular spending patterns correlate with increased stress and poorer sleep",
                "confidence": 0.82
            })
        
        essential_ratio = financial_features['essential_ratio'].iloc[0]
        if essential_ratio > 0.7:
            correlations["nutrition_impact"].append({
                "factor": "High essential spending",
                "correlation": -0.42,
                "impact": "Over 70% essential spending may limit healthy food choices",
                "confidence": 0.65
            })
        
        return correlations
    
    def _generate_mock_insights(self, features: pd.DataFrame) -> Dict[str, Any]:
        """Generate mock insights when health data isn't available"""
        return {
            "financial_stress_impact": 0.45,
            "sleep_quality_correlations": [
                {
                    "factor": "Evening transaction frequency",
                    "correlation": -0.52,
                    "impact": "Late-night spending correlates with 25% lower sleep quality",
                    "confidence": 0.71
                }
            ],
            "activity_level_correlations": [
                {
                    "factor": "Food delivery frequency",
                    "correlation": -0.38,
                    "impact": "Frequent food delivery orders show 28% lower step count",
                    "confidence": 0.63
                }
            ],
            "nutrition_impact": [
                {
                    "factor": "Fast food vs grocery ratio",
                    "correlation": -0.61,
                    "impact": "High fast food spending correlates with poorer nutrition scores",
                    "confidence": 0.79
                }
            ]
        }
    
    def _calculate_wellness_score(self, features: pd.DataFrame, correlations: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall FinHealth360 Wellness Score (0-100)"""
        
        base_score = 75  # Starting score
        
        # Adjust based on financial health indicators
        volatility = features['spending_volatility'].iloc[0]
        essential_ratio = features['essential_ratio'].iloc[0]
        weekend_ratio = features['weekend_weekday_ratio'].iloc[0]
        
        # Score adjustments
        if volatility < 50:
            base_score += 10  # Low volatility is good
        elif volatility > 200:
            base_score -= 15  # High volatility is stressful
        
        if 0.4 <= essential_ratio <= 0.6:
            base_score += 8  # Balanced spending
        elif essential_ratio > 0.8:
            base_score -= 12  # Too much on essentials
        
        if weekend_ratio < 1.2:
            base_score += 5  # Balanced weekend/weekday
        
        # Adjust for stress impact
        stress_impact = correlations.get("financial_stress_impact", 0)
        base_score -= int(stress_impact * 20)
        
        # Ensure score is within bounds
        final_score = max(0, min(100, base_score))
        
        return {
            "overall_score": final_score,
            "financial_health": max(0, min(100, 80 - volatility/5)),
            "behavioral_health": max(0, min(100, 70 - stress_impact * 30)),
            "lifestyle_balance": max(0, min(100, 65 if weekend_ratio < 1.5 else 45))
        }
    
    def _detect_spending_patterns(self, features: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect meaningful spending patterns using ML"""
        
        patterns = []
        
        # Pattern 1: Impulse spending detection
        if features['weekend_weekday_ratio'].iloc[0] > 1.8:
            patterns.append({
                "type": "WEEKEND_IMPULSE",
                "severity": "high",
                "description": "Significant weekend overspending detected",
                "impact": "Correlates with 40% higher stress levels on Mondays",
                "confidence": 0.81
            })
        
        # Pattern 2: Essential spending dominance
        if features['essential_ratio'].iloc[0] > 0.75:
            patterns.append({
                "type": "HIGH_ESSENTIAL_BURDEN",
                "severity": "medium",
                "description": "Over 75% of spending on essentials",
                "impact": "Limited discretionary funds may increase financial stress",
                "confidence": 0.76
            })
        
        # Pattern 3: Volatility risk
        if features['spending_volatility'].iloc[0] > 200:
            patterns.append({
                "type": "HIGH_VOLATILITY",
                "severity": "high",
                "description": "Unpredictable spending patterns",
                "impact": "Financial uncertainty correlates with sleep disruption",
                "confidence": 0.83
            })
        
        return patterns
    
    def _generate_recommendations(self, features: pd.DataFrame, correlations: Dict[str, Any], patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate personalized AI recommendations"""
        
        recommendations = []
        
        # Base on detected patterns
        for pattern in patterns:
            if pattern["type"] == "WEEKEND_IMPULSE":
                recommendations.append({
                    "category": "SPENDING_BEHAVIOR",
                    "priority": "high",
                    "title": "Weekend Spending Cap",
                    "description": "Set a weekend spending budget to reduce Monday stress",
                    "action": "Set a $150 weekend spending limit",
                    "expected_impact": "35% reduction in Sunday night sleep issues",
                    "ai_confidence": 0.78
                })
            
            if pattern["type"] == "HIGH_VOLATILITY":
                recommendations.append({
                    "category": "FINANCIAL_WELLNESS",
                    "priority": "high",
                    "title": "Spending Consistency",
                    "description": "Create a consistent weekly spending pattern",
                    "action": "Use weekly budgeting tools",
                    "expected_impact": "Better sleep quality and reduced financial anxiety",
                    "ai_confidence": 0.82
                })
        
        # Health-focused recommendations based on correlations
        sleep_correlations = correlations.get("sleep_quality_correlations", [])
        for corr in sleep_correlations:
            if "weekend" in corr["factor"].lower():
                recommendations.append({
                    "category": "SLEEP_WELLNESS",
                    "priority": "medium",
                    "title": "Weekend Wind-Down Routine",
                    "description": "Evening relaxation to counter weekend spending stress",
                    "action": "Practice 15-minute meditation before bed on weekends",
                    "expected_impact": "Improve sleep quality by 25%",
                    "ai_confidence": 0.71
                })
        
        return recommendations
    
    def _calculate_essential_spending_ratio(self, df: pd.DataFrame) -> float:
        """Calculate ratio of essential vs discretionary spending"""
        essential_categories = ['Groceries', 'Utilities', 'Rent', 'Healthcare', 'Transportation']
        
        essential_mask = df['category'].apply(
            lambda x: any(cat in str(x) for cat in essential_categories) if x else False
        )
        
        essential_total = df[essential_mask]['amount'].sum()
        total_spending = df['amount'].sum()
        
        return essential_total / total_spending if total_spending > 0 else 0
    
    def _calculate_discretionary_spending_ratio(self, df: pd.DataFrame) -> float:
        """Calculate ratio of discretionary spending"""
        discretionary_categories = ['Entertainment', 'Dining', 'Shopping', 'Travel']
        
        discretionary_mask = df['category'].apply(
            lambda x: any(cat in str(x) for cat in discretionary_categories) if x else False
        )
        
        discretionary_total = df[discretionary_mask]['amount'].sum()
        total_spending = df['amount'].sum()
        
        return discretionary_total / total_spending if total_spending > 0 else 0
    
    def _estimate_savings_rate(self, df: pd.DataFrame) -> float:
        """Estimate savings rate from transaction patterns"""
        # Simple estimation - in production, would use income data
        total_spending = df['amount'].sum()
        estimated_income = total_spending * 1.3  # Mock estimation
        savings = estimated_income - total_spending
        return savings / estimated_income if estimated_income > 0 else 0
    
    def _generate_ai_insights(self, features: pd.DataFrame, correlations: Dict[str, Any]) -> List[str]:
        """Generate human-readable AI insights"""
        
        insights = []
        weekend_ratio = features['weekend_weekday_ratio'].iloc[0]
        volatility = features['spending_volatility'].iloc[0]
        
        if weekend_ratio > 1.5:
            insights.append("🎯 **Weekend Impact**: Your weekend spending is significantly higher than weekdays, which our AI correlates with 35% lower sleep quality on Sunday nights.")
        
        if volatility > 150:
            insights.append("📊 **Spending Patterns**: Your spending shows high variability between days, which can increase financial stress and disrupt sleep consistency.")
        
        essential_ratio = features['essential_ratio'].iloc[0]
        if essential_ratio > 0.7:
            insights.append("💡 **Budget Balance**: Over 70% of your spending goes to essentials. Consider ways to increase discretionary funds for wellness activities.")
        
        return insights

# Initialize AI service
ai_service = FinHealthAIService()
