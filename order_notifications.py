"""Checkout and fulfillment updates published as subscriber notifications."""

from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from infrai_client import InfraiError, InfraiQueue


class OrderStage(str, Enum):
    CHECKOUT = "checkout"
    FULFILLMENT = "fulfillment"


class Subscriber(BaseModel):
    customer_id: str = Field(min_length=1)
    destination: str = Field(min_length=1)


class OrderUpdate(BaseModel):
    order_id: str = Field(min_length=1)
    stage: OrderStage
    subscribers: list[Subscriber] = Field(min_length=1)
    receipt_number: str | None = None
    tracking_number: str | None = None


class FanoutResult(BaseModel):
    order_id: str
    notification_kind: str
    queued: int


def notification_kind(update: OrderUpdate) -> str:
    if update.stage == OrderStage.FULFILLMENT:
        return "order_shipped"
    return "checkout_receipt" if update.receipt_number else "order_confirmed"


def fanout_order_update(update: OrderUpdate, publisher: Any) -> FanoutResult:
    kind = notification_kind(update)
    for subscriber in update.subscribers:
        payload = {
            "event": kind,
            "order_id": update.order_id,
            "customer_id": subscriber.customer_id,
            "destination": subscriber.destination,
            "receipt_number": update.receipt_number,
            "tracking_number": update.tracking_number,
        }
        publisher.publish(
            payload=payload,
            idempotency_key=f"{update.order_id}:{kind}:{subscriber.customer_id}",
        )
    return FanoutResult(
        order_id=update.order_id,
        notification_kind=kind,
        queued=len(update.subscribers),
    )


app = FastAPI(title="Order notification fanout")


@app.post("/order-updates", response_model=FanoutResult)
def publish_order_update(update: OrderUpdate) -> FanoutResult:
    try:
        return fanout_order_update(update, InfraiQueue())
    except InfraiError as error:
        client_status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": error.code, "message": str(error)},
        ) from error
