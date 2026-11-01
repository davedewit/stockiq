"""Admin #19 (the owner's yes, 1 Nov 2026): every report already marked deleted gets an expiry of now, so AWS removes it for good
(the table's TTL, free, within about two days). Only rows with deleted = true and no expiry are touched; each update checks that
condition again. DRY_RUN=true counts them and changes nothing."""
import os, time, boto3
t = boto3.Session(profile_name='default', region_name='us-east-1').resource('dynamodb').Table('stockiq-dashboard-analysis-history')
rows, kw = [], {'FilterExpression': 'deleted = :t AND attribute_not_exists(#ttl)', 'ExpressionAttributeNames': {'#ttl': 'ttl', '#ts': 'timestamp'},
                'ExpressionAttributeValues': {':t': True}, 'ProjectionExpression': 'userId, #ts'}
while True:
    r = t.scan(**kw); rows += r['Items']
    if not r.get('LastEvaluatedKey'):
        break
    kw['ExclusiveStartKey'] = r['LastEvaluatedKey']
print(f'deleted reports without an expiry: {len(rows)}')
if os.environ.get('DRY_RUN') == 'true':
    print('(dry run) nothing changed'); raise SystemExit
now = int(time.time())
for it in rows:
    t.update_item(Key={'userId': it['userId'], 'timestamp': it['timestamp']}, UpdateExpression='SET #ttl = :n', ConditionExpression='deleted = :t',
                  ExpressionAttributeNames={'#ttl': 'ttl'}, ExpressionAttributeValues={':n': now, ':t': True})
print(f'expiry set on {len(rows)}: AWS removes them within about two days')
