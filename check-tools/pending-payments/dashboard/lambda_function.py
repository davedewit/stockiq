import json
import boto3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

# AWS setup
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
history_table = dynamodb.Table('stockiq-dashboard-analysis-history')
CSV_BUCKET = 'stockiq-dashboard-analysis-history'



def lambda_handler(event, context):
    """Handle dashboard requests"""
    try:

        
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': ''
            }
        
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        action = body.get('action')

        
        if action == 'get_history':
            return get_user_history(body.get('userId'), body.get('showDeleted', False), body.get('limit', 50))
        elif action == 'get_analysis':
            return get_analysis_report(body.get('analysisId'), body.get('userId'))
        elif action == 'save_analysis':
            return save_analysis(body)
        elif action == 'delete_analyses':
            return delete_analyses(body)
        elif action == 'download_csv':
            return download_csv(body.get('analysisId'), body.get('userId'))
        elif action == 'set_subscription_end_ttl':
            return set_subscription_end_ttl(body.get('userId'))
        elif action == 'clear_deletion_markers':
            return clear_deletion_markers(body.get('userId'))
        elif action == 'toggle_pin':
            return toggle_pin(body)
        elif action == 'save_notes':
            return save_notes(body)
        elif action == 'save_avg_change':
            return save_avg_change(body)
        else:

            return error_response(400, 'Invalid action')
            
    except Exception as e:
        return error_response(500, f'Internal server error: {str(e)}')

def get_user_history(user_id, show_deleted=False, limit=50):
    """Get user's analysis history and stats with pagination"""
    if not user_id:
        return error_response(400, 'User ID required')
    
    try:
        # Fetch more items than limit to account for pinned sorting
        # Fetch 2x limit to ensure we get enough unpinned items after pinned are extracted
        fetch_limit = limit * 2
        all_items = []
        last_key = None
        
        while len(all_items) < fetch_limit:
            query_params = {
                'KeyConditionExpression': 'userId = :uid',
                'ExpressionAttributeValues': {':uid': user_id},
                'ScanIndexForward': False,
                'Limit': min(fetch_limit - len(all_items), 100)
            }
            if last_key:
                query_params['ExclusiveStartKey'] = last_key
            
            response = history_table.query(**query_params)
            items = response.get('Items', [])
            
            # Filter based on showDeleted
            for item in items:
                if show_deleted or not item.get('deleted', False):
                    all_items.append(item)
            
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
        
        # Sort: pinned first, then by timestamp desc
        pinned = [item for item in all_items if item.get('pinned', False)]
        unpinned = [item for item in all_items if not item.get('pinned', False)]
        
        # Combine and limit to 50
        history = (pinned + unpinned)[:limit]
        
        # Calculate stats from fetched history only
        stats = calculate_user_stats(history)
        
        # Convert Decimal to float for JSON serialization
        history = convert_decimals(history)
        stats = convert_decimals(stats)
        
        return success_response({
            'history': history,
            'stats': stats
        })
        
    except Exception as e:
        return error_response(500, 'Failed to retrieve history')

def get_analysis_report(analysis_id, user_id=None):
    """Get specific analysis report"""
    if not analysis_id or not user_id:
        return error_response(400, 'Analysis ID and User ID required')
    
    try:
        # Check DynamoDB first
        last_evaluated_key = None
        
        while True:
            query_params = {
                'KeyConditionExpression': 'userId = :uid',
                'ExpressionAttributeValues': {':uid': user_id}
            }
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key
                
            response = history_table.query(**query_params)
            items = response.get('Items', [])
            
            for item in items:
                if item.get('analysisId') == analysis_id:
                    # If report is in S3, fetch it
                    if 'reportS3Key' in item and not item.get('report'):
                        try:
                            s3_key = item['reportS3Key']
                            s3_response = s3.get_object(Bucket='stockiq-dashboard-analysis-history', Key=s3_key)
                            item['report'] = s3_response['Body'].read().decode('utf-8')
                            print(f"📦 Fetched report from S3: {s3_key}")
                        except Exception as e:
                            print(f"⚠️ Failed to fetch report from S3: {str(e)}")
                            item['report'] = "Report not available. Please re-run the analysis."
                    return success_response({'analysis': convert_decimals(item)})
            
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        
        # Check S3 for 1-1 custom analysis
        s3_analysis = get_s3_analysis_by_id(user_id, analysis_id)
        if s3_analysis:
            return success_response({'analysis': s3_analysis})
        
        return error_response(404, 'Analysis not found')
        
    except Exception as e:
        return error_response(500, f'Failed to retrieve analysis: {str(e)}')

