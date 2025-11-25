"""
RSS feed parser service
"""
import feedparser
from typing import List, Dict
from datetime import datetime
from app.models.content import ContentType
import logging

logger = logging.getLogger(__name__)


class RSSParser:
    """Parse RSS feeds and extract content"""
    
    def parse_feed(self, feed_url: str) -> List[Dict]:
        """Parse RSS feed and return content items"""
        try:
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                logger.warning(f"Feed parsing error: {feed.bozo_exception}")
            
            items = []
            for entry in feed.entries:
                # Parse published date
                published_at = datetime.utcnow()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published_at = datetime(*entry.updated_parsed[:6])
                
                # Extract content
                content = entry.get('summary', '') or entry.get('description', '')
                
                # Clean HTML from content
                from bs4 import BeautifulSoup
                if content:
                    soup = BeautifulSoup(content, 'html.parser')
                    content = soup.get_text()
                
                item = {
                    "external_id": entry.get('id', entry.get('link', '')),
                    "title": entry.get('title', ''),
                    "text_content": content,
                    "url": entry.get('link', ''),
                    "author": entry.get('author', '') or entry.get('dc:creator', ''),
                    "published_at": published_at,
                    "metadata": {
                        "feed_title": feed.feed.get('title', ''),
                        "feed_link": feed.feed.get('link', ''),
                        "tags": [tag.get('term', '') for tag in entry.get('tags', [])]
                    },
                    "raw_data": {
                        "entry": dict(entry)
                    }
                }
                items.append(item)
            
            return items
            
        except Exception as e:
            logger.error(f"Error parsing RSS feed {feed_url}: {str(e)}", exc_info=True)
            return []

