"""Stripe webhook handler."""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
import stripe
import logging

from ..database import get_db
from ..models import User
from ..config import settings
from ..services.subscription_service import (
    get_plan_from_price_id,
    update_user_subscription_from_stripe,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

# Initialize Stripe
if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle Stripe webhook events.
    
    This endpoint receives webhook events from Stripe and processes them
    to update user subscriptions in the database.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not settings.stripe_webhook_secret:
        logger.warning("Stripe webhook secret not configured - skipping signature verification")
        # In development, we can skip signature verification
        # In production, this should be properly configured
        try:
            event = stripe.Event.construct_from(
                await request.json(), stripe.api_key
            )
        except Exception as e:
            logger.error(f"Error parsing webhook: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
    else:
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    event_type = event["type"]
    event_data = event["data"]["object"]

    logger.info(f"Received Stripe webhook: {event_type}")

    # Checkout session completed
    if event_type == "checkout.session.completed":
        session = event_data
        await handle_checkout_completed(session, db)

    # Subscription created
    elif event_type == "customer.subscription.created":
        subscription = event_data
        await handle_subscription_created(subscription, db)

    # Subscription updated
    elif event_type == "customer.subscription.updated":
        subscription = event_data
        await handle_subscription_updated(subscription, db)

    # Subscription deleted (canceled)
    elif event_type == "customer.subscription.deleted":
        subscription = event_data
        await handle_subscription_deleted(subscription, db)

    # Invoice payment succeeded
    elif event_type == "invoice.payment_succeeded":
        invoice = event_data
        logger.info(f"Invoice payment succeeded: {invoice['id']}")

    # Invoice payment failed
    elif event_type == "invoice.payment_failed":
        invoice = event_data
        logger.warning(f"Invoice payment failed: {invoice['id']}")
        # TODO: Notify user about failed payment

    else:
        logger.info(f"Unhandled event type: {event_type}")

    return {"status": "success"}


async def handle_checkout_completed(session: dict, db: Session):
    """Handle successful checkout session completion."""
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    user_id = session.get("metadata", {}).get("user_id")

    if not user_id:
        logger.error("No user_id in checkout session metadata")
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"User not found: {user_id}")
        return

    # Update user with Stripe IDs
    user.stripe_customer_id = customer_id
    user.stripe_subscription_id = subscription_id
    
    # Get subscription details to determine plan
    if subscription_id:
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            if subscription.items.data:
                price_id = subscription.items.data[0].price.id
                plan = get_plan_from_price_id(price_id)
                user.subscription_tier = plan
                user.subscription_status = subscription.status
                logger.info(f"Set user {user_id} to plan: {plan}")
        except Exception as e:
            logger.error(f"Error fetching subscription details: {e}")
    
    db.commit()

    logger.info(f"Updated user {user_id} with subscription {subscription_id}")


async def handle_subscription_created(subscription: dict, db: Session):
    """Handle subscription creation."""
    customer_id = subscription.get("customer")
    subscription_id = subscription["id"]

    # Find user by customer ID
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        logger.error(f"User not found for customer: {customer_id}")
        return

    user.stripe_subscription_id = subscription_id
    
    # Update plan based on price
    if subscription.get("items", {}).get("data"):
        price_id = subscription["items"]["data"][0]["price"]["id"]
        plan = get_plan_from_price_id(price_id)
        user.subscription_tier = plan
        user.subscription_status = subscription.get("status", "active")
    
    db.commit()

    logger.info(f"Created subscription {subscription_id} for user {user.id} - Plan: {user.subscription_tier}")


async def handle_subscription_updated(subscription: dict, db: Session):
    """Handle subscription updates."""
    customer_id = subscription.get("customer")
    subscription_id = subscription["id"]
    status = subscription.get("status")

    # Find user by customer ID
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        logger.error(f"User not found for customer: {customer_id}")
        return

    # Update subscription status
    user.subscription_status = status
    
    # Update plan if changed
    if subscription.get("items", {}).get("data"):
        price_id = subscription["items"]["data"][0]["price"]["id"]
        plan = get_plan_from_price_id(price_id)
        user.subscription_tier = plan
    
    db.commit()
    
    logger.info(f"Updated subscription {subscription_id} status to {status} for user {user.id} - Plan: {user.subscription_tier}")


async def handle_subscription_deleted(subscription: dict, db: Session):
    """Handle subscription cancellation."""
    customer_id = subscription.get("customer")
    subscription_id = subscription["id"]

    # Find user by customer ID
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        logger.error(f"User not found for customer: {customer_id}")
        return

    # Clear subscription ID and revert to free tier
    user.stripe_subscription_id = None
    user.subscription_tier = "free"
    user.subscription_status = "canceled"
    db.commit()

    logger.info(f"Deleted subscription {subscription_id} for user {user.id} - Reverted to free tier")
