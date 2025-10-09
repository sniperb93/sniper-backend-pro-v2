import os
import requests
import stripe
from flask import Blueprint, request, jsonify, current_app

stripe_bp = Blueprint("stripe_bp", __name__)

# Configure Stripe secret key at import time
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


# --- Utilities ---
def _n8n_headers():
    headers = {"Content-Type": "application/json"}
    if (os.getenv("N8N_WEBHOOK_AUTH", "").lower() == "enabled") and os.getenv("N8N_WEBHOOK_TOKEN"):
        headers["Authorization"] = f"Bearer {os.getenv('N8N_WEBHOOK_TOKEN')}"
    return headers


def trigger_n8n_webhook(path: str, payload: dict) -> dict:
    """Best-effort call to n8n webhook. Returns dict with status/info."""
    base = os.getenv("N8N_BASE_URL")
    if not base:
        return {"ok": False, "reason": "N8N_BASE_URL not set"}
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    try:
        r = requests.post(url, json=payload, headers=_n8n_headers(), timeout=8)
        if r.status_code >= 400:
            return {"ok": False, "code": r.status_code, "text": r.text[:400]}
        # try json
        try:
            return {"ok": True, "data": r.json()}
        except Exception:
            return {"ok": True, "text": r.text[:400]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --- Routes ---
@stripe_bp.route("/create_checkout_session", methods=["POST"])
def create_checkout_session():
    data = request.json or {}
    price_id = data.get("price_id")
    customer_email = data.get("customer_email")
    success_url = os.getenv("STRIPE_SUCCESS_URL")
    cancel_url = os.getenv("STRIPE_CANCEL_URL")

    if not price_id:
        return jsonify({"error": "missing price_id"}), 400
    if not success_url or not cancel_url:
        return jsonify({"error": "Stripe success/cancel URLs not configured"}), 400

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=customer_email,
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
        )
        return jsonify({"url": session.url, "session_id": session.id}), 200
    except Exception as e:
        current_app.logger.error("Stripe create session error: %s", e)
        return jsonify({"error": str(e)}), 400


@stripe_bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not endpoint_secret:
        return jsonify({"error": "STRIPE_WEBHOOK_SECRET missing"}), 400

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        current_app.logger.error("Stripe webhook error: %s", e)
        return jsonify({"error": "invalid signature"}), 400

    # Handle main events
    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email")
        price = None
        # Trigger onboarding flow in n8n if configured
        onboarding_path = os.getenv("N8N_STRIPE_ONBOARDING_PATH", "webhook/stripe-onboarding")
        try:
            info = trigger_n8n_webhook(onboarding_path, {
                "event": "checkout.session.completed",
                "email": email,
                "session_id": session.get("id"),
                "price": price,
            })
            if not info.get("ok"):
                current_app.logger.warning("n8n onboarding trigger failed: %s", info)
        except Exception:
            current_app.logger.exception("Failed to trigger onboarding")

    elif event.get("type") == "invoice.payment_failed":
        # Optionally notify n8n or handle in-app logic
        fail_path = os.getenv("N8N_STRIPE_FAILED_PATH", "webhook/stripe-payment-failed")
        try:
            info = trigger_n8n_webhook(fail_path, {
                "event": "invoice.payment_failed",
                "invoice": event["data"].get("object", {}),
            })
            if not info.get("ok"):
                current_app.logger.warning("n8n payment_failed trigger failed: %s", info)
        except Exception:
            current_app.logger.exception("Failed to trigger payment_failed")

    return jsonify({"status": "received"}), 200