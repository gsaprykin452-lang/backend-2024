"""
Content classification service
"""
from typing import Dict, List
from app.models.content import ContentItem, CategoryType
import re


class RuleBasedClassifier:
    """Rule-based content classifier"""
    
    # Keywords for different categories
    WORK_KEYWORDS = [
        "работа", "проект", "дедлайн", "встреча", "коллега", "офис",
        "задача", "клиент", "бизнес", "компания", "стартап"
    ]
    
    PERSONAL_KEYWORDS = [
        "семья", "друзья", "день рождения", "отпуск", "праздник",
        "личное", "дом", "родные"
    ]
    
    HOBBY_KEYWORDS = [
        "хобби", "спорт", "музыка", "кино", "книга", "игра",
        "путешествие", "фото", "рисование"
    ]
    
    NEWS_KEYWORDS = [
        "новость", "событие", "происшествие", "политика", "экономика",
        "технологии", "наука", "культура"
    ]
    
    IMPORTANT_KEYWORDS = [
        "важно", "срочно", "критично", "внимание", "обязательно",
        "необходимо", "требуется"
    ]
    
    def classify(self, content: ContentItem) -> Dict:
        """Classify content item and return scores"""
        text = (content.text_content or "").lower()
        title = (content.title or "").lower()
        full_text = f"{title} {text}"
        
        # Calculate scores for each category
        work_score = self._calculate_score(full_text, self.WORK_KEYWORDS)
        personal_score = self._calculate_score(full_text, self.PERSONAL_KEYWORDS)
        hobby_score = self._calculate_score(full_text, self.HOBBY_KEYWORDS)
        news_score = self._calculate_score(full_text, self.NEWS_KEYWORDS)
        important_score = self._calculate_score(full_text, self.IMPORTANT_KEYWORDS)
        
        # Determine category
        scores = {
            CategoryType.WORK: work_score,
            CategoryType.PERSONAL: personal_score,
            CategoryType.HOBBY: hobby_score,
            CategoryType.NEWS: news_score,
            CategoryType.IMPORTANT: important_score,
            CategoryType.OTHER: 0.1
        }
        
        category = max(scores, key=scores.get)
        
        # Calculate relevance and importance
        relevance_score = max(work_score, personal_score, hobby_score, news_score)
        importance_score = important_score * 0.5 + relevance_score * 0.5
        
        # Social score from metadata
        social_score = self._calculate_social_score(content.item_metadata or {})
        
        # Personal score (mentions, location, etc.)
        personal_relevance = self._calculate_personal_score(content)
        
        return {
            "category": category,
            "relevance_score": min(relevance_score, 1.0),
            "importance_score": min(importance_score, 1.0),
            "social_score": social_score,
            "personal_score": personal_relevance,
            "topics": self._extract_topics(full_text)
        }
    
    def _calculate_score(self, text: str, keywords: List[str]) -> float:
        """Calculate score based on keyword matches"""
        matches = sum(1 for keyword in keywords if keyword in text)
        return min(matches / len(keywords) * 2.0, 1.0) if keywords else 0.0
    
    def _calculate_social_score(self, metadata: Dict) -> float:
        """Calculate social score from likes, retweets, etc."""
        metrics = metadata.get("public_metrics", {})
        like_count = metrics.get("like_count", 0)
        retweet_count = metrics.get("retweet_count", 0)
        reply_count = metrics.get("reply_count", 0)
        
        # Normalize to 0-1 scale (assuming max 1000 likes = 1.0)
        total_engagement = like_count + retweet_count * 2 + reply_count
        return min(total_engagement / 1000.0, 1.0)
    
    def _calculate_personal_score(self, content: ContentItem) -> float:
        """Calculate personal relevance score"""
        # This can be enhanced with user preferences, mentions, etc.
        # For now, return a base score
        return 0.3
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics/keywords from text"""
        # Simple keyword extraction (can be enhanced with NLP)
        words = re.findall(r'\b[а-яё]{4,}\b', text.lower())
        # Return most common words (simplified)
        from collections import Counter
        common_words = Counter(words).most_common(5)
        return [word for word, count in common_words]


class AIClassifier:
    """AI-powered classifier using OpenAI"""
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
    
    async def classify(self, content: ContentItem, user_preferences: Dict = None) -> Dict:
        """Classify content using OpenAI"""
        from app.models.content import CategoryType
        
        text = content.text_content or ""
        title = content.title or ""
        
        prompt = f"""Проанализируй следующий контент и определи его категорию, релевантность и важность.

Заголовок: {title}
Текст: {text[:500]}

Определи:
1. Категорию: personal, work, hobby, news, important, other
2. Релевантность (0.0-1.0): насколько контент релевантен пользователю
3. Важность (0.0-1.0): насколько важен этот контент
4. Социальная значимость (0.0-1.0): популярность, вирусность
5. Личная значимость (0.0-1.0): упоминания друзей, личные связи

Ответь в формате JSON:
{{
    "category": "work",
    "relevance_score": 0.8,
    "importance_score": 0.6,
    "social_score": 0.4,
    "personal_score": 0.3,
    "topics": ["тема1", "тема2"]
}}"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "Ты помощник для классификации контента. Отвечай только валидным JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            return {
                "category": CategoryType(result.get("category", "other")),
                "relevance_score": float(result.get("relevance_score", 0.5)),
                "importance_score": float(result.get("importance_score", 0.5)),
                "social_score": float(result.get("social_score", 0.3)),
                "personal_score": float(result.get("personal_score", 0.3)),
                "topics": result.get("topics", [])
            }
        except Exception as e:
            # Fallback to rule-based if AI fails
            rule_classifier = RuleBasedClassifier()
            return rule_classifier.classify(content)