def delete_analyses(data):
    """Delete selected analyses"""
    user_id = data.get('userId')
    analysis_ids = data.get('analysisIds', [])
    
    if not user_id:
        return error_response(400, 'User ID required')
    
    if not analysis_ids:
        return error_response(400, 'Analysis IDs required')
    
    try:
        deleted_count = 0
        failed_count = 0
        chart_bucket = 'stockiq-option-1-1-custom-analysis'
        
        print(f"Delete request: userId={user_id}, analysisIds={analysis_ids}")
        
        # Get all items for the user with pagination
        user_items = []
        last_key = None
        while True:
            query_params = {
                'KeyConditionExpression': 'userId = :uid',
                'ExpressionAttributeValues': {':uid': user_id}
            }
            if last_key:
                query_params['ExclusiveStartKey'] = last_key
            
            response = history_table.query(**query_params)
            user_items.extend(response.get('Items', []))
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
        
        print(f"Found {len(user_items)} total items for user")
        
        for analysis_id in analysis_ids:
            try:
                # Find the item with matching analysisId
                item = None
                for user_item in user_items:
                    if user_item.get('analysisId') == analysis_id:
                        item = user_item
                        break
                
                if not item:
                    print(f"Analysis {analysis_id} not found for user {user_id}")
                    failed_count += 1
                    continue
                
                print(f"Deleting analysis {analysis_id}: symbol={item.get('symbol')}, timestamp={item.get('timestamp')}")
                
                # Delete S3 CSV file if it exists
                if 'csvS3Key' in item:
                    try:
                        s3.delete_object(Bucket=CSV_BUCKET, Key=item['csvS3Key'])
                        print(f"Deleted CSV: {item['csvS3Key']}")
                    except Exception as e:
                        print(f"Failed to delete CSV: {str(e)}")
                
                # Delete S3 charts for this analysis
                try:
                    chart_prefix = f"charts/{user_id}/{analysis_id}/"
                    paginator = s3.get_paginator('list_objects_v2')
                    chart_count = 0
                    for page in paginator.paginate(Bucket=chart_bucket, Prefix=chart_prefix):
                        for obj in page.get('Contents', []):
                            s3.delete_object(Bucket=chart_bucket, Key=obj['Key'])
                            chart_count += 1
                    if chart_count > 0:
                        print(f"Deleted {chart_count} charts for {analysis_id}")
                except Exception as e:
                    print(f"Failed to delete charts for {analysis_id}: {str(e)}")
                
                # Soft delete in DynamoDB - mark as deleted
                try:
                    history_table.update_item(
                        Key={
                            'userId': user_id,
                            'timestamp': item['timestamp']
                        },
                        UpdateExpression='SET deleted = :deleted',
                        ExpressionAttributeValues={':deleted': True}
                    )
                    print(f"Marked as deleted in DynamoDB: {analysis_id}")
                    deleted_count += 1
                except Exception as e:
                    print(f"Failed to update DynamoDB for {analysis_id}: {str(e)}")
                    failed_count += 1
                    
            except Exception as e:
                print(f"Error deleting {analysis_id}: {str(e)}")
                failed_count += 1
        
        message = f'Successfully deleted {deleted_count} analyses'
        if failed_count > 0:
            message += f', {failed_count} failed'
        
        return success_response({
            'deletedCount': deleted_count,
            'failedCount': failed_count,
            'message': message
        })
        
    except Exception as e:
        print(f"Delete analyses error: {str(e)}")
        import traceback
        traceback.print_exc()
        return error_response(500, f'Failed to delete analyses: {str(e)}')

