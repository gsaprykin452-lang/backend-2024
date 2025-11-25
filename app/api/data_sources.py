"""
Data sources API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import secrets
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.config import settings
from app.core.encryption import encrypt_data, decrypt_data
from app.models.user import User
from app.models.data_source import DataSource, SourceType
from app.schemas.data_source import (
    DataSourceCreate,
    DataSourceResponse,
    TwitterOAuthInit,
    TwitterOAuthCallback,
    TelegramBotConnect,
    FacebookOAuthInit,
    FacebookOAuthCallback,
    InstagramOAuthInit,
    InstagramOAuthCallback
)
from app.services.twitter_oauth import TwitterOAuth
from app.services.facebook_oauth import FacebookOAuth
from app.services.instagram_oauth import InstagramOAuth
from app.services.telegram_client import TelegramClient

router = APIRouter()

# OAuth credentials (should be in .env)
TWITTER_CLIENT_ID = getattr(settings, "TWITTER_CLIENT_ID", "")
TWITTER_CLIENT_SECRET = getattr(settings, "TWITTER_CLIENT_SECRET", "")
FACEBOOK_APP_ID = getattr(settings, "FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = getattr(settings, "FACEBOOK_APP_SECRET", "")
INSTAGRAM_APP_ID = getattr(settings, "INSTAGRAM_APP_ID", "")
INSTAGRAM_APP_SECRET = getattr(settings, "INSTAGRAM_APP_SECRET", "")
TELEGRAM_BOT_TOKEN = getattr(settings, "TELEGRAM_BOT_TOKEN", "")


@router.get("/", response_model=List[DataSourceResponse])
async def get_data_sources(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all data sources for current user"""
    sources = db.query(DataSource).filter(
        DataSource.user_id == current_user.id
    ).all()
    return sources


