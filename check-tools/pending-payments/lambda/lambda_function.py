import json
import os
import base64
import hashlib
import hmac
import time
import urllib.request
import urllib.parse
import boto3
from datetime import datetime

import sys
sys.path.insert(0, '/opt/python')
sys.path.insert(0, './python')

try:
    import stripe
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
except ImportError:
    stripe = None

dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table('stockiq-user-tracking')

# ---- who is asking (Admin #15): the dashboard sends the proof it holds, never an address or a subscription id
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
    want = b'\x00\x01' + b'\xff' * (k - len(tail) - 3) + b'\x00' + tail
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


def lambda_handler(event, context):
    try:
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        action = body.get('action')
        
        # Check if this is a direct webhook call from Stripe
        if not body.get('action') and event.get('headers', {}).get('stripe-signature'):
            return handle_webhook(event)
        
        if action == 'create_checkout_session':
            return create_checkout_session(body)
        elif action == 'cancel_subscription':
            return cancel_subscription(body)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid action'})
            }
            
    except AuthError as e:
        print(f"Refused: {e}")
        return {'statusCode': 401, 'body': json.dumps({'success': False, 'error': 'Please sign out and sign in again, then try once more.'})}
    except Exception as e:
        print(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_user_subscription_info(user_email):
    """Get existing subscription info for a user"""
    try:
        response = users_table.get_item(
            Key={'user_date': f"{user_email}#registration"}
        )
        if 'Item' in response:
            item = response['Item']
            return {
                'exists': True,
                'customer_id': item.get('stripeCustomerId'),
                'subscription_id': item.get('stripeSubscriptionId'),
                'current_plan': item.get('planType'),
                'status': item.get('subscriptionStatus')
            }
        return {'exists': False}
    except Exception as e:
        print(f"Error getting user subscription info: {e}")
        return {'exists': False}

def create_checkout_session(body):
    if not stripe:
        raise Exception('Stripe not available')
        
    plan_type = body.get('plan_type')
    user_email = body.get('user_email')
    
    if not plan_type:
        raise Exception('plan_type required')
    
    is_test_mode = os.environ.get('STRIPE_SECRET_KEY', '').startswith('sk_test_')
    
    if is_test_mode:
        price_ids = {
            'starter': 'price_1SDe2HGpPmyfuTinxE05mHJb',
            'pro': 'price_1SDe2IGpPmyfuTink4D5Nkqq',
            'elite': 'price_1SDe2IGpPmyfuTinWr13Zo9z'
        }
    else:
        price_ids = {
            'starter': 'price_1SDOEXGpPmyfuTinTnV688OA',
            'pro': 'price_1SDOHRGpPmyfuTingpXYAaGI', 
            'elite': 'price_1SDOHlGpPmyfuTinXGamKSW4'
        }
    
    if plan_type not in price_ids:
        raise Exception(f'Invalid plan type: {plan_type}')
    
    # Check for existing subscription
    subscription_info = get_user_subscription_info(user_email) if user_email else {'exists': False}
    
    # Create checkout session parameters
    checkout_params = {
        'payment_method_types': ['card'],
        'line_items': [{'price': price_ids[plan_type], 'quantity': 1}],
        'mode': 'subscription',
        'success_url': body.get('success_url'),
        'cancel_url': body.get('cancel_url'),
        'metadata': {
            'user_email': user_email or 'social_user', 
            'plan_type': plan_type,
            'is_upgrade': 'true' if subscription_info['exists'] else 'false',
            'old_subscription_id': subscription_info.get('subscription_id', ''),
            'old_plan_type': subscription_info.get('current_plan', '')
        },
        'billing_address_collection': 'required'
    }
    
    # If user has existing subscription, use their customer ID
    if subscription_info['exists'] and subscription_info.get('customer_id'):
        checkout_params['customer'] = subscription_info['customer_id']
        print(f"Using existing customer ID for upgrade: {subscription_info['customer_id']}")
    elif user_email:
        checkout_params['customer_email'] = user_email
    
    session = stripe.checkout.Session.create(**checkout_params)
    
    return {'statusCode': 200, 'body': json.dumps({'checkout_url': session.url})}

def handle_webhook(event):
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

def handle_subscription_created(session):
    user_email = session['metadata'].get('user_email')
    plan_type = session['metadata']['plan_type']
    is_upgrade = session['metadata'].get('is_upgrade') == 'true'
    old_subscription_id = session['metadata'].get('old_subscription_id')
    
    print(f"Processing subscription creation - Email: {user_email}, Plan: {plan_type}, Is Upgrade: {is_upgrade}")
    
    # Always get email from customer (this will be the real email entered in Stripe checkout)
    customer = stripe.Customer.retrieve(session['customer'])
    customer_email = customer['email']
    
    # Use customer email as the primary email for the subscription
    final_email = customer_email if customer_email else user_email
    
    if not final_email:
        print(f"Warning: No email found for subscription {session['subscription']}")
        return
    
    # Only a subscription that is live at Stripe switches a plan on: an old event replayed to us does nothing (Admin #15)
    subscription = stripe.Subscription.retrieve(session['subscription'])
    if subscription['status'] not in ('active', 'trialing'):
        print(f"Ignored: subscription {session['subscription']} is {subscription['status']}, not active")
        return

    # Clear deletion markers when user subscribes
    try:
        lambda_client = boto3.client('lambda')
        lambda_client.invoke(
            FunctionName='stockiq-dashboard',
            InvocationType='Event',
            Payload=json.dumps({
                'body': json.dumps({
                    'action': 'clear_deletion_markers',
                    'userId': final_email
                })
            })
        )
        print(f"Cleared deletion markers for {final_email}")
    except Exception as e:
        print(f"Error clearing deletion markers: {e}")
    
    expiry_date = datetime.fromtimestamp(subscription['current_period_end'])
    today = datetime.now().strftime('%Y-%m-%d')
    
    # For upgrades, preserve existing user_id
    if is_upgrade:
        try:
            existing_user = users_table.get_item(
                Key={'user_date': f"{final_email}#registration"}
            )
            if 'Item' in existing_user:
                user_id = existing_user['Item']['userId']
                print(f"Preserving existing user ID: {user_id}")
            else:
                user_id = f"user_{int(datetime.now().timestamp())}_{hash(final_email) % 10000}"
        except Exception as e:
            print(f"Error getting existing user ID: {e}")
            user_id = f"user_{int(datetime.now().timestamp())}_{hash(final_email) % 10000}"
    else:
        user_id = f"user_{int(datetime.now().timestamp())}_{hash(final_email) % 10000}"
    
    plan_config = {
        'starter': {'daily_limit': 15},
        'pro': {'daily_limit': 50}, 
        'elite': {'daily_limit': 999999}
    }
    config = plan_config.get(plan_type, {'daily_limit': 15})
    
    # Update registration record
    users_table.put_item(
        Item={
            'user_date': f"{final_email}#registration",
            'email': final_email,
            'userId': user_id,
            'registrationTime': datetime.now().isoformat() if not is_upgrade else existing_user.get('Item', {}).get('registrationTime', datetime.now().isoformat()),
            'subscriptionStatus': 'active',
            'planType': plan_type,
            'stripeCustomerId': session['customer'],
            'stripeSubscriptionId': session['subscription'],
            'expiryDate': expiry_date.strftime('%Y-%m-%d'),
            'dailyLimit': config['daily_limit'],
            'updated_at': datetime.now().isoformat(),
            'lastUpgrade': datetime.now().isoformat() if is_upgrade else None
        }
    )
    
    # Update today's usage record with new limits
    users_table.put_item(
        Item={
            'user_date': f"{final_email}#{today}",
            'email': final_email,
            'userId': user_id,
            'date': today,
            'usage_count': 0,  # Reset usage count on upgrade
            'dailyLimit': config['daily_limit'],
            'expiryDate': expiry_date.strftime('%Y-%m-%d'),
            'planType': plan_type,
            'subscriptionStatus': 'active',
            'stripeCustomerId': session['customer'],
            'stripeSubscriptionId': session['subscription'],
            'updated_at': datetime.now().isoformat()
        }
    )
    
    # The record names the new subscription now, so the end of the old one is ignored when Stripe reports it
    # If this is an upgrade, cancel the old subscription
    if is_upgrade and old_subscription_id and old_subscription_id != session['subscription']:
        try:
            print(f"Canceling old subscription: {old_subscription_id}")
            stripe.Subscription.delete(old_subscription_id)
            print(f"Successfully canceled old subscription: {old_subscription_id}")
        except Exception as e:
            print(f"Error canceling old subscription {old_subscription_id}: {e}")
            # Continue with new subscription creation even if old cancellation fails
    

    print(f"Successfully processed subscription for {final_email} - Plan: {plan_type}, Upgrade: {is_upgrade}")

def handle_subscription_updated(subscription):
    """Handle subscription updates (plan changes, etc.)"""
    try:
        customer = stripe.Customer.retrieve(subscription['customer'])
        user_email = customer['email']
        
        if not user_email:
            print("No email found for subscription update")
            return
        if subscription.get('status') in ('canceled', 'incomplete_expired') or not is_current(user_email, subscription.get('id')):
            print(f"Ignored an update of subscription {subscription.get('id')} for {user_email}: it is not the current one")
            return
        
        # Get the new plan type from subscription items
        if subscription['items']['data']:
            price_id = subscription['items']['data'][0]['price']['id']
            
            # Map price IDs to plan types
            price_to_plan = {
                'price_1SDOEXGpPmyfuTinTnV688OA': 'starter',
                'price_1SDOHRGpPmyfuTingpXYAaGI': 'pro',
                'price_1SDOHlGpPmyfuTinXGamKSW4': 'elite',
                # Test mode prices
                'price_1SDe2HGpPmyfuTinxE05mHJb': 'starter',
                'price_1SDe2IGpPmyfuTink4D5Nkqq': 'pro',
                'price_1SDe2IGpPmyfuTinWr13Zo9z': 'elite'
            }
            
            new_plan_type = price_to_plan.get(price_id)
            if not new_plan_type:
                print(f"Unknown price ID: {price_id}")
                return
            
            expiry_date = datetime.fromtimestamp(subscription['current_period_end'])
            
            plan_config = {
                'starter': {'daily_limit': 15},
                'pro': {'daily_limit': 50}, 
                'elite': {'daily_limit': 999999}
            }
            config = plan_config.get(new_plan_type, {'daily_limit': 15})
            
            # Update user's plan
            users_table.update_item(
                Key={'user_date': f"{user_email}#registration"},
                UpdateExpression='SET planType = :plan, dailyLimit = :limit, expiryDate = :expiry, updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':plan': new_plan_type,
                    ':limit': config['daily_limit'],
                    ':expiry': expiry_date.strftime('%Y-%m-%d'),
                    ':timestamp': datetime.now().isoformat()
                }
            )
            
            print(f"Updated subscription for {user_email} to {new_plan_type}")
            
    except Exception as e:
        print(f"Error handling subscription update: {e}")

