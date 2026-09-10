from order_notifications import OrderStage, OrderUpdate, Subscriber, fanout_order_update


class RecordingPublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[dict, str]] = []

    def publish(self, payload: dict, idempotency_key: str) -> dict:
        self.calls.append((payload, idempotency_key))
        return {}


def test_fulfillment_fans_out_a_shipping_update_to_every_subscriber() -> None:
    publisher = RecordingPublisher()
    update = OrderUpdate(
        order_id="order-1042",
        stage=OrderStage.FULFILLMENT,
        receipt_number="receipt-1042",
        tracking_number="track-88",
        subscribers=[
            Subscriber(customer_id="buyer-7", destination="buyer@example.test"),
            Subscriber(customer_id="ops-2", destination="orders@example.test"),
        ],
    )

    result = fanout_order_update(update, publisher)

    assert result.model_dump() == {
        "order_id": "order-1042",
        "notification_kind": "order_shipped",
        "queued": 2,
    }
    assert [call[0]["event"] for call in publisher.calls] == [
        "order_shipped",
        "order_shipped",
    ]
    assert publisher.calls[0][0]["tracking_number"] == "track-88"
    assert [call[1] for call in publisher.calls] == [
        "order-1042:order_shipped:buyer-7",
        "order-1042:order_shipped:ops-2",
    ]

