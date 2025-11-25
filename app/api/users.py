"""
User management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.preferences import UserPreferences
from app.schemas.user import UserUpdate, UserPreferencesUpdate, SubscriptionUpdate
from app.schemas.auth import UserResponse

router = APIRouter()


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user profile"""
    return current_user


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    if user_data.timezone is not None:
        current_user.timezone = user_data.timezone
    if user_data.briefing_time is not None:
        current_user.briefing_time = user_data.briefing_time
    
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/preferences")
async def get_preferences(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user preferences"""
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not preferences:
        # Create default preferences
        preferences = UserPreferences(user_id=current_user.id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    
    return preferences


@router.patch("/preferences")
async def update_preferences(
    prefs_data: UserPreferencesUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not preferences:
        preferences = UserPreferences(user_id=current_user.id)
        db.add(preferences)
    
    if prefs_data.categories_priority is not None:
        preferences.categories_priority = prefs_data.categories_priority
    if prefs_data.topics_interest is not None:
        preferences.topics_interest = prefs_data.topics_interest
    if prefs_data.sources_priority is not None:
        preferences.sources_priority = prefs_data.sources_priority
    if prefs_data.min_relevance_score is not None:
        preferences.min_relevance_score = prefs_data.min_relevance_score
    if prefs_data.max_items_per_briefing is not None:
        preferences.max_items_per_briefing = prefs_data.max_items_per_briefing
    if prefs_data.language is not None:
        preferences.language = prefs_data.language
    if prefs_data.voice_preference is not None:
        preferences.voice_preference = prefs_data.voice_preference
    
    db.commit()
    db.refresh(preferences)
    return preferences


@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_active_user)
):
    """Get user subscription status"""
    return {
        "subscription_status": current_user.subscription_status,
        "subscription_expires_at": current_user.subscription_expires_at,
        "is_active": current_user.is_active
    }


@router.patch("/subscription")
async def update_subscription(
    subscription_data: SubscriptionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update subscription status (cancel/resume)"""
    from datetime import datetime, timedelta
    
    if subscription_data.subscription_status.value == "cancelled":
        # Cancel subscription
        current_user.subscription_status = subscription_data.subscription_status
        # Keep access until expiration date
    elif subscription_data.subscription_status.value == "active":
        # Activate subscription
        current_user.subscription_status = subscription_data.subscription_status
        if not current_user.subscription_expires_at:
            # Set expiration to 30 days from now
            current_user.subscription_expires_at = datetime.utcnow() + timedelta(days=30)
    else:
        current_user.subscription_status = subscription_data.subscription_status
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "subscription_status": current_user.subscription_status,
        "subscription_expires_at": current_user.subscription_expires_at
    }


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Soft delete user account"""
    from datetime import datetime
    
    current_user.deleted_at = datetime.utcnow()
    current_user.is_active = False
    db.commit()
    
    return None