def save_analysis(data):
    """Save new analysis to history"""
    user_id = data.get('userId')
    symbol = data.get('symbol')
    company_name = data.get('companyName', '')
    report = data.get('report', '')
    unique_symbols_analyzed = data.get('uniqueSymbolsAnalyzed', 1)
    csv_data = data.get('csvData', '')
    is_read = data.get('isRead', True)  # Default to True for manual analyses
    
    if not user_id or not symbol:
        return error_response(400, 'User ID and symbol required')
    
    try:
        analysis_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Extract and store charts in S3, replace with S3 URLs in report
        report_with_s3_charts = extract_and_store_charts(report, user_id, analysis_id)
        
        item = {
            'userId': user_id,
            'analysisId': analysis_id,
            'symbol': symbol.upper(),
            'companyName': company_name,
            'report': report_with_s3_charts,
            'timestamp': timestamp,
            'uniqueSymbolsAnalyzed': unique_symbols_analyzed,
            'isRead': is_read
        }
        
        # Store CSV in S3 if provided
        if csv_data:
            try:
                s3_key = f"csv/{user_id}/{analysis_id}.csv"
                s3.put_object(
                    Bucket=CSV_BUCKET,
                    Key=s3_key,
                    Body=csv_data.encode('utf-8'),
                    ContentType='text/csv'
                )
                item['csvS3Key'] = s3_key
            except Exception:
                pass
        
        history_table.put_item(Item=item)
        
        return success_response({
            'analysisId': analysis_id,
            'message': 'Analysis saved successfully'
        })
        
    except Exception as e:
        return error_response(500, 'Failed to save analysis')

def download_csv(analysis_id, user_id=None):
    """Download CSV file from S3"""
    if not analysis_id or not user_id:
        return error_response(400, 'Analysis ID and User ID required')
    
    try:
        last_evaluated_key = None
        
        while True:
            query_params = {
                'KeyConditionExpression': 'userId = :uid',
                'ExpressionAttributeValues': {':uid': user_id}
            }
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key
                
            response = history_table.query(**query_params)
            items = response.get('Items', [])
            
            for item in items:
                if item.get('analysisId') == analysis_id:
                    s3_key = item.get('csvS3Key')
                    if not s3_key:
                        return error_response(404, 'CSV file not available for this analysis')
                    
                    # Return S3 URL - let CSV proxy Lambda handle subscription check and truncation
                    s3_url = f's3://{CSV_BUCKET}/{s3_key}'
                    
                    return success_response({
                        's3Url': s3_url,
                        'symbol': item.get('symbol', ''),
                        'timestamp': item.get('timestamp', '')
                    })
            
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        
        return error_response(404, 'Analysis not found')
        
    except Exception as e:
        return error_response(500, f'Failed to download CSV: {str(e)}')

def filter_history_by_period(history):
    """Filter history based on trial/subscription period"""
    if not history:
        return []
    
    now = datetime.now(timezone.utc)
    
    # For trial users: show only last 7 days
    # For paid users: show current billing cycle (assume monthly)
    seven_days_ago = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Filter to show either trial period (7 days) or current month
    trial_cutoff = seven_days_ago
    subscription_cutoff = month_start
    
    # Use the more recent cutoff (trial is more restrictive)
    cutoff_date = max(trial_cutoff, subscription_cutoff)
    
    filtered = []
    for item in history:
        item_date = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
        if item_date >= cutoff_date:
            filtered.append(item)
    
    return filtered

def calculate_user_stats(history):
    """Calculate user statistics from history"""
    if not history:
        return {
            'totalAnalyses': 0,
            'uniqueSymbols': 0,
            'today': 0,
            'avgPerDay': '0.0'
        }
    
    # Total analyses
    total_analyses = len(history)
    
    # Total unique symbols analyzed (sum of uniqueSymbolsAnalyzed field)
    unique_symbols = sum(int(item.get('uniqueSymbolsAnalyzed', 1)) for item in history)
    
    # Today's analyses
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    today_count = 0
    for item in history:
        item_date = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
        if item_date.tzinfo is None:
            item_date = item_date.replace(tzinfo=timezone.utc)
        if item_date >= today_start:
            today_count += 1
    
    # Average analyses per day (since first analysis)
    if history:
        first_date = None
        for item in history:
            item_date = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
            if item_date.tzinfo is None:
                item_date = item_date.replace(tzinfo=timezone.utc)
            if first_date is None or item_date < first_date:
                first_date = item_date
        
        days_since_first = max(1, (now - first_date).days + 1)
        avg_per_day = total_analyses / days_since_first
    else:
        avg_per_day = 0.0
    
    today = today_count
    
    return {
        'totalAnalyses': total_analyses,
        'uniqueSymbols': unique_symbols,
        'today': today,
        'avgPerDay': f'{avg_per_day:.1f}'
    }

