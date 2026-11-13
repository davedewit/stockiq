#!/usr/bin/env python3
"""Tests for stockiq-payment-handler after Admin #15 (12 Nov 2026). Nothing real is touched: Stripe, the table and the identity
providers' key sets are stand-ins, and the tokens are signed here with a throwaway RSA key.

    python3 check-tools/payments_test.py <payment handler lambda_function.py>

Covers: a forged or mismatched webhook is refused and writes nothing; a replayed 'checkout completed' for a subscription that is no
longer active does nothing; the end or an update of a subscription that is not the member's current one is ignored (a plan change);
the end of the current one marks the member cancelled; cancel_subscription needs proof of who is asking (Cognito, Google, Facebook),
reads the subscription from the asker's own record and ignores one it is sent; the old unsigned 'handle_webhook' action is gone."""
import sys, os, json, time, base64, hashlib, random, importlib.util, types

PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lambda-sync', 'stockiq-payment-handler', 'lambda_function.py')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
fails = []
def check(name, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else '   ' + str(detail)[:300]))
    if not ok: fails.append(name)

# ---- stand-ins
class Obj(dict):
    __getattr__ = dict.get
EVENTS, SUBS, CUSTOMERS, CALLS = {}, {}, {}, []
class Err(Exception): pass
stripe = types.ModuleType('stripe'); stripe.api_key = None
class _Event:
    @staticmethod
    def retrieve(i):
        CALLS.append(('Event.retrieve', i))
        if i not in EVENTS: raise Err('No such event')
        return Obj(EVENTS[i])
class _Sub:
    @staticmethod
    def retrieve(i):
        CALLS.append(('Subscription.retrieve', i)); return Obj(SUBS[i])
    @staticmethod
    def delete(i):
        CALLS.append(('Subscription.delete', i))
class _Cust:
    @staticmethod
    def retrieve(i): return Obj(CUSTOMERS[i])
class _Webhook:
    @staticmethod
    def construct_event(p, s, secret):
        CALLS.append(('construct_event',))
        if s != 'good': raise Err('bad signature')
stripe.Event, stripe.Subscription, stripe.Customer, stripe.Webhook = _Event, _Sub, _Cust, _Webhook
sys.modules['stripe'] = stripe

class Table:
    def __init__(self): self.rows, self.writes = {}, []
    def get_item(self, Key): return {'Item': self.rows[Key['user_date']]} if Key['user_date'] in self.rows else {}
    def put_item(self, Item): self.rows[Item['user_date']] = dict(Item); self.writes.append(('put', Item['user_date']))
    def update_item(self, Key, UpdateExpression, ExpressionAttributeValues):
        self.writes.append(('update', Key['user_date'], ExpressionAttributeValues.get(':status')))
        row = self.rows.setdefault(Key['user_date'], {})
        import re
        for name, val in re.findall(r'(\w+) = (:\w+)', UpdateExpression):     # "SET planType = :plan, ..."
            row[name] = ExpressionAttributeValues[val]

spec = importlib.util.spec_from_file_location('pay', PATH); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
T = Table(); m.users_table = T
INVOKED = []
class FakeLambda:
    def invoke(self, **kw): INVOKED.append(json.loads(json.loads(kw['Payload'])['body'])['action'])
m.boto3 = types.SimpleNamespace(client=lambda *_: FakeLambda(), resource=m.boto3.resource)

# ---- a throwaway RSA key and the tokens signed with it
def prime(bits):
    while True:
        p = random.getrandbits(bits) | (1 << (bits - 1)) | 1
        if all(pow(a, p - 1, p) == 1 for a in (2, 3, 5, 7, 11, 13, 17, 19, 23)) and all(p % q for q in (3, 5, 7, 11, 13)): return p