@router.post("/", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_data_source(
    source_data: DataSourceCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new data source"""
    new_source = DataSource(
        user_id=current_user.id,
        source_type=source_data.source_type,
        name=source_data.name,
        settings=source_data.settings
    )
    
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    
    return new_source


@router.get("/twitter/oauth/init")
async def init_twitter_oauth(
    redirect_uri: str,
    current_user: User = Depends(get_current_active_user)
):
    """Initialize Twitter OAuth flow"""
    if not TWITTER_CLIENT_ID or not TWITTER_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Twitter OAuth not configured"
        )
    
    twitter_oauth = TwitterOAuth(
        client_id=TWITTER_CLIENT_ID,
        client_secret=TWITTER_CLIENT_SECRET,
        redirect_uri=redirect_uri
    )
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    code_challenge = secrets.token_urlsafe(32)
    
    auth_url = twitter_oauth.get_authorization_url(
        state=state,
        code_challenge=code_challenge
    )
    
    return {
        "authorization_url": auth_url,
        "state": state,
        "code_verifier": code_challenge  # In production, store this securely
    }


@router.post("/twitter/oauth/callback")
async def twitter_oauth_callback(
    callback_data: TwitterOAuthCallback,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Handle Twitter OAuth callback"""
    if not TWITTER_CLIENT_ID or not TWITTER_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Twitter OAuth not configured"
        )
    
    twitter_oauth = TwitterOAuth(
        client_id=TWITTER_CLIENT_ID,
        client_secret=TWITTER_CLIENT_SECRET,
        redirect_uri=callback_data.redirect_uri
    )
    
    # Exchange code for tokens
    tokens = await twitter_oauth.exchange_code_for_tokens(
        code=callback_data.code,
        code_verifier=callback_data.state  # In production, retrieve from storage
    )
    
    # Get user info
    user_info = await twitter_oauth.get_user_info(tokens["access_token"])
    twitter_user = user_info.get("data", {})
    
    # Encrypt and store credentials
    credentials = {
        "access_token": encrypt_data(tokens["access_token"]),
        "refresh_token": encrypt_data(tokens.get("refresh_token", "")),
        "token_type": tokens.get("token_type", "bearer"),
        "expires_in": tokens.get("expires_in"),
        "twitter_user_id": twitter_user.get("id"),
        "twitter_username": twitter_user.get("username")
    }
    
    # Create or update data source
    existing_source = db.query(DataSource).filter(
        DataSource.user_id == current_user.id,
        DataSource.source_type == SourceType.TWITTER,
        DataSource.settings["twitter_user_id"].astext == twitter_user.get("id")
    ).first()
    
    if existing_source:
        existing_source.credentials = credentials
        existing_source.name = f"Twitter: @{twitter_user.get('username')}"
        existing_source.is_active = True
        db.commit()
        db.refresh(existing_source)
        return existing_source
    else:
        new_source = DataSource(
            user_id=current_user.id,
            source_type=SourceType.TWITTER,
            name=f"Twitter: @{twitter_user.get('username')}",
            credentials=credentials,
            is_active=True
        )
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        return new_source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(
    source_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a data source"""
    source = db.query(DataSource).filter(
        DataSource.id == source_id,
        DataSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data source not found"
        )
    
    db.delete(source)
    db.commit()
    return None


# Telegram endpoints
@router.post("/telegram/connect", response_model=DataSourceResponse)
async def connect_telegram_bot(
    bot_data: TelegramBotConnect,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Connect Telegram bot"""
    from app.services.telegram_client import TelegramClient
    import asyncio
    
    # Verify bot token
    telegram_client = TelegramClient(bot_data.bot_token)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        bot_info = loop.run_until_complete(telegram_client.get_me())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bot token: {str(e)}"
        )
    finally:
        loop.close()
    
    # Encrypt and store credentials
    credentials = {
        "bot_token": encrypt_data(bot_data.bot_token),
        "bot_username": bot_info.get("result", {}).get("username", ""),
        "bot_id": str(bot_info.get("result", {}).get("id", ""))
    }
    
    # Create or update data source
    existing_source = db.query(DataSource).filter(
        DataSource.user_id == current_user.id,
        DataSource.source_type == SourceType.TELEGRAM,
        DataSource.settings["bot_id"].astext == credentials["bot_id"]
    ).first()
    
    bot_username = credentials.get("bot_username", "bot")
    if existing_source:
        existing_source.credentials = credentials
        existing_source.name = f"Telegram: @{bot_username}"
        existing_source.settings = {"chat_ids": bot_data.chat_ids or []}
        existing_source.is_active = True
        db.commit()
        db.refresh(existing_source)
        return existing_source
    else:
        new_source = DataSource(
            user_id=current_user.id,
            source_type=SourceType.TELEGRAM,
            name=f"Telegram: @{bot_username}",
            credentials=credentials,
            settings={"chat_ids": bot_data.chat_ids or []},
            is_active=True
        )
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        return new_source


# Facebook endpoints
@router.get("/facebook/oauth/init")
async def init_facebook_oauth(
    redirect_uri: str,
    current_user: User = Depends(get_current_active_user)
):
    """Initialize Facebook OAuth flow"""
    if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Facebook OAuth not configured"
        )
    
    facebook_oauth = FacebookOAuth(
        app_id=FACEBOOK_APP_ID,
        app_secret=FACEBOOK_APP_SECRET,
        redirect_uri=redirect_uri
    )
    
    state = secrets.token_urlsafe(32)
    auth_url = facebook_oauth.get_authorization_url(state=state)
    
    return {
        "authorization_url": auth_url,
        "state": state
    }


