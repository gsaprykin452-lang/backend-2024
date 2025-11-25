"""
Celery tasks for syncing content from data sources
"""
from celery import Task
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.data_source import DataSource, SourceType
from app.models.content import ContentItem, ContentType
from app.models.sync_log import SyncLog, SyncStatus
from app.services.twitter_client import TwitterClient
from app.services.rss_parser import RSSParser
from app.services.telegram_client import TelegramClient
from app.services.facebook_client import FacebookClient
from app.services.instagram_client import InstagramClient
from app.core.encryption import decrypt_data
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.sync.sync_data_source")
def sync_data_source(self: Task, source_id: str):
    """Sync content from a specific data source"""
    db = SessionLocal()
    start_time = datetime.utcnow()
    
    try:
        source = db.query(DataSource).filter(DataSource.id == source_id).first()
        if not source or not source.is_active:
            logger.warning(f"Source {source_id} not found or inactive")
            return
        
        # Update last_sync_at
        source.last_sync_at = start_time
        
        items_fetched = 0
        items_new = 0
        items_updated = 0
        error_message = None
        
        try:
            if source.source_type == SourceType.TWITTER:
                items_fetched, items_new, items_updated = sync_twitter_source(db, source)
            elif source.source_type == SourceType.RSS:
                items_fetched, items_new, items_updated = sync_rss_source(db, source)
            elif source.source_type == SourceType.TELEGRAM:
                items_fetched, items_new, items_updated = sync_telegram_source(db, source)
            elif source.source_type == SourceType.FACEBOOK:
                items_fetched, items_new, items_updated = sync_facebook_source(db, source)
            elif source.source_type == SourceType.INSTAGRAM:
                items_fetched, items_new, items_updated = sync_instagram_source(db, source)
            else:
                logger.warning(f"Unsupported source type: {source.source_type}")
                items_fetched = items_new = items_updated = 0
            
            status = SyncStatus.SUCCESS if not error_message else SyncStatus.PARTIAL
            
        except Exception as e:
            logger.error(f"Error syncing source {source_id}: {str(e)}", exc_info=True)
            status = SyncStatus.FAILED
            error_message = str(e)
        
        # Create sync log
        duration = (datetime.utcnow() - start_time).total_seconds()
        sync_log = SyncLog(
            source_id=source.id,
            status=status,
            items_fetched=items_fetched,
            items_new=items_new,
            items_updated=items_updated,
            error_message=error_message,
            duration_seconds=duration,
            started_at=start_time,
            completed_at=datetime.utcnow()
        )
        db.add(sync_log)
        db.commit()
        
    except Exception as e:
        logger.error(f"Critical error in sync_data_source: {str(e)}", exc_info=True)
        db.rollback()
    finally:
        db.close()


def sync_twitter_source(db: Session, source: DataSource) -> tuple[int, int, int]:
    """Sync content from Twitter source"""
    import asyncio
    
    if not source.credentials:
        raise ValueError("No credentials found for Twitter source")
    
    # Decrypt credentials
    credentials = source.credentials
    access_token = decrypt_data(credentials["access_token"])
    
    # Initialize Twitter client
    twitter_client = TwitterClient(access_token)
    
    # Get last sync time or default to 24 hours ago
    last_sync = source.last_sync_at
    if last_sync:
        start_time = last_sync
    else:
        start_time = datetime.utcnow() - timedelta(hours=24)
    
    # Get user timeline (async call in sync function)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        tweets = loop.run_until_complete(
            twitter_client.get_user_timeline(
                user_id=credentials.get("twitter_user_id"),
                max_results=100,
                start_time=start_time
            )
        )
    finally:
        loop.close()
    
    items_fetched = len(tweets)
    items_new = 0
    items_updated = 0
    
    for tweet in tweets:
        external_id = tweet.get("id")
        
        # Check if content item already exists
        existing_item = db.query(ContentItem).filter(
            ContentItem.source_id == source.id,
            ContentItem.external_id == external_id
        ).first()
        
        if existing_item:
            # Update existing item
            existing_item.text_content = tweet.get("text")
            existing_item.item_metadata = {
                "public_metrics": tweet.get("public_metrics", {}),
                "lang": tweet.get("lang")
            }
            existing_item.raw_data = tweet
            items_updated += 1
        else:
            # Create new content item
            published_at = datetime.fromisoformat(
                tweet.get("created_at").replace("Z", "+00:00")
            )
            
            new_item = ContentItem(
                source_id=source.id,
                external_id=external_id,
                content_type=ContentType.POST,
                text_content=tweet.get("text"),
                url=f"https://twitter.com/i/web/status/{external_id}",
                author=credentials.get("twitter_username"),
                published_at=published_at,
                item_metadata={
                    "public_metrics": tweet.get("public_metrics", {}),
                    "lang": tweet.get("lang")
                },
                raw_data=tweet
            )
            db.add(new_item)
            items_new += 1
    
    db.commit()
    return items_fetched, items_new, items_updated