def handle_subscription_renewal(invoice):
    if not invoice.get('subscription'):
        return
        
    subscription = stripe.Subscription.retrieve(invoice['subscription'])
    customer = stripe.Customer.retrieve(invoice['customer'])
    user_email = customer['email']
    
    if not user_email:
        return
        
    expiry_date = datetime.fromtimestamp(subscription['current_period_end'])
    
    try:
        users_table.update_item(
            Key={'user_date': f"{user_email}#registration"},
            UpdateExpression='SET expiryDate = :expiry, subscriptionStatus = :status, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':expiry': expiry_date.strftime('%Y-%m-%d'),
                ':status': 'active',
                ':timestamp': datetime.now().isoformat()
            }
        )
        print(f"Renewed subscription for {user_email}")
    except Exception as e:
        print(f"Error updating renewal: {e}")

def handle_subscription_cancelled(subscription):
    customer = stripe.Customer.retrieve(subscription['customer'])
    user_email = customer['email']
    
    if not user_email:
        return

    if not is_current(user_email, subscription.get('id')):
        print(f"Ignored the end of subscription {subscription.get('id')} for {user_email}: the member's current subscription is another one (a plan change)")
        return

    try:
        users_table.update_item(
            Key={'user_date': f"{user_email}#registration"},
            UpdateExpression='SET subscriptionStatus = :status, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':status': 'cancelled',
                ':timestamp': datetime.now().isoformat()
            }
        )
        print(f"Cancelled subscription for {user_email}")
    except Exception as e:
        print(f"Error updating cancellation: {e}")
    
    # Set 30-day deletion when user unsubscribes
    try:
        lambda_client = boto3.client('lambda')
        lambda_client.invoke(
            FunctionName='stockiq-dashboard',
            InvocationType='Event',
            Payload=json.dumps({
                'body': json.dumps({
                    'action': 'set_subscription_end_ttl',
                    'userId': user_email
                })
            })
        )
        print(f"Set 30-day deletion for {user_email}")
    except Exception as e:
        print(f"Error setting deletion TTL: {e}")

def cancel_subscription(body):
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