@router.post("/facebook/oauth/callback", response_model=DataSourceResponse)
async def facebook_oauth_callback(
    callback_data: FacebookOAuthCallback,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Handle Facebook OAuth callback"""
    if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Facebook OAuth not configured"
        )
    
    facebook_oauth = FacebookOAuth(
        app_id=FACEBOOK_APP_ID,
        app_secret=FACEBOOK_APP_SECRET,
        redirect_uri=callback_data.redirect_uri
    )
    
    # Exchange code for tokens
    tokens = await facebook_oauth.exchange_code_for_tokens(callback_data.code)
    access_token = tokens.get("access_token")
    
    # Get long-lived token
    long_lived = await facebook_oauth.get_long_lived_token(access_token)
    long_lived_token = long_lived.get("access_token", access_token)
    
    # Get user info
    user_info = await facebook_oauth.get_user_info(long_lived_token)
    
    # Encrypt and store credentials
    credentials = {
        "access_token": encrypt_data(long_lived_token),
        "expires_in": long_lived.get("expires_in", tokens.get("expires_in")),
        "facebook_user_id": user_info.get("id"),
        "facebook_name": user_info.get("name", "")
    }
    
    # Create or update data source
    existing_source = db.query(DataSource).filter(
        DataSource.user_id == current_user.id,
        DataSource.source_type == SourceType.FACEBOOK,
        DataSource.settings["facebook_user_id"].astext == user_info.get("id")
    ).first()
    
    if existing_source:
        existing_source.credentials = credentials
        existing_source.name = f"Facebook: {user_info.get('name', 'User')}"
        existing_source.is_active = True
        db.commit()
        db.refresh(existing_source)
        return existing_source
    else:
        new_source = DataSource(
            user_id=current_user.id,
            source_type=SourceType.FACEBOOK,
            name=f"Facebook: {user_info.get('name', 'User')}",
            credentials=credentials,
            is_active=True
        )
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        return new_source


# Instagram endpoints
@router.get("/instagram/oauth/init")
async def init_instagram_oauth(
    redirect_uri: str,
    current_user: User = Depends(get_current_active_user)
):
    """Initialize Instagram OAuth flow"""
    if not INSTAGRAM_APP_ID or not INSTAGRAM_APP_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Instagram OAuth not configured"
        )
    
    instagram_oauth = InstagramOAuth(
        app_id=INSTAGRAM_APP_ID,
        app_secret=INSTAGRAM_APP_SECRET,
        redirect_uri=redirect_uri
    )
    
    state = secrets.token_urlsafe(32)
    auth_url = instagram_oauth.get_authorization_url(state=state)
    
    return {
        "authorization_url": auth_url,
        "state": state
    }


@router.post("/instagram/oauth/callback", response_model=DataSourceResponse)
async def instagram_oauth_callback(
    callback_data: InstagramOAuthCallback,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Handle Instagram OAuth callback"""
    if not INSTAGRAM_APP_ID or not INSTAGRAM_APP_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Instagram OAuth not configured"
        )
    
    instagram_oauth = InstagramOAuth(
        app_id=INSTAGRAM_APP_ID,
        app_secret=INSTAGRAM_APP_SECRET,
        redirect_uri=callback_data.redirect_uri
    )
    
    # Exchange code for tokens
    tokens = await instagram_oauth.exchange_code_for_tokens(callback_data.code)
    access_token = tokens.get("access_token")
    
    # Get user info
    user_info = await instagram_oauth.get_user_info(access_token)
    
    # Encrypt and store credentials
    credentials = {
        "access_token": encrypt_data(access_token),
        "user_id": user_info.get("id"),
        "username": user_info.get("username", "")
    }
    
    # Create or update data source
    existing_source = db.query(DataSource).filter(
        DataSource.user_id == current_user.id,
        DataSource.source_type == SourceType.INSTAGRAM,
        DataSource.settings["user_id"].astext == user_info.get("id")
    ).first()
    
    username = user_info.get("username", "user")
    if existing_source:
        existing_source.credentials = credentials
        existing_source.name = f"Instagram: @{username}"
        existing_source.is_active = True
        db.commit()
        db.refresh(existing_source)
        return existing_source
    else:
        new_source = DataSource(
            user_id=current_user.id,
            source_type=SourceType.INSTAGRAM,
            name=f"Instagram: @{username}",
            credentials=credentials,
            settings={"user_id": user_info.get("id")},
            is_active=True
        )
        db.add(new_source)
        db.commit()
        db.refresh(new_source)
        return new_source