def clear_deletion_markers(user_id):
    """Remove TTL and S3 tags when user subscribes"""
    if not user_id:
        return error_response(400, 'User ID required')
    
    try:
        # Get all analyses for the user with pagination
        items = []
        last_key = None
        
        while True:
            query_params = {
                'KeyConditionExpression': 'userId = :uid',
                'ExpressionAttributeValues': {':uid': user_id}
            }
            if last_key:
                query_params['ExclusiveStartKey'] = last_key
            
            response = history_table.query(**query_params)
            items.extend(response.get('Items', []))
            
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
        
        updated_count = 0
        chart_bucket = 'stockiq-option-1-1-custom-analysis'
        
        for item in items:
            # Only process items that have TTL set
            if 'ttl' in item:
                analysis_id = item.get('analysisId')
                
                # Remove tag from S3 CSV file
                if 'csvS3Key' in item:
                    try:
                        s3.delete_object_tagging(
                            Bucket=CSV_BUCKET,
                            Key=item['csvS3Key']
                        )
                    except Exception as e:
                        print(f"Failed to remove CSV tag {item['csvS3Key']}: {e}")
                
                # Remove tags from charts in stockiq-option-1-1-custom-analysis bucket
                if analysis_id:
                    try:
                        chart_prefix = f"charts/{user_id}/{analysis_id}/"
                        paginator = s3.get_paginator('list_objects_v2')
                        for page in paginator.paginate(Bucket=chart_bucket, Prefix=chart_prefix):
                            for obj in page.get('Contents', []):
                                try:
                                    s3.delete_object_tagging(
                                        Bucket=chart_bucket,
                                        Key=obj['Key']
                                    )
                                except Exception as e:
                                    print(f"Failed to remove chart tag {obj['Key']}: {e}")
                    except Exception:
                        pass
                
                # Remove tags from charts in stockiq-dashboard-analysis-history bucket
                if analysis_id:
                    try:
                        chart_prefix = f"charts/{user_id}/{analysis_id}/"
                        paginator = s3.get_paginator('list_objects_v2')
                        for page in paginator.paginate(Bucket=CSV_BUCKET, Prefix=chart_prefix):
                            for obj in page.get('Contents', []):
                                try:
                                    s3.delete_object_tagging(
                                        Bucket=CSV_BUCKET,
                                        Key=obj['Key']
                                    )
                                except Exception as e:
                                    print(f"Failed to remove chart tag {obj['Key']}: {e}")
                    except Exception:
                        pass
                
                # Remove TTL and deleted flag from DynamoDB
                history_table.update_item(
                    Key={
                        'userId': user_id,
                        'timestamp': item['timestamp']
                    },
                    UpdateExpression='REMOVE #ttl, deleted',
                    ExpressionAttributeNames={'#ttl': 'ttl'}
                )
                updated_count += 1
        
        return success_response({
            'updatedCount': updated_count,
            'message': f'Cleared deletion markers for {updated_count} analyses'
        })
        
    except Exception as e:
        return error_response(500, 'Failed to clear deletion markers')

