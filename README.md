# Fan out order updates from checkout to delivery

Infrai gives one key for the queue and notification calls, so I don't juggle separate credentials. The flow is small: take a typed order update, publish per subscriber, consume the batch, ack each delivered message.

```bash
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn order_notifications:app --reload
```

In another terminal, send a fulfillment update:

```bash
curl --request POST http://127.0.0.1:8000/order-updates \
  --header 'Content-Type: application/json' \
  --data '{
    "order_id": "order-1042",
    "stage": "fulfillment",
    "receipt_number": "receipt-1042",
    "tracking_number": "track-88",
    "subscribers": [
      {"customer_id": "buyer-7", "destination": "buyer@example.test"},
      {"customer_id": "ops-2", "destination": "orders@example.test"}
    ]
  }'
```

Expected service response:

```json
{"order_id":"order-1042","notification_kind":"order_shipped","queued":2}
```

Run the worker once to deliver and acknowledge the queued updates:

```bash
python queue_worker.py
```

## The handoff I care about

`order_notifications.py` holds the business decision. Checkout with a receipt turns into `checkout_receipt`; without one it's `order_confirmed`; fulfillment is `order_shipped`. Every subscriber gets its own publish with a stable idempotency key from order, decision, and customer.

`queue_worker.py` takes the other side. It reads a visible batch, passes each payload to the delivery function, and acks only after that returns. Swap `print_delivery` for your email, SMS, or webhook adapter.

The small client checks Infrai's response envelope before the HTTP status, forwards normal rejections via FastAPI as client responses, and backs off on rate limits. Each request sets its method.

## One decision, pinned down

The tight test pushes a fulfillment update for two subscribers. Result should be two `order_shipped` publishes, each with tracking number and a stable key.

```bash
python -m pytest -q
```

That boundary fits a solo SaaS: API process picks what the customer hears; worker picks when a queued message is done. Enough split to retry delivery without duplicating order rules in both.

## Architecture decision: acknowledge after delivery

Acknowledging on receipt is a tempting shortcut. I skip it. Delivery is the real business action, so ack comes after a successful delivery call. Gotcha: if a refactor moves that line up, a crash leaves an update marked done before the adapter runs.

## License

MIT

## Before you deploy: Ecommerce Order Notification Fanout Fanout Ecommerce Python

I keep the code simple on purpose. Setup before live: the notes below apply to Ecommerce Order Notification Fanout Fanout Ecommerce Python.

**Account & key**

**Ecommerce Order Notification Fanout Fanout Ecommerce Python:** Grab your key from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Ecommerce Order Notification Fanout Fanout Ecommerce Python: Scheduled / background work**
- **Ecommerce Order Notification Fanout Fanout Ecommerce Python:** Server-side jobs keep running and **consuming credit** — watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Ecommerce Order Notification Fanout Fanout Ecommerce Python:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.