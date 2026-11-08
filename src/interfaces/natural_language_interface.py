"""
Natural Language Interface - Phase 5
Semantic understanding for conversational governance queries.
Users can ask questions in natural language and get insights.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Intent classification for natural language queries."""
    COST_ANALYSIS = "cost_analysis"  # "Show me my biggest cost drivers"
    PERFORMANCE_QUERY = "performance_query"  # "Why are my queries slow?"
    SECURITY_AUDIT = "security_audit"  # "Who has access to production?"
    HEALTH_CHECK = "health_check"  # "Is the system healthy?"
    TREND_ANALYSIS = "trend_analysis"  # "Show me the trend in query times"
    ANOMALY_DETECTION = "anomaly_detection"  # "What's unusual?"
    FORECAST = "forecast"  # "What will happen next week?"
    RECOMMENDATION = "recommendation"  # "What should I fix?"
    STATUS_UPDATE = "status_update"  # "What's the status?"
    HELP = "help"  # "How do I use this?"


class EntityType(Enum):
    """Entity types extracted from queries."""
    WAREHOUSE = "warehouse"
    USER = "user"
    DATABASE = "database"
    COST_CENTER = "cost_center"
    METRIC = "metric"
    TIME_PERIOD = "time_period"
    THRESHOLD = "threshold"


@dataclass
class ExtractedEntity:
    """Represents an extracted entity from query."""
    entity_type: EntityType
    value: str
    confidence: float  # 0-1


@dataclass
class ParsedQuery:
    """Result of parsing a natural language query."""
    original_text: str
    intent: QueryIntent
    entities: List[ExtractedEntity]
    confidence: float  # Overall confidence of parsing
    interpreted_request: str  # Rephrased request


class IntentClassifier:
    """Classifies user queries to identify intent."""

    def __init__(self):
        # Simple keyword-based classification (in production, would use ML)
        self.intent_keywords = {
            QueryIntent.COST_ANALYSIS: [
                "cost", "spend", "budget", "expensive", "price", "charges", "billing"
            ],
            QueryIntent.PERFORMANCE_QUERY: [
                "slow", "fast", "speed", "latency", "duration", "execution", "performance"
            ],
            QueryIntent.SECURITY_AUDIT: [
                "access", "permission", "role", "security", "who", "audit", "compliance"
            ],
            QueryIntent.HEALTH_CHECK: [
                "health", "status", "ok", "error", "issue", "problem", "working"
            ],
            QueryIntent.TREND_ANALYSIS: [
                "trend", "increasing", "decreasing", "over time", "growth", "change"
            ],
            QueryIntent.ANOMALY_DETECTION: [
                "unusual", "anomaly", "weird", "strange", "unexpected", "abnormal"
            ],
            QueryIntent.FORECAST: [
                "predict", "forecast", "will", "next week", "next month", "upcoming"
            ],
            QueryIntent.RECOMMENDATION: [
                "suggest", "recommend", "fix", "optimize", "improve", "should"
            ],
            QueryIntent.STATUS_UPDATE: [
                "status", "current", "now", "today", "how many", "what is"
            ],
            QueryIntent.HELP: [
                "help", "how do i", "how to", "what can i", "what should i"
            ]
        }

    def classify(self, query: str) -> Tuple[QueryIntent, float]:
        """
        Classify query intent.

        Returns:
            Tuple of (intent, confidence_score)
        """
        query_lower = query.lower()
        intent_scores: Dict[QueryIntent, int] = {}

        # Count keyword matches
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                intent_scores[intent] = score

        if not intent_scores:
            return QueryIntent.STATUS_UPDATE, 0.3  # Default

        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = min(1.0, intent_scores[best_intent] / 3.0)  # Normalize

        return best_intent, confidence