random.seed(7)
P, Q = prime(520), prime(520); N = P * Q; E = 65537; D = pow(E, -1, (P - 1) * (Q - 1))
other_N = prime(520) * prime(520)
b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b'=').decode()
def sign(claims, kid='k1', alg='RS256', bad=False):
    head = b64(json.dumps({'alg': alg, 'kid': kid}).encode()); body = b64(json.dumps(claims).encode())
    k = (N.bit_length() + 7) // 8; tail = m._SHA256 + hashlib.sha256((head + '.' + body).encode()).digest()
    em = b'\x00\x01' + b'\xff' * (k - len(tail) - 3) + b'\x00' + tail
    sig = pow(int.from_bytes(em, 'big'), D, N).to_bytes(k, 'big')
    if bad: sig = sig[:-1] + bytes([sig[-1] ^ 1])
    return head + '.' + body + '.' + b64(sig)
KEYS = {'keys': [{'kid': 'k1', 'n': b64(N.to_bytes((N.bit_length() + 7) // 8, 'big')), 'e': b64(E.to_bytes(3, 'big'))}]}
FB = {'email': None}
def fetch(url):
    if 'graph.facebook.com' in url:
        if FB['email'] is None: raise Err('401')
        return {'email': FB['email']}
    return KEYS
m._fetch_json = fetch
now = int(time.time())
cog = lambda **kw: dict({'iss': m.COGNITO_ISS, 'aud': m.COGNITO_CLIENT, 'token_use': 'id', 'exp': now + 3000, 'email': 'pay@example.com'}, **kw)
goo = lambda **kw: dict({'iss': 'https://accounts.google.com', 'aud': m.GOOGLE_CLIENT, 'exp': now + 3000, 'email': 'pay@example.com', 'email_verified': True}, **kw)

def call(body, headers=None):
    event = {'body': json.dumps(body), 'headers': headers or {}}
    r = m.lambda_handler(event, None); return r['statusCode'], json.loads(r['body'])

# ---- identity
check('the RSA check accepts a signature made with the key', m.rs256_ok(b'abc', pow(int.from_bytes(m._SHA256.join([b'\x00\x01' + b'\xff' * ((N.bit_length() + 7) // 8 - len(m._SHA256) - 32 - 3) + b'\x00', b'']) + hashlib.sha256(b'abc').digest(), 'big'), D, N).to_bytes((N.bit_length() + 7) // 8, 'big'), KEYS['keys'][0]['n'], KEYS['keys'][0]['e']))
check('a Cognito ID token is accepted and gives the email', m.identity_email({'provider': 'cognito', 'token': sign(cog())}) == 'pay@example.com')
def refused(body, why=''):
    try: m.identity_email(body); return False
    except m.AuthError as e: return why in str(e)
check('a changed signature is refused', refused({'provider': 'cognito', 'token': sign(cog(), bad=True)}, 'signature'))
check('an expired token is refused', refused({'provider': 'cognito', 'token': sign(cog(exp=now - 4000))}, 'expired'))
check("another app's token (wrong audience) is refused", refused({'provider': 'cognito', 'token': sign(cog(aud='someone-else'))}, 'audience'))
check('an access token passed as an ID token is refused', refused({'provider': 'cognito', 'token': sign(cog(token_use='access'))}, 'ID token'))
check('a token from another issuer is refused', refused({'provider': 'cognito', 'token': sign(cog(iss='https://evil.example/pool'))}, 'issuer'))
check('an unknown key id is refused', refused({'provider': 'cognito', 'token': sign(cog(), kid='zzz')}, 'signature'))
check('"alg: none" style tokens are refused', refused({'provider': 'cognito', 'token': sign(cog(), alg='none')}, 'unsupported'))
check('no token, junk, and an unknown provider are refused', refused({'provider': 'cognito'}) and refused({'provider': 'cognito', 'token': 'a.b.c'}) and refused({'provider': 'x', 'token': 'y'}, 'unknown'))
check('a Google credential is accepted', m.identity_email({'provider': 'google', 'token': sign(goo())}) == 'pay@example.com')
check('a Google credential for another client or unverified email is refused', refused({'provider': 'google', 'token': sign(goo(aud='other'))}, 'audience') and refused({'provider': 'google', 'token': sign(goo(email_verified=False))}, 'verified'))
FB['email'] = 'pay@example.com'; check('a Facebook token Facebook accepts gives its email', m.identity_email({'provider': 'facebook', 'token': 'fbtoken'}) == 'pay@example.com')
FB['email'] = None; check('a Facebook token Facebook refuses is refused', refused({'provider': 'facebook', 'token': 'fbtoken'}, 'Facebook'))

# ---- cancel
T.rows['pay@example.com#registration'] = {'user_date': 'pay@example.com#registration', 'stripeSubscriptionId': 'sub_mine', 'subscriptionStatus': 'active', 'planType': 'pro'}
T.rows['victim@example.com#registration'] = {'user_date': 'victim@example.com#registration', 'stripeSubscriptionId': 'sub_victim', 'subscriptionStatus': 'active'}
CALLS.clear()
code, body = call({'action': 'cancel_subscription', 'subscription_id': 'sub_victim'})
check('the old call (a subscription id and nothing else) is refused and cancels nothing', code == 401 and not [c for c in CALLS if c[0] == 'Subscription.delete'], (code, body, CALLS))
code, body = call({'action': 'cancel_subscription', 'provider': 'cognito', 'token': sign(cog()), 'subscription_id': 'sub_victim'})
check("with proof, it cancels the asker's own subscription and ignores the one it was sent", code == 200 and body.get('success') and CALLS == [('Subscription.delete', 'sub_mine')], (code, body, CALLS))
CALLS.clear(); T.rows['nobody@example.com#registration'] = {'user_date': 'nobody@example.com#registration'}
code, body = call({'action': 'cancel_subscription', 'provider': 'cognito', 'token': sign(cog(email='nobody@example.com'))})
check('a member with no subscription gets 404 and nothing is cancelled', code == 404 and not CALLS, (code, body))
code, body = call({'action': 'cancel_subscription', 'provider': 'cognito', 'token': sign(cog(email='Pay@Example.com'))})
check('the address is found whatever its case', code == 200 and CALLS == [('Subscription.delete', 'sub_mine')], (code, body, CALLS))

# ---- the webhook
def stripe_event(i, typ, obj):
    EVENTS[i] = {'id': i, 'type': typ, 'data': {'object': obj}}
def hook(body, headers=None): return call(body, headers or {'stripe-signature': 'good'})
CALLS.clear(); before = list(T.writes)
code, body = hook({'id': 'evt_forged', 'type': 'customer.subscription.deleted', 'data': {'object': {'id': 'sub_mine', 'customer': 'cus_1'}}})
check('a forged event (an id Stripe does not know) is refused and writes nothing', code == 400 and T.writes == before, (code, body, T.writes[len(before):]))
stripe_event('evt_real', 'customer.subscription.deleted', {'id': 'sub_mine', 'customer': 'cus_1'}); CUSTOMERS['cus_1'] = {'email': 'pay@example.com'}
code, body = hook({'id': 'evt_real', 'type': 'invoice.payment_succeeded'})
check('an event whose body says another type than Stripe has is refused', code == 400 and T.writes == before, (code, body))
code, body = call({'action': 'handle_webhook', 'id': 'evt_real', 'type': 'customer.subscription.deleted'})
check("the old unsigned 'handle_webhook' action is gone", code == 400 and 'Invalid action' in body.get('error', ''), (code, body))
T.rows['pay@example.com#registration'].update(subscriptionStatus='active', stripeSubscriptionId='sub_new')
INVOKED.clear()
code, body = hook({'id': 'evt_real', 'type': 'customer.subscription.deleted'})
check("the end of a subscription that is not the member's current one (a plan change) changes nothing", code == 200 and T.rows['pay@example.com#registration']['subscriptionStatus'] == 'active' and not INVOKED, (code, T.rows['pay@example.com#registration'], INVOKED))
stripe_event('evt_cur', 'customer.subscription.deleted', {'id': 'sub_new', 'customer': 'cus_1'})
code, body = hook({'id': 'evt_cur', 'type': 'customer.subscription.deleted'})
check("the end of the member's current subscription marks them cancelled and starts the 30-day deletion", code == 200 and T.rows['pay@example.com#registration']['subscriptionStatus'] == 'cancelled' and INVOKED == ['set_subscription_end_ttl'], (T.rows['pay@example.com#registration'], INVOKED))
T.rows['pay@example.com#registration'].update(subscriptionStatus='active', planType='pro', stripeSubscriptionId='sub_new')
price = {'items': {'data': [{'price': {'id': 'price_1SDOEXGpPmyfuTinTnV688OA'}}]}, 'customer': 'cus_1', 'current_period_end': now + 86400}
stripe_event('evt_upd_old', 'customer.subscription.updated', dict(price, id='sub_old', status='canceled'))
hook({'id': 'evt_upd_old', 'type': 'customer.subscription.updated'})
check("an update of the old subscription does not put the plan back", T.rows['pay@example.com#registration']['planType'] == 'pro', T.rows['pay@example.com#registration'])
stripe_event('evt_upd_new', 'customer.subscription.updated', dict(price, id='sub_new', status='active'))
T.rows['pay@example.com#registration']['user_date'] = 'pay@example.com#registration'
hook({'id': 'evt_upd_new', 'type': 'customer.subscription.updated'})
check("an update of the current subscription changes the plan as before", T.rows['pay@example.com#registration'].get('planType') == 'starter', T.rows['pay@example.com#registration'])

# checkout completed: only a live subscription switches a plan on
session = {'customer': 'cus_1', 'subscription': 'sub_live', 'metadata': {'user_email': 'pay@example.com', 'plan_type': 'elite', 'is_upgrade': 'true', 'old_subscription_id': 'sub_new'}}
SUBS['sub_live'] = {'id': 'sub_live', 'status': 'canceled', 'current_period_end': now + 86400}
stripe_event('evt_co_dead', 'checkout.session.completed', session); CALLS.clear(); before = list(T.writes)
code, body = hook({'id': 'evt_co_dead', 'type': 'checkout.session.completed'})
check('a replayed checkout for a subscription that is no longer active changes nothing and cancels nothing', code == 200 and T.writes == before and not [c for c in CALLS if c[0] == 'Subscription.delete'], (code, T.writes[len(before):], CALLS))
AT_DELETE = []
_orig_delete = _Sub.delete
def _spy_delete(i):
    AT_DELETE.append((i, T.rows['pay@example.com#registration'].get('stripeSubscriptionId'))); _orig_delete(i)
_Sub.delete = staticmethod(_spy_delete)
SUBS['sub_live']['status'] = 'active'; stripe_event('evt_co_live', 'checkout.session.completed', session); CALLS.clear()
code, body = hook({'id': 'evt_co_live', 'type': 'checkout.session.completed'})
rec = T.rows['pay@example.com#registration']
check('a checkout for a live subscription switches the plan on and ends the old subscription', code == 200 and rec.get('planType') == 'elite' and rec.get('stripeSubscriptionId') == 'sub_live' and ('Subscription.delete', 'sub_new') in CALLS, (code, rec, CALLS))
SUBS['sub_same'] = {'id': 'sub_same', 'status': 'active', 'current_period_end': now + 86400}
stripe_event('evt_co_same', 'checkout.session.completed', dict(session, subscription='sub_same', metadata=dict(session['metadata'], old_subscription_id='sub_same'))); CALLS.clear()
hook({'id': 'evt_co_same', 'type': 'checkout.session.completed'})
check('the old subscription ends only after the record names the new one (so its "deleted" event is ignored)', AT_DELETE[:1] == [('sub_new', 'sub_live')], AT_DELETE)
check('a checkout never deletes the subscription it is switching on', ('Subscription.delete', 'sub_same') not in CALLS, CALLS)
CALLS.clear(); hook({'id': 'evt_co_live', 'type': 'checkout.session.completed'}, {'stripe-signature': 'wrong'})
check('a signature that does not check is logged and the event is still taken from Stripe', ('Event.retrieve', 'evt_co_live') in CALLS)
code, body = call({'action': 'create_checkout_session', 'plan_type': 'nonsense', 'user_email': 'x@example.com'})
check('everything else still answers (an invalid plan is the usual error, not a crash of the module)', code == 500 and 'Invalid plan' in body.get('error', ''), (code, body))

print('ALL PASS' if not fails else f'SOME FAILED ({len(fails)})')
sys.exit(1 if fails else 0)
