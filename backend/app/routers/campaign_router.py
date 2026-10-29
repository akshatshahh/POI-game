"""Opt-ins for notifications about future POI Game campaigns."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import CampaignSubscription, User
from app.schemas import (
    CampaignSubscriptionRequest,
    CampaignSubscriptionResponse,
    CampaignSubscriptionStatus,
)

router = APIRouter(tags=["campaigns"])
CONSENT_VERSION = "campaign-notification-v1"


@router.get(
    "/campaign-subscriptions/me",
    response_model=CampaignSubscriptionStatus,
)
async def get_campaign_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CampaignSubscriptionStatus:
    result = await db.execute(
        select(CampaignSubscription).where(CampaignSubscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()
    if subscription is None:
        return CampaignSubscriptionStatus(subscribed=False)
    return CampaignSubscriptionStatus(
        subscribed=True,
        email=subscription.email,
        created_at=subscription.created_at,
    )


@router.post(
    "/campaign-subscriptions",
    response_model=CampaignSubscriptionResponse,
    status_code=201,
)
async def subscribe_to_campaigns(
    body: CampaignSubscriptionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CampaignSubscription:
    if body.email != user.email.lower():
        raise HTTPException(
            status_code=400,
            detail="Use the email address associated with your account",
        )

    result = await db.execute(
        select(CampaignSubscription).where(CampaignSubscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()

    if subscription is None:
        subscription = CampaignSubscription(
            user_id=user.id,
            email=user.email.lower(),
            consent_version=CONSENT_VERSION,
        )
        db.add(subscription)
    else:
        subscription.email = user.email.lower()
        subscription.consent_version = CONSENT_VERSION

    try:
        await db.flush()
    except IntegrityError as exc:
        # A double-click can race two inserts for the same account. Re-read
        # after rolling back so that repeated opt-ins remain idempotent.
        await db.rollback()
        existing_result = await db.execute(
            select(CampaignSubscription).where(
                CampaignSubscription.user_id == user.id
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None and existing.email == user.email.lower():
            return existing
        raise HTTPException(
            status_code=409,
            detail="The notification preference could not be saved",
        ) from exc

    await db.refresh(subscription)
    return subscription


@router.delete(
    "/campaign-subscriptions/me",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_campaign_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(
        select(CampaignSubscription).where(CampaignSubscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()
    if subscription is not None:
        await db.delete(subscription)
        await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
