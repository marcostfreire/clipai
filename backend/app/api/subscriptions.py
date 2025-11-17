"""Subscription and billing endpoints using Stripe."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import stripe
from typing import Optional

from ..database import get_db
from ..models import User
from ..config import settings
from .auth import get_current_user

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

# Initialize Stripe
if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key
else:
    raise ValueError("STRIPE_SECRET_KEY not configured")


class CreateCheckoutRequest(BaseModel):
    """Request body for creating a checkout session."""

    price_id: str
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    """Response containing the Stripe checkout session URL."""

    url: str
    session_id: str


class SubscriptionStatusResponse(BaseModel):
    """User's subscription status."""

    plan: str  # 'free', 'starter', 'pro'
    status: str  # 'active', 'canceled', 'past_due', etc.
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False


@router.post("/create-checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout session for subscription.
    
    This endpoint creates a Stripe Checkout session and returns the URL
    to redirect the user to complete payment.
    """
    try:
        # Create or retrieve Stripe customer
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={"user_id": str(current_user.id)},
            )
            current_user.stripe_customer_id = customer.id
            db.commit()
        else:
            customer_id = current_user.stripe_customer_id

        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": request.price_id,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={
                "user_id": str(current_user.id),
            },
            allow_promotion_codes=True,
            billing_address_collection="required",
        )

        return CheckoutSessionResponse(
            url=checkout_session.url,
            session_id=checkout_session.id,
        )

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}",
        )


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's subscription status.
    
    Returns the user's current plan and subscription details.
    """
    try:
        # If no Stripe subscription, user is on free plan
        if not current_user.stripe_subscription_id:
            return SubscriptionStatusResponse(
                plan="free",
                status="active",
            )

        # Retrieve subscription from Stripe
        subscription = stripe.Subscription.retrieve(
            current_user.stripe_subscription_id
        )

        # Determine plan based on price ID
        plan = "free"
        if subscription.items.data:
            price_id = subscription.items.data[0].price.id
            if price_id == settings.stripe_price_pro:
                plan = "pro"
            elif price_id == settings.stripe_price_starter:
                plan = "starter"

        return SubscriptionStatusResponse(
            plan=plan,
            status=subscription.status,
            current_period_end=str(subscription.current_period_end),
            cancel_at_period_end=subscription.cancel_at_period_end,
        )

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve subscription status: {str(e)}",
        )


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
):
    """
    Cancel user's subscription at the end of the billing period.
    
    The user will retain access until the end of their current billing period.
    """
    try:
        if not current_user.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active subscription to cancel",
            )

        # Cancel subscription at period end
        subscription = stripe.Subscription.modify(
            current_user.stripe_subscription_id,
            cancel_at_period_end=True,
        )

        return {
            "message": "Subscription will be canceled at the end of the billing period",
            "current_period_end": subscription.current_period_end,
        }

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}",
        )


@router.post("/reactivate")
async def reactivate_subscription(
    current_user: User = Depends(get_current_user),
):
    """
    Reactivate a subscription that was set to cancel.
    
    This only works if the subscription hasn't been canceled yet.
    """
    try:
        if not current_user.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No subscription to reactivate",
            )

        # Remove cancel_at_period_end flag
        subscription = stripe.Subscription.modify(
            current_user.stripe_subscription_id,
            cancel_at_period_end=False,
        )

        return {
            "message": "Subscription reactivated successfully",
            "current_period_end": subscription.current_period_end,
        }

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reactivate subscription: {str(e)}",
        )


@router.get("/portal")
async def get_customer_portal(
    current_user: User = Depends(get_current_user),
):
    """
    Get Stripe Customer Portal URL for managing subscription.
    
    Redirects user to Stripe's hosted portal where they can manage
    their payment methods, view invoices, and cancel subscriptions.
    """
    try:
        if not current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Stripe customer found",
            )

        # Create portal session
        # Get base URL from oauth_redirect_uri or use default
        base_url = "https://frontend-xi-hazel-22.vercel.app"
        if settings.oauth_redirect_uri and "://" in settings.oauth_redirect_uri:
            base_url = settings.oauth_redirect_uri.rsplit('/api', 1)[0]
        
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=f"{base_url}/videos",
        )

        return {"url": portal_session.url}

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create portal session: {str(e)}",
        )