def sync_rss_source(db: Session, source: DataSource) -> tuple[int, int, int]:
    """Sync content from RSS source"""
    if not source.settings or "feed_url" not in source.settings:
        raise ValueError("No feed_url found in RSS source settings")
    
    feed_url = source.settings["feed_url"]
    rss_parser = RSSParser()
    
    # Parse RSS feed
    feed_items = rss_parser.parse_feed(feed_url)
    
    items_fetched = len(feed_items)
    items_new = 0
    items_updated = 0
    
    for item_data in feed_items:
        external_id = item_data["external_id"]
        
        # Check if content item already exists
        existing_item = db.query(ContentItem).filter(
            ContentItem.source_id == source.id,
            ContentItem.external_id == external_id
        ).first()
        
        if existing_item:
            # Update existing item
            existing_item.title = item_data.get("title")
            existing_item.text_content = item_data.get("text_content")
            existing_item.url = item_data.get("url")
            existing_item.author = item_data.get("author")
            existing_item.item_metadata = item_data.get("metadata")
            existing_item.raw_data = item_data.get("raw_data")
            items_updated += 1
        else:
            # Create new content item
            new_item = ContentItem(
                source_id=source.id,
                external_id=external_id,
                content_type=ContentType.ARTICLE,
                title=item_data.get("title"),
                text_content=item_data.get("text_content"),
                url=item_data.get("url"),
                author=item_data.get("author"),
                published_at=item_data.get("published_at"),
                item_metadata=item_data.get("metadata"),
                raw_data=item_data.get("raw_data")
            )
            db.add(new_item)
            items_new += 1
    
    db.commit()
    return items_fetched, items_new, items_updated


def sync_telegram_source(db: Session, source: DataSource) -> tuple[int, int, int]:
    """Sync content from Telegram source"""
    import asyncio
    
    if not source.credentials:
        raise ValueError("No credentials found for Telegram source")
    
    credentials = source.credentials
    bot_token = decrypt_data(credentials["bot_token"])
    telegram_client = TelegramClient(bot_token)
    
    # Get last sync time or default to 24 hours ago
    last_sync = source.last_sync_at
    if last_sync:
        # Get updates after last sync
        offset = int(last_sync.timestamp())
    else:
        offset = None
    
    # Get updates
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        updates = loop.run_until_complete(
            telegram_client.get_updates(offset=offset, limit=100)
        )
    finally:
        loop.close()
    
    items_fetched = len(updates)
    items_new = 0
    items_updated = 0
    
    for update in updates:
        message = update.get("message", {})
        if not message:
            continue
        
        external_id = str(message.get("message_id", ""))
        chat_id = str(message.get("chat", {}).get("id", ""))
        
        # Check if content item already exists
        existing_item = db.query(ContentItem).filter(
            ContentItem.source_id == source.id,
            ContentItem.external_id == external_id
        ).first()
        
        if existing_item:
            items_updated += 1
            continue
        
        # Parse message date
        message_date = message.get("date")
        if message_date:
            published_at = datetime.fromtimestamp(message_date)
        else:
            published_at = datetime.utcnow()
        
        # Get message text
        text = message.get("text", "") or message.get("caption", "")
        
        # Create new content item
        new_item = ContentItem(
            source_id=source.id,
            external_id=external_id,
            content_type=ContentType.MESSAGE,
            text_content=text,
            author=message.get("from", {}).get("username", ""),
            published_at=published_at,
            item_metadata={
                "chat_id": chat_id,
                "chat_type": message.get("chat", {}).get("type", ""),
                "message_type": message.get("message_type", "text")
            },
            raw_data=message
        )
        db.add(new_item)
        items_new += 1
    
    db.commit()
    return items_fetched, items_new, items_updated


