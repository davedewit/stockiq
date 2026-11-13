#!/usr/bin/env python3
"""Admin #15 (payments), built 12 Nov 2026 as a patch of the live mirrors, so the staged files can always be rebuilt:
    python3 check-tools/pending-payments/patch.py        writes lambda/lambda_function.py (stockiq-payment-handler) and
                                                         dashboard/lambda_function.py (stockiq-dashboard) from lambda-sync/
What it closes (details in Admin #15):
  1. a Stripe event is believed only after it is fetched back from Stripe by its id (a forged body names an id Stripe does not know),
     and the unsigned 'handle_webhook' action is gone; a signature, when STRIPE_WEBHOOK_SECRET is set, is checked and logged (not yet
     enforced: nobody has seen it pass on a real event);
  2. checkout.session.completed switches a plan on only while its subscription is active at Stripe (a replayed old event does nothing);
  3. a 'subscription deleted' or 'updated' event for a subscription that is not the member's current one is ignored (a plan change
     deletes the old subscription, which marked the paying member cancelled and started the deletion of their data);
  4. cancel_subscription proves who is asking (a Cognito ID token, a Google credential or a Facebook access token, verified here),
     finds the subscription itself and ignores any subscription id it is sent;
  5. stockiq-dashboard no longer hands out a member's subscription id (get_subscription_id is removed).
Not done (a plan change is still a new checkout and the old subscription deleted, so a downgrade loses the rest of the paid month):
Subscription.modify with proration would need the upgrade buttons on three pages changed; left as an idea in the register."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))


def sub(text, old, new, count=1):
    assert text.count(old) == count, (old[:70], text.count(old))
    return text.replace(old, new)


# ---------------------------------------------------------------- the payment handler
pay = open(os.path.join(ROOT, 'lambda-sync', 'stockiq-payment-handler', 'lambda_function.py'), encoding='utf-8').read()

pay = sub(pay, "import json\nimport os\nimport boto3\nfrom datetime import datetime\n",
"""import json
import os
import base64
import hashlib
import hmac
import time
import urllib.request
import urllib.parse
import boto3
from datetime import datetime
""")

pay = sub(pay, "def lambda_handler(event, context):", '''# ---- who is asking (Admin #15): the dashboard sends the proof it holds, never an address or a subscription id
class AuthError(Exception):
    pass


COGNITO_ISS = 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_P4lqPzrlY'
COGNITO_CLIENT = '6s3i43db9g6jlgjisr0b3blh56'
GOOGLE_CLIENT = '851713356105-bm61s5e7qf0tkn5ll8jvslhg98ce6pe9.apps.googleusercontent.com'
_JWKS = {}
_SHA256 = bytes.fromhex('3031300d060960864801650304020105000420')      # DigestInfo prefix of SHA-256 (RFC 8017)


def _b64(s):
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


def _fetch_json(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def _jwks(url):
    got = _JWKS.get(url)
    if got and time.time() - got[0] < 6 * 3600:
        return got[1]
    keys = _fetch_json(url)['keys']
    _JWKS[url] = (time.time(), keys)
    return keys


def rs256_ok(signing_input, signature, n_b64, e_b64):
    """RSASSA-PKCS1-v1_5 with SHA-256, in plain Python (no library in this package does it)."""
    n, e = int.from_bytes(_b64(n_b64), 'big'), int.from_bytes(_b64(e_b64), 'big')
    k = (n.bit_length() + 7) // 8
    if len(signature) != k or int.from_bytes(signature, 'big') >= n:
        return False
    tail = _SHA256 + hashlib.sha256(signing_input).digest()
    want = b'\\x00\\x01' + b'\\xff' * (k - len(tail) - 3) + b'\\x00' + tail
    return hmac.compare_digest(pow(int.from_bytes(signature, 'big'), e, n).to_bytes(k, 'big'), want)


def verify_jwt(token, jwks_url, issuers, audience, cognito=False):
    """The claims of a token signed by the identity provider, or AuthError."""
    try:
        head64, claims64, sig64 = str(token).split('.')
        head, claims = json.loads(_b64(head64)), json.loads(_b64(claims64))
        if head.get('alg') != 'RS256':
            raise AuthError('unsupported token')
        key = next((k for k in _jwks(jwks_url) if k.get('kid') == head.get('kid')), None)
        if not key or not rs256_ok((head64 + '.' + claims64).encode(), _b64(sig64), key['n'], key['e']):
            raise AuthError('bad signature')
    except AuthError:
        raise
    except Exception as e:
        raise AuthError(f'unreadable token: {type(e).__name__}')
    if float(claims.get('exp', 0)) < time.time() - 30:
        raise AuthError('expired')
    if claims.get('iss') not in issuers:
        raise AuthError('wrong issuer')
    if (claims.get('aud') if not isinstance(claims.get('aud'), list) else audience if audience in claims['aud'] else None) != audience:
        raise AuthError('wrong audience')
    if cognito and claims.get('token_use') != 'id':
        raise AuthError('not an ID token')
    if not cognito and claims.get('email_verified') not in (True, 'true'):
        raise AuthError('email not verified')
    return claims


def identity_email(body):
    """The email of whoever sent `provider` and `token` (a Cognito ID token, a Google credential or a Facebook access token)."""
    provider, token = str(body.get('provider') or ''), str(body.get('token') or '')
    if not token or len(token) > 6000:
        raise AuthError('no proof of who is asking')
    if provider == 'cognito':
        claims = verify_jwt(token, COGNITO_ISS + '/.well-known/jwks.json', (COGNITO_ISS,), COGNITO_CLIENT, cognito=True)
    elif provider == 'google':
        claims = verify_jwt(token, 'https://www.googleapis.com/oauth2/v3/certs', ('accounts.google.com', 'https://accounts.google.com'), GOOGLE_CLIENT)
    elif provider == 'facebook':
        try:
            claims = _fetch_json('https://graph.facebook.com/me?fields=email&access_token=' + urllib.parse.quote(token))
        except Exception as e:
            raise AuthError(f'Facebook did not accept the token: {type(e).__name__}')
    else:
        raise AuthError('unknown sign-in kind')
    email = str(claims.get('email') or '').strip()
    if not email:
        raise AuthError('the token carries no email')
    return email


def registration_of(email):
    """The member's registration record, tried as the token spells the address and then in lower case."""
    for e in dict.fromkeys([email, email.lower()]):
        item = users_table.get_item(Key={'user_date': f"{e}#registration"}).get('Item')
        if item:
            return item
    return None


