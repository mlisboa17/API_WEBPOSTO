"""
Priority Engine — Decision Scoring Algorithm

Calculates priority scores for decisions based on:
- Financial impact (30%)
- Urgency (25%)
- Confidence (20%)
- Ease of execution (15%)
- Time to resolve (10%)

Algorithm produces a score from 0-100 for ranking decisions.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .schemas import ActionPriority, ActionType

logger = logging.getLogger(__name__)


@dataclass
class PriorityWeights:
    """Weights for priority calculation."""
    financial_impact: float = 0.30
    urgency: float = 0.25
    confidence: float = 0.20
    ease: float = 0.15
    time: float = 0.10
    
    def validate(self):
        """Validate weights sum to 1.0."""
        total = (self.financial_impact + self.urgency + self.confidence + 
                 self.ease + self.time)
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


class PriorityEngine:
    """
    Engine to calculate priority scores for decisions.
    
    Combines multiple factors into a single priority score (0-100)
    for ranking and prioritizing decisions.
    """
    
    # Score thresholds for priority levels
    CRITICAL_THRESHOLD = 80
    HIGH_THRESHOLD = 60
    MEDIUM_THRESHOLD = 40
    
    def __init__(self, weights: Optional[PriorityWeights] = None):
        self.weights = weights or PriorityWeights()
        self.weights.validate()
        
        # Financial impact tiers (in BRL)
        self.financial_tiers = [
            (100000, 100),  # > 100k = max score
            (50000, 90),
            (20000, 80),
            (10000, 70),
            (5000, 60),
            (2000, 50),
            (1000, 40),
            (500, 30),
            (100, 20),
            (0, 10),  # < 100 = min score
        ]
        
        # Time to resolve scoring (minutes)
        self.time_scores = [
            (15, 100),   # < 15 min = max
            (30, 85),
            (60, 70),
            (120, 55),
            (240, 40),
            (480, 25),
            (float('inf'), 10),  # > 8 hours = min
        ]
        
    def calculate_score(
        self,
        financial_value: float,
        urgency_score: float,
        confidence: float,
        action_type: ActionType,
        priority: ActionPriority,
        time_to_resolve: Optional[int] = None,
        custom_weights: Optional[PriorityWeights] = None
    ) -> Dict[str, float]:
        """
        Calculate priority score for a decision.
        
        Args:
            financial_value: Expected financial value (R$)
            urgency_score: Urgency score (0-1)
            confidence: Confidence score (0-1)
            action_type: Type of action
            priority: Priority level
            time_to_resolve: Estimated minutes to resolve
            custom_weights: Optional custom weights
            
        Returns:
            Dictionary with all component scores and total
        """
        try:
            weights = custom_weights or self.weights
            
            # Calculate individual component scores
            financial_impact_score = self._score_financial_impact(financial_value)
            urgency_component_score = self._score_urgency(urgency_score, priority, action_type)
            confidence_component_score = self._score_confidence(confidence)
            ease_score = self._score_ease(time_to_resolve)
            time_score = self._score_time(time_to_resolve)
            
            # Calculate weighted total
            total_score = (
                financial_impact_score * weights.financial_impact +
                urgency_component_score * weights.urgency +
                confidence_component_score * weights.confidence +
                ease_score * weights.ease +
                time_score * weights.time
            )
            
            # Apply priority multipliers
            total_score = self._apply_priority_multiplier(total_score, priority, action_type)
            
            # Cap at 100
            total_score = min(100, total_score)
            
            return {
                "total_score": round(total_score, 1),
                "financial_impact_score": round(financial_impact_score, 1),
                "urgency_score": round(urgency_component_score, 1),
                "confidence_score": round(confidence_component_score, 1),
                "ease_score": round(ease_score, 1),
                "time_score": round(time_score, 1),
            }
            
        except Exception as e:
            logger.error(f"Error calculating priority score: {e}")
            return {
                "total_score": 50.0,
                "financial_impact_score": 50.0,
                "urgency_score": 50.0,
                "confidence_score": 50.0,
                "ease_score": 50.0,
                "time_score": 50.0,
            }
    
    def _score_financial_impact(self, value: float) -> float:
        """
        Score financial impact (0-100).
        
        Uses tiered scoring based on absolute value.
        """
        absolute_value = abs(value)
        
        for threshold, score in self.financial_tiers:
            if absolute_value >= threshold:
                return score
        
        return 0
    
    def _score_urgency(
        self,
        urgency: float,
        priority: ActionPriority,
        action_type: ActionType
    ) -> float:
        """
        Score urgency (0-100).
        
        Combines base urgency with priority and action type.
        """
        # Base urgency score (0-100)
        base_score = urgency * 100
        
        # Priority multipliers
        priority_multipliers = {
            ActionPriority.CRITICAL: 1.2,
            ActionPriority.HIGH: 1.0,
            ActionPriority.MEDIUM: 0.8,
            ActionPriority.LOW: 0.6,
        }
        multiplier = priority_multipliers.get(priority, 1.0)
        
        # Action type adjustments
        type_adjustments = {
            ActionType.URGENT: 15,
            ActionType.RECOVER: 10,
            ActionType.OPTIMIZE: 0,
            ActionType.REVIEW: -5,
            ActionType.MONITOR: -10,
        }
        adjustment = type_adjustments.get(action_type, 0)
        
        score = (base_score * multiplier) + adjustment
        return max(0, min(100, score))
    
    def _score_confidence(self, confidence: float) -> float:
        """
        Score confidence (0-100).
        
        Higher confidence = higher score.
        Below 0.6 confidence gets penalized.
        """
        if confidence < 0.6:
            # Penalize low confidence
            return confidence * 50  # 0-30 range
        elif confidence < 0.8:
            # Medium confidence
            return 30 + (confidence - 0.6) * 250  # 30-80 range
        else:
            # High confidence
            return 80 + (confidence - 0.8) * 100  # 80-100 range
    
    def _score_ease(self, time_to_resolve: Optional[int]) -> float:
        """
        Score ease of execution (0-100).
        
        Easier = higher score.
        Based on time to resolve.
        """
        if time_to_resolve is None:
            return 50.0  # Unknown = middle score
        
        # Shorter time = higher score (inverse relationship)
        for threshold, score in self.time_scores:
            if time_to_resolve <= threshold:
                return score
        
        return 0
    
    def _score_time(self, time_to_resolve: Optional[int]) -> float:
        """
        Score time factor (0-100).
        
        Rewards quick wins but doesn't penalize important long-term actions.
        Uses a curve that peaks at quick actions but doesn't drop to zero.
        """
        if time_to_resolve is None:
            return 50.0
        
        if time_to_resolve <= 15:
            return 100  # Quick win
        elif time_to_resolve <= 60:
            return 85   # Under an hour
        elif time_to_resolve <= 240:
            return 70   # Under 4 hours
        elif time_to_resolve <= 480:
            return 55   # Under 8 hours
        else:
            return 40   # Longer actions still get base score
    
    def _apply_priority_multiplier(
        self,
        score: float,
        priority: ActionPriority,
        action_type: ActionType
    ) -> float:
        """
        Apply final priority multipliers.
        
        Critical items get boosted, low priority gets slightly reduced.
        """
        # Base multipliers
        multipliers = {
            ActionPriority.CRITICAL: 1.15,
            ActionPriority.HIGH: 1.05,
            ActionPriority.MEDIUM: 1.0,
            ActionPriority.LOW: 0.95,
        }
        
        multiplier = multipliers.get(priority, 1.0)
        
        # Extra boost for urgent action types at critical priority
        if action_type == ActionType.URGENT and priority == ActionPriority.CRITICAL:
            multiplier += 0.1
        
        return score * multiplier
    
    def get_priority_level(self, total_score: float) -> ActionPriority:
        """
        Determine priority level from total score.
        
        Args:
            total_score: Priority score (0-100)
            
        Returns:
            ActionPriority level
        """
        if total_score >= self.CRITICAL_THRESHOLD:
            return ActionPriority.CRITICAL
        elif total_score >= self.HIGH_THRESHOLD:
            return ActionPriority.HIGH
        elif total_score >= self.MEDIUM_THRESHOLD:
            return ActionPriority.MEDIUM
        else:
            return ActionPriority.LOW
    
    def rank_decisions(
        self,
        decisions: list,
        key_func=None
    ) -> list:
        """
        Rank decisions by priority score.
        
        Args:
            decisions: List of decision objects
            key_func: Optional function to extract score from decision
            
        Returns:
            Sorted list of decisions (highest score first)
        """
        if key_func is None:
            key_func = lambda d: getattr(d, 'total_score', 0)
        
        return sorted(decisions, key=key_func, reverse=True)
    
    def filter_by_confidence(
        self,
        decisions: list,
        min_confidence: float = 0.60
    ) -> list:
        """
        Filter decisions by minimum confidence.
        
        Args:
            decisions: List of decision objects
            min_confidence: Minimum confidence threshold (0-1)
            
        Returns:
            Filtered list of decisions
        """
        return [
            d for d in decisions
            if getattr(d, 'confidence', 0) >= min_confidence
        ]
    
    def get_top_n(
        self,
        decisions: list,
        n: int = 5,
        min_confidence: Optional[float] = 0.60
    ) -> list:
        """
        Get top N decisions by priority.
        
        Args:
            decisions: List of decision objects
            n: Number of top decisions to return
            min_confidence: Optional minimum confidence filter
            
        Returns:
            Top N decisions
        """
        # Filter by confidence if specified
        if min_confidence is not None:
            decisions = self.filter_by_confidence(decisions, min_confidence)
        
        # Rank and return top N
        ranked = self.rank_decisions(decisions)
        return ranked[:n]