def sync_facebook_source(db: Session, source: DataSource) -> tuple[int, int, int]:
    """Sync content from Facebook source"""
    import asyncio
    
    if not source.credentials:
        raise ValueError("No credentials found for Facebook source")
    
    credentials = source.credentials
    access_token = decrypt_data(credentials["access_token"])
    facebook_client = FacebookClient(access_token)
    
    # Get last sync time or default to 24 hours ago
    last_sync = source.last_sync_at
    if last_sync:
        start_time = last_sync
    else:
        start_time = datetime.utcnow() - timedelta(hours=24)
    
    # Get user feed
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        posts = loop.run_until_complete(
            facebook_client.get_user_feed(
                user_id="me",
                limit=100,
                since=start_time
            )
        )
    finally:
        loop.close()
    
    items_fetched = len(posts)
    items_new = 0
    items_updated = 0
    
    for post in posts:
        external_id = post.get("id", "")
        
        # Check if content item already exists
        existing_item = db.query(ContentItem).filter(
            ContentItem.source_id == source.id,
            ContentItem.external_id == external_id
        ).first()
        
        if existing_item:
            existing_item.text_content = post.get("message", "")
            existing_item.item_metadata = {
                "likes": post.get("likes", {}).get("summary", {}).get("total_count", 0),
                "comments": post.get("comments", {}).get("summary", {}).get("total_count", 0),
                "shares": post.get("shares", {}).get("count", 0)
            }
            existing_item.raw_data = post
            items_updated += 1
        else:
            # Parse created time
            created_time = post.get("created_time", "")
            if created_time:
                published_at = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
            else:
                published_at = datetime.utcnow()
            
            new_item = ContentItem(
                source_id=source.id,
                external_id=external_id,
                content_type=ContentType.POST,
                text_content=post.get("message", ""),
                author=post.get("from", {}).get("name", ""),
                published_at=published_at,
                item_metadata={
                    "likes": post.get("likes", {}).get("summary", {}).get("total_count", 0),
                    "comments": post.get("comments", {}).get("summary", {}).get("total_count", 0),
                    "shares": post.get("shares", {}).get("count", 0)
                },
                raw_data=post
            )
            db.add(new_item)
            items_new += 1
    
    db.commit()
    return items_fetched, items_new, items_updated


def sync_instagram_source(db: Session, source: DataSource) -> tuple[int, int, int]:
    """Sync content from Instagram source"""
    import asyncio
    
    if not source.credentials:
        raise ValueError("No credentials found for Instagram source")
    
    credentials = source.credentials
    access_token = decrypt_data(credentials["access_token"])
    instagram_client = InstagramClient(access_token)
    
    # Get last sync time or default to 24 hours ago
    last_sync = source.last_sync_at
    
    # Get user media
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        media_items = loop.run_until_complete(
            instagram_client.get_user_media(user_id="me", limit=100)
        )
    finally:
        loop.close()
    
    items_fetched = len(media_items)
    items_new = 0
    items_updated = 0
    
    for media in media_items:
        external_id = media.get("id", "")
        
        # Check if content item already exists
        existing_item = db.query(ContentItem).filter(
            ContentItem.source_id == source.id,
            ContentItem.external_id == external_id
        ).first()
        
        if existing_item:
            existing_item.text_content = media.get("caption", "")
            existing_item.item_metadata = {
                "media_type": media.get("media_type", ""),
                "media_url": media.get("media_url", ""),
                "permalink": media.get("permalink", "")
            }
            existing_item.raw_data = media
            items_updated += 1
        else:
            # Parse timestamp
            timestamp = media.get("timestamp", "")
            if timestamp:
                published_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                published_at = datetime.utcnow()
            
            new_item = ContentItem(
                source_id=source.id,
                external_id=external_id,
                content_type=ContentType.POST,
                title=media.get("caption", "")[:200] if media.get("caption") else None,
                text_content=media.get("caption", ""),
                url=media.get("permalink", ""),
                author=media.get("username", ""),
                published_at=published_at,
                item_metadata={
                    "media_type": media.get("media_type", ""),
                    "media_url": media.get("media_url", ""),
                    "thumbnail_url": media.get("thumbnail_url", "")
                },
                raw_data=media
            )
            db.add(new_item)
            items_new += 1
    
    db.commit()
    return items_fetched, items_new, items_updated


@celery_app.task(name="app.tasks.sync.sync_all_sources")
def sync_all_sources():
    """Sync all active data sources"""
    db = SessionLocal()
    try:
        sources = db.query(DataSource).filter(
            DataSource.is_active == True
        ).all()
        
        for source in sources:
            # Check if it's time to sync
            if source.last_sync_at:
                time_since_sync = datetime.utcnow() - source.last_sync_at
                sync_interval = timedelta(minutes=source.sync_frequency_minutes)
                if time_since_sync < sync_interval:
                    continue
            
            # Queue sync task
            sync_data_source.delay(str(source.id))
            logger.info(f"Queued sync for source {source.id}")
        
    finally:
        db.close()