def lambda_handler(event, context):''')

pay = sub(pay, """        elif action == 'handle_webhook':
            return handle_webhook(event)
        elif action == 'cancel_subscription':""", """        elif action == 'cancel_subscription':""")

pay = sub(pay, """    except Exception as e:
        print(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,""", """    except AuthError as e:
        print(f"Refused: {e}")
        return {'statusCode': 401, 'body': json.dumps({'success': False, 'error': 'Please sign out and sign in again, then try once more.'})}
    except Exception as e:
        print(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,""")

# the webhook: believe an event only when Stripe confirms it
old_wh = pay[pay.index("def handle_webhook(event):"):pay.index("def handle_subscription_created(session):")]
new_wh = '''def handle_webhook(event):
    """A Stripe event. The body names an event id; the event is fetched back from Stripe with our own key and only that copy is
    believed, so a forged body (any id Stripe does not know) does nothing (Admin #15). The signature, if a signing secret is set,
    is checked and logged but not yet enforced: it has not been seen to pass on a real event."""
    payload = event['body']
    if event.get('isBase64Encoded') and isinstance(payload, str):
        payload = base64.b64decode(payload).decode('utf-8')
    secret, sig_header = os.environ.get('STRIPE_WEBHOOK_SECRET'), (event.get('headers') or {}).get('stripe-signature')
    if secret and sig_header and stripe:
        try:
            stripe.Webhook.construct_event(payload, sig_header, secret)
            print('Webhook signature: ok')
        except Exception as e:
            print(f'Webhook signature: NOT ok ({type(e).__name__}); the event is still checked with Stripe')
    claimed = json.loads(payload) if isinstance(payload, str) else payload
    event_id = str((claimed or {}).get('id') or '')
    if not stripe or not event_id.startswith('evt_'):
        return {'statusCode': 400, 'body': json.dumps({'error': 'Not a Stripe event'})}
    try:
        stripe_event = stripe.Event.retrieve(event_id)
    except Exception as e:
        print(f"Refused: Stripe has no event {event_id[:12]}… ({type(e).__name__})")
        return {'statusCode': 400, 'body': json.dumps({'error': 'Event not found at Stripe'})}
    event_type = stripe_event['type']
    if event_type != claimed.get('type'):
        print(f"Refused: the body said {claimed.get('type')} but Stripe has {event_type}")
        return {'statusCode': 400, 'body': json.dumps({'error': 'Event does not match Stripe'})}
    print(f"Processing webhook: {event_type}")

    if event_type == 'checkout.session.completed':
        handle_subscription_created(stripe_event['data']['object'])
    elif event_type == 'invoice.payment_succeeded':
        handle_subscription_renewal(stripe_event['data']['object'])
    elif event_type == 'customer.subscription.deleted':
        handle_subscription_cancelled(stripe_event['data']['object'])
    elif event_type == 'customer.subscription.updated':
        handle_subscription_updated(stripe_event['data']['object'])
    else:
        print(f"Unhandled webhook type: {event_type}")

    return {'statusCode': 200, 'body': json.dumps({'received': True})}

