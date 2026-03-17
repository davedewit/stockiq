#!/usr/bin/env python3
"""
Email Flow Test - Tests complete purchase with email sending
Run this after SES is in production mode
"""

import requests
import json
import time

BASE_URL = "https://gxp4jnaa5rozlxrogpgb6t4etu0ncdfn.lambda-url.us-east-1.on.aws"
TEST_EMAIL = "dave@dewit.com.au"  # Use your verified email

def simulate_stripe_webhook():
    """Simulate a successful Stripe payment webhook"""
    
    # First create a checkout session
    payload = {
        "items": [{"product_id": "stockiq-pro", "quantity": 1}],
        "customer_email": TEST_EMAIL,
        "webhook_url": "https://httpbin.org/post"
    }
    
    print("🛒 Creating checkout session...")
    response = requests.post(f"{BASE_URL}/checkout_sessions", json=payload)
    
    if response.status_code != 200:
        print("❌ Failed to create checkout session")
        return False
        
    session_data = response.json()
    session_id = session_data.get('session_id')
    print(f"✅ Session created: {session_id}")
    
    # Simulate Stripe webhook for successful payment
    webhook_payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": f"cs_test_{session_id}",
                "customer_email": TEST_EMAIL,
                "metadata": {
                    "session_id": session_id,
                    "product_id": "stockiq-pro"
                },
                "payment_status": "paid",
                "amount_total": 1499
            }
        }
    }
    
    print("💳 Simulating Stripe webhook...")
    webhook_response = requests.post(f"{BASE_URL}/webhooks", json=webhook_payload)
    
    if webhook_response.status_code == 200:
        print("✅ Webhook processed successfully")
        print("📧 Welcome email should be sent to:", TEST_EMAIL)
        print("⏰ Check your email in 1-2 minutes")
        return True
    else:
        print(f"❌ Webhook failed: {webhook_response.status_code}")
        return False

if __name__ == "__main__":
    print("🧪 TESTING EMAIL FLOW")
    print("=" * 40)
    simulate_stripe_webhook()