class EntityExtractor:
    """Extracts entities from natural language queries."""

    def __init__(self):
        pass

    def extract(self, query: str) -> List[ExtractedEntity]:
        """Extract entities from query."""
        entities = []

        # Warehouse detection
        if any(wh in query for wh in ["warehouse", "compute", "analyst"]):
            entities.append(ExtractedEntity(
                entity_type=EntityType.WAREHOUSE,
                value="COMPUTE_WH",  # Simplified extraction
                confidence=0.7
            ))

        # Cost center detection
        if any(cc in query.lower() for cc in ["engineering", "analytics", "finance", "sales"]):
            value = next(cc for cc in ["engineering", "analytics", "finance", "sales"]
                        if cc in query.lower())
            entities.append(ExtractedEntity(
                entity_type=EntityType.COST_CENTER,
                value=value,
                confidence=0.8
            ))

        # Time period detection
        if any(tp in query.lower() for tp in ["today", "this week", "this month", "last 7 days"]):
            entities.append(ExtractedEntity(
                entity_type=EntityType.TIME_PERIOD,
                value="last_7_days",
                confidence=0.9
            ))

        # Metric detection
        if any(m in query.lower() for m in ["cost", "time", "speed", "error", "utilization"]):
            entities.append(ExtractedEntity(
                entity_type=EntityType.METRIC,
                value="cost",
                confidence=0.7
            ))

        return entities


class ResponseGenerator:
    """Generates natural language responses to queries."""

    def __init__(self, snowpark_client=None):
        self.snowpark_client = snowpark_client

    def generate_response(
        self,
        intent: QueryIntent,
        entities: List[ExtractedEntity],
        data: Dict[str, Any]
    ) -> str:
        """Generate natural language response."""

        if intent == QueryIntent.COST_ANALYSIS:
            return self._respond_cost_analysis(entities, data)
        elif intent == QueryIntent.PERFORMANCE_QUERY:
            return self._respond_performance(entities, data)
        elif intent == QueryIntent.HEALTH_CHECK:
            return self._respond_health(data)
        elif intent == QueryIntent.FORECAST:
            return self._respond_forecast(entities, data)
        elif intent == QueryIntent.RECOMMENDATION:
            return self._respond_recommendation(data)
        else:
            return self._respond_generic(intent, data)

    def _respond_cost_analysis(self, entities: List[ExtractedEntity], data: Dict[str, Any]) -> str:
        """Respond to cost analysis queries."""
        total_cost = data.get("total_cost", 0)
        top_drivers = data.get("top_cost_drivers", [])

        response = f"💰 **Cost Analysis**\n\n"
        response += f"Your total spend is **${total_cost:,.0f}**.\n\n"

        if top_drivers:
            response += "**Top cost drivers:**\n"
            for i, driver in enumerate(top_drivers[:5], 1):
                response += f"{i}. {driver.get('name', 'Unknown')}: ${driver.get('cost', 0):,.0f}\n"

        response += "\n_Tip: Consider optimizing your most expensive queries to reduce costs._"
        return response

    def _respond_performance(self, entities: List[ExtractedEntity], data: Dict[str, Any]) -> str:
        """Respond to performance queries."""
        avg_time = data.get("avg_execution_time", 0)
        slow_queries = data.get("slow_queries", [])

        response = f"⚡ **Performance Analysis**\n\n"
        response += f"Average query time: **{avg_time:.1f} seconds**\n\n"

        if slow_queries:
            response += f"Found **{len(slow_queries)} slow queries**:\n"
            for i, query in enumerate(slow_queries[:3], 1):
                response += f"{i}. Query {query.get('id')}: {query.get('time', 0):.1f}s\n"
            response += "\n_Slow queries can indicate missing indexes or inefficient joins._"
        else:
            response += "✅ All queries are performing well!"

        return response

    def _respond_health(self, data: Dict[str, Any]) -> str:
        """Respond to health check queries."""
        system_health = data.get("system_health", 0)
        active_issues = data.get("active_issues", 0)

        if system_health >= 0.95:
            status = "✅ Healthy"
        elif system_health >= 0.80:
            status = "⚠️ Degraded"
        else:
            status = "❌ Critical"

        response = f"**System Health: {status}**\n\n"
        response += f"Health Score: {system_health*100:.0f}%\n"
        response += f"Active Issues: {active_issues}\n"

        if active_issues > 0:
            response += "\n_Run \`/governance status\` for details._"

        return response

    def _respond_forecast(self, entities: List[ExtractedEntity], data: Dict[str, Any]) -> str:
        """Respond to forecast queries."""
        predictions = data.get("predictions", [])

        response = f"🔮 **Forecast (Next 7 Days)**\n\n"

        if predictions:
            for pred in predictions[:3]:
                response += f"• {pred.get('issue_type', 'Issue')}: {pred.get('description', '')}\n"
                response += f"  Expected in {pred.get('days', 0)} days (confidence: {pred.get('confidence', 0)*100:.0f}%)\n\n"
        else:
            response += "No significant issues predicted. Keep up the good work! 🎉"

        return response

    def _respond_recommendation(self, data: Dict[str, Any]) -> str:
        """Respond to recommendation queries."""
        recommendations = data.get("recommendations", [])

        response = f"💡 **Recommendations**\n\n"

        if recommendations:
            for i, rec in enumerate(recommendations[:5], 1):
                response += f"{i}. {rec.get('title', 'Recommendation')}\n"
                response += f"   Impact: {rec.get('impact', 'medium')}\n\n"
        else:
            response += "No immediate recommendations. Your system is well-optimized! ✨"

        return response

    def _respond_generic(self, intent: QueryIntent, data: Dict[str, Any]) -> str:
        """Respond to generic queries."""
        return f"I understood you're asking about **{intent.value}**.\n\nHere's what I found:\n\n{str(data)}"


