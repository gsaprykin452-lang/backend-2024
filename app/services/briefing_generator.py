"""
Briefing generation service
"""
from typing import List, Dict
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.models.content import ContentItem, ContentClassification
from app.models.briefing import Briefing, BriefingContent, BriefingStatus
from app.models.user import User
from app.core.config import settings
import openai
import json


class BriefingGenerator:
    """Generate text summaries and audio briefings"""
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
        self.max_duration_seconds = settings.BRIEFING_DURATION_SECONDS
    
    async def generate_text_summary(
        self,
        content_items: List[ContentItem],
        user: User
    ) -> str:
        """Generate text summary from content items"""
        # Prepare content for summarization
        content_texts = []
        for item in content_items:
            text = item.text_content or item.title or ""
            if text:
                content_texts.append(f"- {text[:200]}")
        
        content_summary = "\n".join(content_texts[:20])  # Limit to 20 items
        
        prompt = f"""Создай краткий утренний дайджест на основе следующего контента.
Дайджест должен быть рассчитан на {self.max_duration_seconds} секунд чтения (примерно 300-400 слов).
Будь кратким, информативным и структурированным.

Контент:
{content_summary}

Структура дайджеста:
1. Краткое введение (1-2 предложения)
2. Основные новости и события (по категориям)
3. Личные обновления (если есть)
4. Заключение

Язык: русский
Стиль: дружелюбный, профессиональный"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Ты создаешь утренние дайджесты. Будь кратким и информативным."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            summary = response.choices[0].message.content
            return summary
        except Exception as e:
            # Fallback summary
            return self._create_fallback_summary(content_items)
    
    def _create_fallback_summary(self, content_items: List[ContentItem]) -> str:
        """Create a simple fallback summary"""
        summary_parts = ["Доброе утро! Вот ваш дайджест на сегодня:\n"]
        
        for i, item in enumerate(content_items[:10], 1):
            text = (item.text_content or item.title or "")[:100]
            summary_parts.append(f"{i}. {text}...")
        
        return "\n".join(summary_parts)
    
    async def generate_audio(
        self,
        text: str,
        voice_id: str = None
    ) -> bytes:
        """Generate audio from text using TTS"""
        from app.core.config import settings
        
        # Try ElevenLabs first, fallback to OpenAI TTS
        if settings.ELEVENLABS_API_KEY:
            try:
                return await self._generate_with_elevenlabs(text, voice_id or settings.ELEVENLABS_VOICE_ID)
            except Exception as e:
                print(f"ElevenLabs TTS failed: {e}, falling back to OpenAI")
        
        # Fallback to OpenAI TTS
        return await self._generate_with_openai(text)
    
    async def _generate_with_elevenlabs(self, text: str, voice_id: str) -> bytes:
        """Generate audio using ElevenLabs"""
        from elevenlabs import generate, set_api_key
        from app.core.config import settings
        
        set_api_key(settings.ELEVENLABS_API_KEY)
        audio = generate(
            text=text,
            voice=voice_id,
            model="eleven_multilingual_v2"
        )
        return audio
    
    async def _generate_with_openai(self, text: str) -> bytes:
        """Generate audio using OpenAI TTS"""
        response = await self.openai_client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        return response.content
    
    def select_content_for_briefing(
        self,
        db: Session,
        user: User,
        max_items: int = None
    ) -> List[ContentItem]:
        """Select most relevant content items for briefing"""
        from app.models.data_source import DataSource
        from app.models.user import UserPreferences
        
        max_items = max_items or settings.MAX_CONTENT_ITEMS_PER_BRIEFING
        
        # Get user preferences
        preferences = db.query(UserPreferences).filter(
            UserPreferences.user_id == user.id
        ).first()
        
        min_relevance = preferences.min_relevance_score if preferences else settings.MIN_RELEVANCE_SCORE
        
        # Get content from last 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Get active sources
        sources = db.query(DataSource).filter(
            DataSource.user_id == user.id,
            DataSource.is_active == True
        ).all()
        
        source_ids = [str(s.id) for s in sources]
        
        # Get classified content
        content = db.query(ContentItem).join(ContentClassification).filter(
            ContentItem.source_id.in_(source_ids),
            ContentItem.published_at >= cutoff_time,
            ContentClassification.relevance_score >= min_relevance
        ).order_by(
            ContentClassification.relevance_score.desc(),
            ContentClassification.importance_score.desc()
        ).limit(max_items * 2).all()  # Get more, then filter
        
        # Filter and rank
        ranked_content = []
        for item in content:
            if item.classification:
                ranked_content.append(item)
        
        # Return top items
        return ranked_content[:max_items]

