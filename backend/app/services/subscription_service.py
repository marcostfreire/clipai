"""Subscription service for plan limits and usage tracking."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import stripe
import logging

from ..models import User, Video
from ..config import settings

logger = logging.getLogger(__name__)

# Plan limits configuration
PLAN_LIMITS = {
    "free": {
        "videos_per_month": 2,
        "clips_per_video": 3,
        "max_video_duration_minutes": 30,
        "watermark": True,
        "priority_queue": False,
        "api_access": False,
    },
    "starter": {
        "videos_per_month": 12,
        "clips_per_video": -1,  # unlimited
        "max_video_duration_minutes": 60,
        "watermark": False,
        "priority_queue": False,
        "api_access": False,
    },
    "pro": {
        "videos_per_month": 50,
        "clips_per_video": -1,  # unlimited
        "max_video_duration_minutes": 120,
        "watermark": False,
        "priority_queue": True,
        "api_access": True,
    },
}

# Stripe Price IDs mapping
STRIPE_PRICE_TO_PLAN = {
    # Free plan (R$0)
    "price_1SUSZdCMwpJ5YuyfbFDEQh5A": "free",
    # Starter plan (R$149/month)
    "price_1SUSowCMwpJ5YuyfvZq5iXYZ": "starter",
    # Pro plan (R$499/month)
    "price_1SUSowCMwpJ5YuyfiRMdGv15": "pro",
}


def get_plan_from_price_id(price_id: str) -> str:
    """Get plan name from Stripe price ID."""
    return STRIPE_PRICE_TO_PLAN.get(price_id, "free")


def get_user_plan(user: Optional[User]) -> str:
    """
    Get user's current subscription plan.
    
    Returns 'free' if user is None or has no active subscription.
    """
    if not user:
        return "free"
    
    # Check subscription_tier first (updated by webhook)
    if user.subscription_tier and user.subscription_tier != "free":
        if user.subscription_status == "active":
            return user.subscription_tier
    
    # Fallback: Check Stripe subscription directly
    if user.stripe_subscription_id and settings.stripe_secret_key:
        try:
            stripe.api_key = settings.stripe_secret_key
            subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
            
            if subscription.status == "active":
                if subscription.items.data:
                    price_id = subscription.items.data[0].price.id
                    return get_plan_from_price_id(price_id)
        except Exception as e:
            logger.error(f"Error fetching Stripe subscription: {e}")
    
    return "free"


def get_plan_limits(plan: str) -> Dict[str, Any]:
    """Get limits for a specific plan."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def count_user_videos_this_month(db: Session, user_id: str) -> int:
    """
    Count how many videos a user has processed this month.
    
    Counts videos that are queued, processing, or completed.
    """
    # Get first day of current month
    today = datetime.utcnow()
    first_day_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Count videos created this month by this user
    count = db.query(func.count(Video.id)).filter(
        and_(
            Video.user_id == user_id,
            Video.created_at >= first_day_of_month,
            Video.status.in_(["queued", "processing", "completed"])
        )
    ).scalar()
    
    return count or 0


def check_video_upload_allowed(
    db: Session, 
    user: Optional[User]
) -> Dict[str, Any]:
    """
    Check if user can upload another video based on their plan limits.
    
    Returns a dict with:
    - allowed: bool
    - reason: str (if not allowed)
    - plan: str
    - used: int
    - limit: int
    - remaining: int
    """
    plan = get_user_plan(user)
    limits = get_plan_limits(plan)
    video_limit = limits["videos_per_month"]
    
    # Anonymous users get free tier limits but can't track usage
    if not user:
        return {
            "allowed": True,  # Allow anonymous uploads but with free tier features
            "plan": "free",
            "used": 0,
            "limit": video_limit,
            "remaining": video_limit,
            "message": "Faça login para acompanhar seu uso",
        }
    
    # Count videos this month
    used = count_user_videos_this_month(db, user.id)
    remaining = max(0, video_limit - used)
    
    if used >= video_limit:
        return {
            "allowed": False,
            "reason": f"Você atingiu o limite de {video_limit} vídeos por mês no plano {plan.title()}",
            "plan": plan,
            "used": used,
            "limit": video_limit,
            "remaining": 0,
            "upgrade_url": "/pricing",
        }
    
    return {
        "allowed": True,
        "plan": plan,
        "used": used,
        "limit": video_limit,
        "remaining": remaining,
    }


def get_user_usage_stats(db: Session, user: User) -> Dict[str, Any]:
    """
    Get complete usage statistics for a user.
    
    Returns plan info, limits, and current usage.
    """
    plan = get_user_plan(user)
    limits = get_plan_limits(plan)
    used = count_user_videos_this_month(db, user.id)
    video_limit = limits["videos_per_month"]
    
    # Calculate days until reset
    today = datetime.utcnow()
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    days_until_reset = (next_month - today).days
    
    return {
        "plan": plan,
        "plan_display_name": plan.title(),
        "subscription_status": user.subscription_status or "active",
        "limits": {
            "videos_per_month": video_limit,
            "clips_per_video": limits["clips_per_video"],
            "max_video_duration_minutes": limits["max_video_duration_minutes"],
            "watermark": limits["watermark"],
            "priority_queue": limits["priority_queue"],
            "api_access": limits["api_access"],
        },
        "usage": {
            "videos_this_month": used,
            "videos_remaining": max(0, video_limit - used),
            "percentage_used": round((used / video_limit) * 100, 1) if video_limit > 0 else 0,
        },
        "reset": {
            "days_until_reset": days_until_reset,
            "reset_date": next_month.strftime("%Y-%m-%d"),
        },
        "stripe_customer_id": user.stripe_customer_id,
        "stripe_subscription_id": user.stripe_subscription_id,
    }


def update_user_subscription_from_stripe(
    db: Session, 
    user: User, 
    subscription: Dict[str, Any]
) -> User:
    """
    Update user's subscription info from Stripe webhook data.
    """
    # Get plan from price ID
    if subscription.get("items", {}).get("data"):
        price_id = subscription["items"]["data"][0]["price"]["id"]
        plan = get_plan_from_price_id(price_id)
        user.subscription_tier = plan
    
    # Update status
    user.subscription_status = subscription.get("status", "active")
    user.stripe_subscription_id = subscription.get("id")
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Updated user {user.id} subscription: plan={user.subscription_tier}, status={user.subscription_status}")
    
    return user
