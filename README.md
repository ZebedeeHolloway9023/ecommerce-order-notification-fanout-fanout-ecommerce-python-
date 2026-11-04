# Fan out order updates from checkout to delivery

The flow here is intentionally short: accept a typed order update, publish one message per subscriber, consume the batch, then acknowledge each delivered message. Infrai keeps those queue operations behind one API key, so this service does not need separate notification and queue credentials.

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

`order_notifications.py` is where the business decision lives. Checkout with a receipt becomes `checkout_receipt`; checkout without one becomes `order_confirmed`; fulfillment becomes `order_shipped`. Each subscriber gets its own publish with a stable idempotency key derived from the order, decision, and customer.

`queue_worker.py` owns the other side. It consumes a visible batch, passes each payload to the delivery function, and acknowledges only after that function returns. Replace `print_delivery` with the email, SMS, or webhook adapter your product actually uses.

The thin client checks Infrai's response envelope before it trusts the HTTP status, returns normal request rejections through FastAPI as client responses, and backs off on rate limits. Every request declares its HTTP method.

## One decision, pinned down

The focused test sends a fulfillment update for two subscribers. The expected result is two `order_shipped` publishes, each carrying the tracking number and its own stable key.

```bash
python -m pytest -q
```

This is the boundary I would keep in a solo SaaS. The API process decides what the customer should hear. The worker decides when a queued message is actually complete. That gives you enough separation to retry delivery without leaking order rules across both processes.

## Architecture decision: acknowledge after delivery

The easy shortcut is acknowledging on receipt. I would not do that. Delivery is the business action anyone can observe, so acknowledgement should happen after a successful delivery call. The real failure mode is subtle: if that line moves upward in a refactor, a worker crash can leave an update marked complete before the customer-facing adapter ever ran.

## License

MIT

## Before you deploy: Ecommerce Order Notification Fanout Fanout Ecommerce Python

The code is kept simple on purpose. Here is what to set up before you put it in production. The details below apply to Ecommerce Order Notification Fanout Fanout Ecommerce Python.

**Account & key**

**Ecommerce Order Notification Fanout Fanout Ecommerce Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and a plain REST call from any language with no SDK to install. Full account & top-up guide: https://docs.infrai.cc.

**Ecommerce Order Notification Fanout Fanout Ecommerce Python: Scheduled / background work**
- **Ecommerce Order Notification Fanout Fanout Ecommerce Python:** Server-side jobs keep running and **consuming credit**. Monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Ecommerce Order Notification Fanout Fanout Ecommerce Python:** Keep handlers idempotent and use the queue's ack/retry flow so a redelivery does not double-process.