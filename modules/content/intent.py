"""
Enhanced Search Intent Classification Module

This module provides advanced search intent classification with improved accuracy,
confidence scoring, and extensibility.
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
from urllib.parse import urlparse
from dataclasses import dataclass
from collections import defaultdict


class IntentType(Enum):
    """Search intent types with descriptions."""
    TRANSACTIONAL = "transactional"
    COMMERCIAL = "commercial" 
    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"
    
    def __str__(self) -> str:
        return self.value


@dataclass
class IntentResult:
    """Result of intent classification."""
    primary_intent: IntentType
    confidence: float
    intent_scores: Dict[str, int]
    matched_signals: Dict[str, List[str]]
    url_signals: List[str]
    reasoning: str


class IntentClassifier:
    """Advanced search intent classifier with weighted keywords and patterns."""
    
    def __init__(self):
        """Initialize classifier with enhanced keyword patterns."""
        self.intent_patterns = {
            IntentType.TRANSACTIONAL: {
                'strong': [
                    r'\b(buy|purchase|order|checkout|cart|payment)\b',
                    r'\b(book|booking|reserve|subscription)\b',
                    r'\b(price|pricing|cost|quote|estimate)\b',
                    r'\b(download|install|get|acquire)\b',
                    r'\b(trial|demo|signup|sign up|register)\b',
                    r'\b(hire|employ|engage|contract)\b',
                ],
                'medium': [
                    r'\b(deal|offer|discount|coupon|sale)\b',
                    r'\b(free|cheap|affordable|budget)\b',
                    r'\b(shop|store|market|vendor)\b',
                ],
                'weak': [
                    r'\b(get started|begin|start)\b',
                    r'\b(contact|call|phone)\b',
                ]
            },
            IntentType.COMMERCIAL: {
                'strong': [
                    r'\b(best|top|leading|premier)\b',
                    r'\b(vs|versus|compare|comparison)\b',
                    r'\b(review|reviews|rating|ratings)\b',
                    r'\b(alternative|alternatives|options)\b',
                ],
                'medium': [
                    r'\b(features|benefits|advantages)\b',
                    r'\b(pros|cons|disadvantages)\b',
                    r'\b(recommendation|recommend)\b',
                    r'\b(evaluation|assess|analysis)\b',
                ],
                'weak': [
                    r'\b(quality|performance|reliability)\b',
                    r'\b(popular|trending|latest)\b',
                ]
            },
            IntentType.INFORMATIONAL: {
                'strong': [
                    r'\b(how|what|why|when|where|which)\b',
                    r'\b(guide|tutorial|instruction|manual)\b',
                    r'\b(learn|study|understand|explain)\b',
                    r'\b(definition|meaning|concept)\b',
                ],
                'medium': [
                    r'\b(tips|advice|help|assistance)\b',
                    r'\b(examples|samples|instances)\b',
                    r'\b(strategy|method|approach|technique)\b',
                    r'\b(steps|process|procedure)\b',
                ],
                'weak': [
                    r'\b(information|info|details|facts)\b',
                    r'\b(overview|introduction|basics)\b',
                    r'\b(faq|questions|answers)\b',
                ]
            },
            IntentType.NAVIGATIONAL: {
                'strong': [
                    r'\b(login|log in|sign in|signin)\b',
                    r'\b(dashboard|account|profile)\b',
                    r'\b(homepage|home|main page)\b',
                    r'\b(contact|about|support)\b',
                ],
                'medium': [
                    r'\b(help center|customer service)\b',
                    r'\b(terms|privacy|policy)\b',
                    r'\b(location|address|directions)\b',
                    r'\b(career|jobs|employment)\b',
                ],
                'weak': [
                    r'\b(site|website|portal|platform)\b',
                    r'\b(official|main|primary)\b',
                ]
            }
        }
        
        # URL pattern weights
        self.url_patterns = {
            IntentType.TRANSACTIONAL: {
                'strong': ['/pricing', '/plans', '/buy', '/order', '/checkout', '/cart', '/purchase'],
                'medium': ['/trial', '/demo', '/signup', '/register', '/subscribe'],
                'weak': ['/contact', '/quote', '/estimate']
            },
            IntentType.COMMERCIAL: {
                'strong': ['/compare', '/vs', '/versus', '/reviews', '/alternatives'],
                'medium': ['/features', '/benefits', '/pricing-comparison'],
                'weak': ['/products', '/services', '/solutions']
            },
            IntentType.INFORMATIONAL: {
                'strong': ['/blog', '/guide', '/tutorial', '/how-to', '/learn'],
                'medium': ['/help', '/support', '/faq', '/documentation'],
                'weak': ['/news', '/articles', '/resources']
            },
            IntentType.NAVIGATIONAL: {
                'strong': ['/login', '/signin', '/dashboard', '/account', '/profile'],
                'medium': ['/about', '/contact', '/home', '/index'],
                'weak': ['/sitemap', '/directory']
            }
        }
        
        # Weight multipliers
        self.pattern_weights = {'strong': 3, 'medium': 2, 'weak': 1}
        self.url_weights = {'strong': 4, 'medium': 2, 'weak': 1}

    def _extract_text_signals(self, text: str) -> Tuple[Dict[IntentType, int], Dict[IntentType, List[str]]]:
        """Extract and score intent signals from text."""
        text_lower = text.lower()
        scores = defaultdict(int)
        matches = defaultdict(list)
        
        for intent_type, strength_patterns in self.intent_patterns.items():
            for strength, patterns in strength_patterns.items():
                weight = self.pattern_weights[strength]
                for pattern in patterns:
                    found_matches = re.findall(pattern, text_lower)
                    if found_matches:
                        scores[intent_type] += len(found_matches) * weight
                        matches[intent_type].extend(found_matches)
        
        return dict(scores), dict(matches)

    def _extract_url_signals(self, url: str) -> Tuple[Dict[IntentType, int], List[str]]:
        """Extract and score intent signals from URL."""
        if not url:
            return {}, []
        
        parsed_url = urlparse(url)
        path_lower = parsed_url.path.lower()
        query_lower = parsed_url.query.lower()
        full_url_lower = f"{path_lower} {query_lower}".strip()
        
        scores = defaultdict(int)
        url_signals = []
        
        for intent_type, strength_patterns in self.url_patterns.items():
            for strength, patterns in strength_patterns.items():
                weight = self.url_weights[strength]
                for pattern in patterns:
                    if pattern in full_url_lower:
                        scores[intent_type] += weight
                        url_signals.append(f"{pattern} ({strength})")
        
        return dict(scores), url_signals

    def _calculate_confidence(self, scores: Dict[IntentType, int], total_signals: int) -> float:
        """Calculate confidence score based on signal strength and distribution."""
        if not scores or total_signals == 0:
            return 0.0
        
        max_score = max(scores.values())
        total_score = sum(scores.values())
        
        if total_score == 0:
            return 0.0
        
        # Base confidence from dominant signal strength
        base_confidence = min(max_score / 10.0, 1.0)  # Normalize to 0-1
        
        # Penalty for competing intents
        second_highest = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
        competition_penalty = second_highest / max_score if max_score > 0 else 0
        
        confidence = base_confidence * (1 - competition_penalty * 0.3)
        return round(min(max(confidence, 0.0), 1.0), 2)

    def _generate_reasoning(self, primary_intent: IntentType, text_matches: Dict, 
                          url_signals: List[str], scores: Dict[IntentType, int]) -> str:
        """Generate human-readable reasoning for the classification."""
        reasons = []
        
        if primary_intent in text_matches and text_matches[primary_intent]:
            reasons.append(f"Text contains {primary_intent.value} keywords: {', '.join(list(set(text_matches[primary_intent]))[:3])}")
        
        if url_signals:
            reasons.append(f"URL indicates {primary_intent.value} intent: {', '.join(url_signals[:2])}")
        
        if len(scores) > 1:
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_scores) > 1 and sorted_scores[1][1] > 0:
                reasons.append(f"Secondary signals for {sorted_scores[1][0].value} intent detected")
        
        return "; ".join(reasons) if reasons else "Default classification based on general content analysis"

    def classify(self, text: str, url: Optional[str] = None) -> IntentResult:
        """
        Classify search intent with enhanced accuracy and detailed results.
        
        Args:
            text: Search query or content text
            url: Optional URL to analyze for additional signals
            
        Returns:
            IntentResult with classification details
        """
        if not text or not text.strip():
            return IntentResult(
                primary_intent=IntentType.INFORMATIONAL,
                confidence=0.0,
                intent_scores={intent.value: 0 for intent in IntentType},
                matched_signals={},
                url_signals=[],
                reasoning="No text provided - defaulting to informational"
            )
        
        # Extract text signals
        text_scores, text_matches = self._extract_text_signals(text)
        
        # Extract URL signals
        url_scores, url_signals = self._extract_url_signals(url)
        
        # Combine scores
        combined_scores = defaultdict(int)
        for intent_type in IntentType:
            combined_scores[intent_type] = (
                text_scores.get(intent_type, 0) + 
                url_scores.get(intent_type, 0)
            )
        
        # Determine primary intent with tie-breaking
        intent_priority = [
            IntentType.TRANSACTIONAL,
            IntentType.COMMERCIAL, 
            IntentType.NAVIGATIONAL,
            IntentType.INFORMATIONAL
        ]
        
        max_score = max(combined_scores.values()) if combined_scores.values() else 0
        
        if max_score <= 0:
            primary_intent = IntentType.INFORMATIONAL
        else:
            # Find highest scoring intent, with priority-based tie breaking
            candidates = [intent for intent in intent_priority 
                         if combined_scores[intent] == max_score]
            primary_intent = candidates[0]
        
        # Calculate confidence
        total_signals = sum(len(matches) for matches in text_matches.values()) + len(url_signals)
        confidence = self._calculate_confidence(dict(combined_scores), total_signals)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(primary_intent, text_matches, url_signals, dict(combined_scores))
        
        return IntentResult(
            primary_intent=primary_intent,
            confidence=confidence,
            intent_scores={intent.value: combined_scores[intent] for intent in IntentType},
            matched_signals={intent.value: matches for intent, matches in text_matches.items()},
            url_signals=url_signals,
            reasoning=reasoning
        )


# Convenience function to maintain backward compatibility
def classify_search_intent(text: str, url: Optional[str] = None) -> dict:
    """
    Legacy function for backward compatibility.
    
    Returns:
        Dictionary with searchIntent, intentScores, and intentSignals
    """
    classifier = IntentClassifier()
    result = classifier.classify(text, url)
    
    return {
        'searchIntent': result.primary_intent.value,
        'intentScores': result.intent_scores,
        'intentSignals': result.matched_signals,
        'confidence': result.confidence,
        'urlSignals': result.url_signals,
        'reasoning': result.reasoning
    }

