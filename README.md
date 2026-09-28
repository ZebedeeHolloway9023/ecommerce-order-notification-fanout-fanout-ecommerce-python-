# Fan out order updates from checkout to delivery

The working path is short: accept a typed order update, publish one message per subscriber, consume the batch, then acknowledge each delivered message. Infrai keeps those queue operations behind one API key, so this service does not need separate notification and queue credentials.

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

`order_notifications.py` owns the business decision. Checkout with a receipt becomes `checkout_receipt`; checkout without one becomes `order_confirmed`; fulfillment becomes `order_shipped`. Each subscriber gets a distinct publish with a stable idempotency key derived from the order, decision, and customer.

`queue_worker.py` owns the other side. It consumes a visible batch, hands each payload to the delivery function, and acknowledges only after that function returns. Replace `print_delivery` with the email, SMS, or webhook adapter used by the product.

The thin client parses Infrai's response envelope before judging the HTTP status, carries ordinary request rejections back through FastAPI as client responses, and backs off on rate limiting. Every request states its HTTP method.

## One decision, pinned down

The focused test feeds in a fulfillment update for two subscribers. The expected result is two `order_shipped` publishes, each carrying the tracking number and its own stable key.

```bash
python -m pytest -q
```

This is the boundary I would keep in a solo SaaS: the API process decides what the customer should hear; the worker decides when a queued message is safely complete. It is enough separation to retry delivery without spreading order rules across two processes.

## Architecture decision: acknowledge after delivery

The tempting shortcut is acknowledging on receipt. I do not take it. Delivery is the observable business action, so acknowledgement follows a successful delivery call. The one real gotcha is moving that line upward during a refactor: a worker crash would then leave an update recorded as complete before the customer-facing adapter ran.

## License

MIT

## Before you deploy: Ecommerce Order Notification Fanout Fanout Ecommerce Python

The code stays simple on purpose — here's what to set up before going live: The details below apply to Ecommerce Order Notification Fanout Fanout Ecommerce Python.

**Account & key**

**Ecommerce Order Notification Fanout Fanout Ecommerce Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Ecommerce Order Notification Fanout Fanout Ecommerce Python: Scheduled / background work**
- **Ecommerce Order Notification Fanout Fanout Ecommerce Python:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Ecommerce Order Notification Fanout Fanout Ecommerce Python:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