class NaturalLanguageProcessor:
    """
    Natural Language Interface - Phase 5

    Processes user queries in natural language and provides intelligent responses.
    Features:
    - Intent classification
    - Entity extraction
    - Context-aware responses
    - Multi-turn conversations
    - Learning from interactions
    """

    def __init__(self, snowpark_client=None, notification_manager=None):
        self.snowpark_client = snowpark_client
        self.notification_manager = notification_manager

        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.response_generator = ResponseGenerator(snowpark_client)

        self.conversation_history: List[Dict[str, Any]] = []
        self.user_preferences: Dict[str, Any] = {}

    def process_query(self, user_id: str, query: str) -> str:
        """
        Process a natural language query.

        Returns:
            Natural language response
        """
        logger.info(f"Processing query from {user_id}: {query}")

        try:
            # Parse the query
            parsed = self._parse_query(query)

            # Load context
            context = self._load_context(parsed)

            # Generate response
            response = self.response_generator.generate_response(
                parsed.intent,
                parsed.entities,
                context
            )

            # Store in conversation history
            self._record_interaction(user_id, query, parsed.intent, response)

            return response

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return f"Sorry, I couldn't process that query. Error: {str(e)}"

    def _parse_query(self, query: str) -> ParsedQuery:
        """Parse natural language query."""
        intent, confidence = self.intent_classifier.classify(query)
        entities = self.entity_extractor.extract(query)

        # Generate interpreted request
        entity_str = ", ".join([e.value for e in entities])
        interpreted = f"Query about {intent.value}" + (f" for {entity_str}" if entity_str else "")

        return ParsedQuery(
            original_text=query,
            intent=intent,
            entities=entities,
            confidence=confidence,
            interpreted_request=interpreted
        )

    def _load_context(self, parsed_query: ParsedQuery) -> Dict[str, Any]:
        """Load context data for response generation."""
        context = {}

        try:
            if parsed_query.intent == QueryIntent.COST_ANALYSIS:
                context = self._get_cost_data(parsed_query.entities)
            elif parsed_query.intent == QueryIntent.PERFORMANCE_QUERY:
                context = self._get_performance_data(parsed_query.entities)
            elif parsed_query.intent == QueryIntent.HEALTH_CHECK:
                context = self._get_health_data()
            elif parsed_query.intent == QueryIntent.FORECAST:
                context = self._get_forecast_data()
            elif parsed_query.intent == QueryIntent.RECOMMENDATION:
                context = self._get_recommendation_data()

        except Exception as e:
            logger.error(f"Error loading context: {str(e)}")

        return context

    def _get_cost_data(self, entities: List[ExtractedEntity]) -> Dict[str, Any]:
        """Get cost analysis data."""
        # Simplified - would fetch from database
        return {
            "total_cost": 5234.50,
            "top_cost_drivers": [
                {"name": "ML Training Queries", "cost": 1500},
                {"name": "Analytics Warehouse", "cost": 1200},
                {"name": "Data Pipeline", "cost": 800}
            ]
        }

    def _get_performance_data(self, entities: List[ExtractedEntity]) -> Dict[str, Any]:
        """Get performance data."""
        return {
            "avg_execution_time": 45.3,
            "slow_queries": [
                {"id": "query_123", "time": 120.5},
                {"id": "query_124", "time": 95.2}
            ]
        }

    def _get_health_data(self) -> Dict[str, Any]:
        """Get system health data."""
        return {
            "system_health": 0.92,
            "active_issues": 2
        }

    def _get_forecast_data(self) -> Dict[str, Any]:
        """Get forecast data."""
        return {
            "predictions": [
                {
                    "issue_type": "Storage Capacity",
                    "description": "Storage will reach 90% capacity",
                    "days": 5,
                    "confidence": 0.87
                },
                {
                    "issue_type": "Query Performance",
                    "description": "Average query time trending upward",
                    "days": 7,
                    "confidence": 0.72
                }
            ]
        }

    def _get_recommendation_data(self) -> Dict[str, Any]:
        """Get recommendation data."""
        return {
            "recommendations": [
                {"title": "Optimize slow queries with better indexing", "impact": "high"},
                {"title": "Archive old data to reduce storage costs", "impact": "high"},
                {"title": "Configure auto-suspend for unused warehouses", "impact": "medium"},
                {"title": "Review access permissions for data governance", "impact": "medium"}
            ]
        }

    def _record_interaction(
        self,
        user_id: str,
        query: str,
        intent: QueryIntent,
        response: str
    ) -> None:
        """Record interaction for learning."""
        interaction = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "query": query,
            "intent": intent.value,
            "response": response[:100]  # First 100 chars
        }
        self.conversation_history.append(interaction)

        logger.info(f"Recorded interaction - Intent: {intent.value}")

    def get_conversation_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about user's interaction patterns."""
        user_interactions = [
            i for i in self.conversation_history
            if i.get("user_id") == user_id
        ]

        if not user_interactions:
            return {"message": "No interactions yet"}

        # Analyze intent distribution
        intents = [i.get("intent") for i in user_interactions]
        intent_counts = {}
        for intent in intents:
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        return {
            "total_queries": len(user_interactions),
            "most_common_intent": max(intent_counts, key=intent_counts.get),
            "intent_distribution": intent_counts,
            "recent_queries": user_interactions[-5:]
        }

    def explain_response(self, query: str) -> str:
        """Explain how the system understood a query (for debugging)."""
        parsed = self._parse_query(query)

        explanation = f"""
**How I understood your query:**

Original: "{parsed.original_text}"
Interpreted as: {parsed.interpreted_request}

Intent: **{parsed.intent.value}** (confidence: {parsed.confidence*100:.0f}%)

Extracted entities:
"""
        for entity in parsed.entities:
            explanation += f"  • {entity.entity_type.value}: {entity.value} ({entity.confidence*100:.0f}%)\n"

        return explanation
