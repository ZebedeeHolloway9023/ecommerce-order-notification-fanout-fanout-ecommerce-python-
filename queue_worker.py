"""Consume queued customer updates, deliver them, then acknowledge each message."""

from __future__ import annotations

from typing import Any, Callable

from infrai_client import InfraiQueue


def print_delivery(payload: dict[str, Any]) -> None:
    print(
        f"delivered {payload.get('event')} for order {payload.get('order_id')} "
        f"to {payload.get('destination')}"
    )


def run_once(
    queue: InfraiQueue,
    deliver: Callable[[dict[str, Any]], None] = print_delivery,
) -> int:
    batch = queue.consume(max_messages=10, visibility_timeout=30)
    messages = batch.get("messages") or []
    for message in messages:
        deliver(message.get("payload") or {})
        queue.ack(message_id=str(message["message_id"]))
    return len(messages)


if __name__ == "__main__":
    delivered = run_once(InfraiQueue())
    print(f"acknowledged {delivered} notification(s)")