def is_current(email, subscription_id):
    """False when the member's record names another subscription than this one (a plan change's old subscription, a replayed event).
    A record that names none (a legacy one) counts as current, as before."""
    try:
        record = registration_of(email) or {}
    except Exception as e:
        print(f"Could not read the record to compare subscriptions: {e}")
        return True
    have = record.get('stripeSubscriptionId')
    return not have or not subscription_id or have == subscription_id

'''
pay = pay.replace(old_wh, new_wh)

# checkout.session.completed: only a live subscription switches a plan on; the old one is only cancelled after that
pay = sub(pay, """    # If this is an upgrade, cancel the old subscription
    if is_upgrade and old_subscription_id:""", """    # Only a subscription that is live at Stripe switches a plan on: an old event replayed to us does nothing (Admin #15)
    subscription = stripe.Subscription.retrieve(session['subscription'])
    if subscription['status'] not in ('active', 'trialing'):
        print(f"Ignored: subscription {session['subscription']} is {subscription['status']}, not active")
        return

    # If this is an upgrade, cancel the old subscription
    if is_upgrade and old_subscription_id and old_subscription_id != session['subscription']:""")
pay = sub(pay, """    subscription = stripe.Subscription.retrieve(session['subscription'])
    expiry_date = datetime.fromtimestamp(subscription['current_period_end'])
    today = datetime.now().strftime('%Y-%m-%d')""", """    expiry_date = datetime.fromtimestamp(subscription['current_period_end'])
    today = datetime.now().strftime('%Y-%m-%d')""")

# an update for a subscription that is not the member's current one
pay = sub(pay, """        if not user_email:
            print("No email found for subscription update")
            return
""", """        if not user_email:
            print("No email found for subscription update")
            return
        if subscription.get('status') in ('canceled', 'incomplete_expired') or not is_current(user_email, subscription.get('id')):
            print(f"Ignored an update of subscription {subscription.get('id')} for {user_email}: it is not the current one")
            return
""")

# a deletion of a subscription that is not the member's current one
pay = sub(pay, """    if not user_email:
        return
        
    try:
        users_table.update_item(
            Key={'user_date': f"{user_email}#registration"},
            UpdateExpression='SET subscriptionStatus = :status, updated_at = :timestamp',""", """    if not user_email:
        return

    if not is_current(user_email, subscription.get('id')):
        print(f"Ignored the end of subscription {subscription.get('id')} for {user_email}: the member's current subscription is another one (a plan change)")
        return

    try:
        users_table.update_item(
            Key={'user_date': f"{user_email}#registration"},
            UpdateExpression='SET subscriptionStatus = :status, updated_at = :timestamp',""")

old_cancel = pay[pay.index("def cancel_subscription(body):"):]
new_cancel = '''def cancel_subscription(body):
    """Cancel the asker's own subscription. Who is asking is proved by the token; the subscription is read from their record, and a
    subscription id in the request is ignored (Admin #15: anyone could cancel any member's subscription by sending its id)."""
    if not stripe:
        raise Exception('Stripe not available')

    email = identity_email(body)
    record = registration_of(email)
    subscription_id = (record or {}).get('stripeSubscriptionId')
    if not subscription_id:
        return {'statusCode': 404, 'body': json.dumps({'success': False, 'error': 'No active subscription found'})}

    stripe.Subscription.delete(subscription_id)
    return {'statusCode': 200, 'body': json.dumps({'success': True})}
'''
pay = pay.replace(old_cancel, new_cancel)
# the old subscription ends LAST on a plan change: Stripe's "deleted" event for it can arrive while this function is still running, and
# while the record still named it the event would have counted as the member's own cancellation
i0 = pay.index("    # If this is an upgrade, cancel the old subscription")
i1 = pay.index("    # Clear deletion markers when user subscribes")
old_block = pay[i0:i1]
pay = pay[:i0] + pay[i1:]
marker = '    print(f"Successfully processed subscription for {final_email} - Plan: {plan_type}, Upgrade: {is_upgrade}")'
assert pay.count(marker) == 1
pay = pay.replace(marker, "    # The record names the new subscription now, so the end of the old one is ignored when Stripe reports it\n" + old_block.rstrip('\n') + "\n\n" + marker)
open(os.path.join(HERE, 'lambda', 'lambda_function.py'), 'w', encoding='utf-8').write(pay)

# ---------------------------------------------------------------- the dashboard function: no more handing out subscription ids
dash = open(os.path.join(ROOT, 'lambda-sync', 'stockiq-dashboard', 'lambda_function.py'), encoding='utf-8').read()
dash = sub(dash, """        elif action == 'get_subscription_id':
            return get_subscription_id(body)
""", "")
start = dash.index("def get_subscription_id(data):")
end = dash.index("\n\n", dash.index("return error_response(500, f'Failed to get subscription ID", start))
dash = dash[:start] + dash[end + 2:]
open(os.path.join(HERE, 'dashboard', 'lambda_function.py'), 'w', encoding='utf-8').write(dash)
print('written: lambda/lambda_function.py (payment handler), dashboard/lambda_function.py (dashboard)')