def set_subscription_end_ttl(user_id):
    """Set 30-day TTL on all analyses when subscription ends"""
    if not user_id:
        return error_response(400, 'User ID required')
    
    try:
        # Get all analyses for the user with pagination
        items = []
        last_key = None
        
        while True:
            query_params = {
                'KeyConditionExpression': 'userId = :uid',
                'ExpressionAttributeValues': {':uid': user_id}
            }
            if last_key:
                query_params['ExclusiveStartKey'] = last_key
            
            response = history_table.query(**query_params)
            items.extend(response.get('Items', []))
            
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
        
        # Calculate and validate TTL
        now = datetime.now(timezone.utc)
        ttl_timestamp = int((now + timedelta(days=30)).timestamp())
        now_timestamp = int(now.timestamp())
        
        if ttl_timestamp <= now_timestamp:
            return error_response(500, 'Invalid TTL calculation')
        
        updated_count = 0
        chart_bucket = 'stockiq-option-1-1-custom-analysis'
        
        for item in items:
            # Only set TTL if not already set (to avoid overwriting existing TTL)
            if 'ttl' not in item:
                analysis_id = item.get('analysisId')
                
                # Tag S3 CSV file for lifecycle cleanup
                if 'csvS3Key' in item:
                    try:
                        s3.put_object_tagging(
                            Bucket=CSV_BUCKET,
                            Key=item['csvS3Key'],
                            Tagging={'TagSet': [{'Key': 'AutoDelete', 'Value': 'true'}]}
                        )
                    except Exception as e:
                        print(f"Failed to tag CSV {item['csvS3Key']}: {e}")
                
                # Tag all charts in stockiq-option-1-1-custom-analysis bucket
                if analysis_id:
                    try:
                        chart_prefix = f"charts/{user_id}/{analysis_id}/"
                        paginator = s3.get_paginator('list_objects_v2')
                        for page in paginator.paginate(Bucket=chart_bucket, Prefix=chart_prefix):
                            for obj in page.get('Contents', []):
                                try:
                                    s3.put_object_tagging(
                                        Bucket=chart_bucket,
                                        Key=obj['Key'],
                                        Tagging={'TagSet': [{'Key': 'AutoDelete', 'Value': 'true'}]}
                                    )
                                except Exception as e:
                                    print(f"Failed to tag chart {obj['Key']}: {e}")
                    except Exception:
                        pass
                
                # Tag all charts in stockiq-dashboard-analysis-history bucket
                if analysis_id:
                    try:
                        chart_prefix = f"charts/{user_id}/{analysis_id}/"
                        paginator = s3.get_paginator('list_objects_v2')
                        for page in paginator.paginate(Bucket=CSV_BUCKET, Prefix=chart_prefix):
                            for obj in page.get('Contents', []):
                                try:
                                    s3.put_object_tagging(
                                        Bucket=CSV_BUCKET,
                                        Key=obj['Key'],
                                        Tagging={'TagSet': [{'Key': 'AutoDelete', 'Value': 'true'}]}
                                    )
                                except Exception as e:
                                    print(f"Failed to tag chart {obj['Key']}: {e}")
                    except Exception:
                        pass
                
                history_table.update_item(
                    Key={
                        'userId': user_id,
                        'timestamp': item['timestamp']
                    },
                    UpdateExpression='SET #ttl = :ttl, deleted = :deleted',
                    ExpressionAttributeNames={'#ttl': 'ttl'},
                    ExpressionAttributeValues={':ttl': ttl_timestamp, ':deleted': True}
                )
                updated_count += 1
        
        return success_response({
            'updatedCount': updated_count,
            'message': f'Set 30-day TTL for {updated_count} analyses with S3 lifecycle cleanup'
        })
        
    except Exception as e:
        return error_response(500, 'Failed to set subscription end TTL')

def extract_and_store_charts(report, user_id, analysis_id):
    """Extract base64 chart images from report and store in S3"""
    import re
    import base64
    
    # Find all base64 image data URLs in the report
    pattern = r'<img src="(data:image/[^;]+;base64,[^"]+)"'
    matches = re.findall(pattern, report)
    
    if not matches:
        return report
    
    modified_report = report
    chart_bucket = 'stockiq-option-1-1-custom-analysis'
    
    for idx, data_url in enumerate(matches):
        try:
            # Extract the base64 data
            if ';base64,' in data_url:
                header, base64_data = data_url.split(';base64,', 1)
                image_type = header.split('/')[-1]  # e.g., 'png', 'svg+xml'
                
                # Decode base64 to binary
                image_binary = base64.b64decode(base64_data)
                
                # Store in S3 as binary
                s3_key = f"charts/{user_id}/{analysis_id}/chart_{idx}.{image_type.replace('+xml', '')}"
                s3.put_object(
                    Bucket=chart_bucket,
                    Key=s3_key,
                    Body=image_binary,
                    ContentType=f'image/{image_type}'
                )
                
                # Generate S3 URL
                s3_url = f"https://{chart_bucket}.s3.amazonaws.com/{s3_key}"
                
                # Replace in report
                modified_report = modified_report.replace(data_url, s3_url)
        except Exception as e:
            print(f"Failed to store chart {idx}: {str(e)}")
            continue
    
    return modified_report

def get_s3_analysis_history(user_id):
    """Get analysis history from S3 for 1-1 custom analysis"""
    s3_bucket = 'stockiq-option-1-1-custom-analysis'
    prefix = f"users/{user_id}/analyses/"
    items = []
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=s3_bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                try:
                    response = s3.get_object(Bucket=s3_bucket, Key=obj['Key'])
                    data = json.loads(response['Body'].read().decode('utf-8'))
                    items.append(data)
                except Exception:
                    continue
    except Exception:
        pass
    
    return items

def get_s3_analysis_by_id(user_id, analysis_id):
    """Get specific analysis from S3 by ID"""
    s3_bucket = 'stockiq-option-1-1-custom-analysis'
    prefix = f"users/{user_id}/analyses/"
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=s3_bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                if analysis_id in obj['Key']:
                    response = s3.get_object(Bucket=s3_bucket, Key=obj['Key'])
                    return json.loads(response['Body'].read().decode('utf-8'))
    except Exception:
        pass
    
    return None

