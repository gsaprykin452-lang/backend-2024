"""
Celery tasks for generating briefings
"""
from celery import Task
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.briefing import Briefing, BriefingStatus
from app.models.content import ContentItem
from app.services.briefing_generator import BriefingGenerator
from app.services.classification import RuleBasedClassifier, AIClassifier
from app.core.config import settings
import openai
import os
import logging

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None


@celery_app.task(bind=True, name="app.tasks.briefing.generate_briefing")
def generate_briefing(self: Task, user_id: str, briefing_date: str = None):
    """Generate briefing for a specific user and date"""
    db = SessionLocal()
    start_time = datetime.utcnow()
    
    try:
        user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if not user or not user.is_active:
            logger.warning(f"User {user_id} not found or inactive")
            return
        
        # Parse date
        if briefing_date:
            target_date = datetime.fromisoformat(briefing_date).date()
        else:
            target_date = date.today()
        
        # Check if briefing already exists
        existing_briefing = db.query(Briefing).filter(
            Briefing.user_id == user.id,
            Briefing.date == target_date
        ).first()
        
        if existing_briefing and existing_briefing.status == BriefingStatus.DELIVERED:
            logger.info(f"Briefing for user {user_id} on {target_date} already exists")
            return existing_briefing.id
        
        # Create or update briefing
        if existing_briefing:
            briefing = existing_briefing
            briefing.status = BriefingStatus.GENERATING
        else:
            briefing = Briefing(
                user_id=user.id,
                date=target_date,
                status=BriefingStatus.GENERATING
            )
            db.add(briefing)
        
        db.commit()
        db.refresh(briefing)
        
        # Generate briefing
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Select content
            generator = BriefingGenerator(openai_client)
            content_items = generator.select_content_for_briefing(db, user)
            
            if not content_items:
                briefing.status = BriefingStatus.FAILED
                briefing.error_message = "No content available for briefing"
                db.commit()
                return briefing.id
            
            # Generate text summary
            text_summary = loop.run_until_complete(
                generator.generate_text_summary(content_items, user)
            )
            
            # Generate audio
            audio_data = loop.run_until_complete(
                generator.generate_audio(text_summary)
            )
            
            # Save audio file
            audio_url = save_audio_file(briefing.id, audio_data)
            
            # Update briefing
            briefing.text_summary = text_summary
            briefing.audio_file_url = audio_url
            briefing.audio_duration_seconds = settings.BRIEFING_DURATION_SECONDS
            briefing.content_items_count = len(content_items)
            briefing.generated_at = datetime.utcnow()
            briefing.status = BriefingStatus.READY
            
            # Create briefing_content links
            from app.models.briefing import BriefingContent
            for order, item in enumerate(content_items, 1):
                briefing_content = BriefingContent(
                    briefing_id=briefing.id,
                    content_id=item.id,
                    order=order,
                    included_reason=f"Relevance: {item.classification.relevance_score:.2f}"
                )
                db.add(briefing_content)
            
            db.commit()
            logger.info(f"Briefing {briefing.id} generated successfully")
            
        except Exception as e:
            logger.error(f"Error generating briefing: {str(e)}", exc_info=True)
            briefing.status = BriefingStatus.FAILED
            briefing.error_message = str(e)
            db.commit()
        finally:
            loop.close()
        
        return briefing.id
        
    except Exception as e:
        logger.error(f"Critical error in generate_briefing: {str(e)}", exc_info=True)
        db.rollback()
    finally:
        db.close()


def save_audio_file(briefing_id: str, audio_data: bytes) -> str:
    """Save audio file and return URL"""
    if settings.STORAGE_TYPE == "local":
        # Save locally
        os.makedirs(settings.STORAGE_LOCAL_PATH, exist_ok=True)
        file_path = os.path.join(settings.STORAGE_LOCAL_PATH, f"{briefing_id}.mp3")
        with open(file_path, "wb") as f:
            f.write(audio_data)
        return f"/storage/{briefing_id}.mp3"
    else:
        # TODO: Implement S3/Azure storage
        raise NotImplementedError("S3/Azure storage not implemented yet")


@celery_app.task(name="app.tasks.briefing.generate_daily_briefings")
def generate_daily_briefings():
    """Generate briefings for all users who need them today"""
    db = SessionLocal()
    try:
        # Get all active users
        users = db.query(User).filter(
            User.deleted_at.is_(None),
            User.is_active == True
        ).all()
        
        current_time = datetime.utcnow()
        today = date.today()
        
        for user in users:
            # Check if it's time to generate briefing
            briefing_time = user.briefing_time
            briefing_datetime = datetime.combine(today, briefing_time)
            
            # Generate 10 minutes before briefing time
            generation_time = briefing_datetime - timedelta(
                minutes=settings.BRIEFING_GENERATION_START_MINUTES
            )
            
            # Check if we're in the generation window (within 1 hour)
            time_diff = (current_time - generation_time).total_seconds()
            if 0 <= time_diff <= 3600:  # Within 1 hour window
                # Check if briefing already exists
                existing = db.query(Briefing).filter(
                    Briefing.user_id == user.id,
                    Briefing.date == today
                ).first()
                
                if not existing or existing.status != BriefingStatus.DELIVERED:
                    # Queue briefing generation
                    generate_briefing.delay(str(user.id), today.isoformat())
                    logger.info(f"Queued briefing generation for user {user.id}")
        
    finally:
        db.close()


@celery_app.task(name="app.tasks.briefing.classify_pending_content")
def classify_pending_content():
    """Classify unclassified content items"""
    db = SessionLocal()
    try:
        from app.models.content import ContentClassification
        
        # Get unclassified content (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        unclassified = db.query(ContentItem).outerjoin(ContentClassification).filter(
            ContentClassification.id.is_(None),
            ContentItem.published_at >= cutoff_time
        ).limit(100).all()
        
        classifier = RuleBasedClassifier()
        ai_classifier = AIClassifier(openai_client) if openai_client else None
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            for item in unclassified:
                # Use AI classifier if available, otherwise rule-based
                if ai_classifier:
                    classification_data = loop.run_until_complete(
                        ai_classifier.classify(item)
                    )
                else:
                    classification_data = classifier.classify(item)
                
                # Create classification
                classification = ContentClassification(
                    content_id=item.id,
                    category=classification_data["category"],
                    relevance_score=classification_data["relevance_score"],
                    importance_score=classification_data["importance_score"],
                    social_score=classification_data["social_score"],
                    personal_score=classification_data["personal_score"],
                    topics=classification_data.get("topics", []),
                    model_version="rule-based-v1" if not ai_classifier else "gpt-4-v1"
                )
                db.add(classification)
            
            db.commit()
            logger.info(f"Classified {len(unclassified)} content items")
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Error classifying content: {str(e)}", exc_info=True)
        db.rollback()
    finally:
        db.close()

