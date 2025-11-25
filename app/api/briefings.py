"""
Briefings API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.briefing import Briefing, BriefingContent, BriefingStatus
from app.schemas.briefing import BriefingResponse, BriefingDetailResponse
from app.tasks.briefing import generate_briefing

router = APIRouter()


@router.get("/", response_model=List[BriefingResponse])
async def get_briefings(
    days: int = 7,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's briefings (last N days)"""
    cutoff_date = date.today() - timedelta(days=days)
    
    briefings = db.query(Briefing).filter(
        Briefing.user_id == current_user.id,
        Briefing.date >= cutoff_date
    ).order_by(Briefing.date.desc()).all()
    
    return briefings


@router.get("/today", response_model=Optional[BriefingResponse])
async def get_today_briefing(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get today's briefing"""
    briefing = db.query(Briefing).filter(
        Briefing.user_id == current_user.id,
        Briefing.date == date.today()
    ).first()
    
    return briefing


@router.get("/{briefing_id}", response_model=BriefingDetailResponse)
async def get_briefing(
    briefing_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get briefing details with content items"""
    briefing = db.query(Briefing).filter(
        Briefing.id == briefing_id,
        Briefing.user_id == current_user.id
    ).first()
    
    if not briefing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Briefing not found"
        )
    
    # Get briefing content
    briefing_content = db.query(BriefingContent).filter(
        BriefingContent.briefing_id == briefing.id
    ).order_by(BriefingContent.order).all()
    
    # Format response
    from app.models.content import ContentItem
    content_items = []
    for bc in briefing_content:
        content = db.query(ContentItem).filter(ContentItem.id == bc.content_id).first()
        content_items.append({
            "id": str(bc.id),
            "content_id": str(bc.content_id),
            "order": bc.order,
            "included_reason": bc.included_reason,
            "content_title": content.title if content else None,
            "content_text": (content.text_content[:200] if content and content.text_content else None)
        })
    
    return {
        **BriefingResponse.from_orm(briefing).dict(),
        "content_items": content_items
    }


@router.post("/generate", response_model=BriefingResponse)
async def trigger_briefing_generation(
    target_date: Optional[date] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Manually trigger briefing generation"""
    if not target_date:
        target_date = date.today()
    
    # Check if briefing already exists
    existing = db.query(Briefing).filter(
        Briefing.user_id == current_user.id,
        Briefing.date == target_date
    ).first()
    
    if existing and existing.status == BriefingStatus.DELIVERED:
        return existing
    
    # Queue briefing generation
    task = generate_briefing.delay(str(current_user.id), target_date.isoformat())
    
    # Create or update briefing record
    if existing:
        existing.status = BriefingStatus.GENERATING
        briefing = existing
    else:
        briefing = Briefing(
            user_id=current_user.id,
            date=target_date,
            status=BriefingStatus.GENERATING
        )
        db.add(briefing)
    
    db.commit()
    db.refresh(briefing)
    
    return briefing


@router.post("/{briefing_id}/mark-delivered", response_model=BriefingResponse)
async def mark_briefing_delivered(
    briefing_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark briefing as delivered"""
    briefing = db.query(Briefing).filter(
        Briefing.id == briefing_id,
        Briefing.user_id == current_user.id
    ).first()
    
    if not briefing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Briefing not found"
        )
    
    briefing.status = BriefingStatus.DELIVERED
    briefing.delivered_at = datetime.utcnow()
    
    db.commit()
    db.refresh(briefing)
    
    return briefing