def convert_decimals(obj):
    """Convert DynamoDB Decimal objects to float for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj

def success_response(data):
    """Return success response"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps(data)
    }

def toggle_pin(data):
    """Toggle pin status for an analysis"""
    user_id = data.get('userId')
    analysis_id = data.get('analysisId')
    is_pinned = data.get('isPinned', False)
    
    if not user_id or not analysis_id:
        return error_response(400, 'User ID and Analysis ID required')
    
    try:
        # Get all items for the user with pagination
        last_key = None
        target_item = None
        
        while True:
            query_params = {
                'KeyConditionExpression': 'userId = :uid',
                'ExpressionAttributeValues': {':uid': user_id}
            }
            if last_key:
                query_params['ExclusiveStartKey'] = last_key
            
            response = history_table.query(**query_params)
            items = response.get('Items', [])
            
            for item in items:
                if item.get('analysisId') == analysis_id:
                    target_item = item
                    break
            
            if target_item:
                break
            
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
        
        if not target_item:
            return error_response(404, 'Analysis not found')
        
        # Update pin status
        history_table.update_item(
            Key={
                'userId': user_id,
                'timestamp': target_item['timestamp']
            },
            UpdateExpression='SET pinned = :pinned',
            ExpressionAttributeValues={':pinned': is_pinned}
        )
        
        return success_response({
            'analysisId': analysis_id,
            'isPinned': is_pinned,
            'message': 'Pin status updated successfully'
        })
        
    except Exception as e:
        print(f"Error toggling pin: {str(e)}")
        return error_response(500, f'Failed to toggle pin: {str(e)}')

def save_notes(data):
    """Save notes for an analysis"""
    user_id = data.get('userId')
    analysis_id = data.get('analysisId')
    notes = data.get('notes', '')
    
    if not user_id or not analysis_id:
        return error_response(400, 'User ID and Analysis ID required')
    
    try:
        # Find the item with pagination
        last_key = None
        target_item = None
        
        while True:
            query_params = {
                'KeyConditionExpression': 'userId = :uid',
                'ExpressionAttributeValues': {':uid': user_id}
            }
            if last_key:
                query_params['ExclusiveStartKey'] = last_key
            
            response = history_table.query(**query_params)
            items = response.get('Items', [])
            
            for item in items:
                if item.get('analysisId') == analysis_id:
                    target_item = item
                    break
            
            if target_item:
                break
            
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
        
        if not target_item:
            return error_response(404, 'Analysis not found')
        
        # Update notes
        history_table.update_item(
            Key={
                'userId': user_id,
                'timestamp': target_item['timestamp']
            },
            UpdateExpression='SET notes = :notes',
            ExpressionAttributeValues={':notes': notes}
        )
        
        return success_response({'message': 'Notes saved'})
        
    except Exception as e:
        return error_response(500, f'Failed to save notes: {str(e)}')

def save_avg_change(data):
    """Save average change percentage for a screener"""
    user_id = data.get('userId')
    analysis_id = data.get('analysisId')
    avg_change = data.get('avgChange')
    
    if not user_id or not analysis_id or avg_change is None:
        return error_response(400, 'User ID, Analysis ID, and avgChange required')
    
    try:
        # Find the item with pagination
        last_key = None
        target_item = None
        
        while True:
            query_params = {
                'KeyConditionExpression': 'userId = :uid',
                'ExpressionAttributeValues': {':uid': user_id}
            }
            if last_key:
                query_params['ExclusiveStartKey'] = last_key
            
            response = history_table.query(**query_params)
            items = response.get('Items', [])
            
            for item in items:
                if item.get('analysisId') == analysis_id:
                    target_item = item
                    break
            
            if target_item:
                break
            
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
        
        if not target_item:
            return error_response(404, 'Analysis not found')
        
        # Update avgChange
        history_table.update_item(
            Key={
                'userId': user_id,
                'timestamp': target_item['timestamp']
            },
            UpdateExpression='SET avgChange = :avgChange',
            ExpressionAttributeValues={':avgChange': Decimal(str(avg_change))}
        )
        
        return success_response({'message': 'Average change saved'})
        
    except Exception as e:
        return error_response(500, f'Failed to save average change: {str(e)}')



def error_response(status_code, message):
    """Return error response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps({'error': message})
    }