import boto3
import json
from datetime import datetime

def lambda_handler(event, context):
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    ses = boto3.client('ses', region_name='us-east-1')
    
    # Get ALL stats (not just last 24 hours)
    now = datetime.utcnow()
    
    try:
        response = dynamodb.scan(TableName='stockiq-ai-chat-stats')
        items = response.get('Items', [])
        
        # Aggregate by user
        user_stats = {}
        total_input_tokens = 0
        total_output_tokens = 0
        
        for item in items:
            user_id = item['userId']['S']
            input_tokens = int(item.get('inputTokens', {}).get('N', 0))
            output_tokens = int(item.get('outputTokens', {}).get('N', 0))
            
            if user_id not in user_stats:
                user_stats[user_id] = {'messages': 0, 'input_tokens': 0, 'output_tokens': 0}
            
            user_stats[user_id]['messages'] += 1
            user_stats[user_id]['input_tokens'] += input_tokens
            user_stats[user_id]['output_tokens'] += output_tokens
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
        
        # Build email
        total_messages = sum(u['messages'] for u in user_stats.values())
        total_tokens = total_input_tokens + total_output_tokens
        input_cost = (total_input_tokens / 1000000) * 0.20
        output_cost = (total_output_tokens / 1000000) * 1.20
        total_cost = input_cost + output_cost
        
        email_body = f"StockIQ AI Chat Usage Report\n"
        email_body += f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        email_body += "=" * 60 + "\n\n"
        
        email_body += "SUMMARY (Last 24 Hours)\n"
        email_body += "-" * 60 + "\n"
        email_body += f"Total Messages: {total_messages:,}\n"
        email_body += f"Input Tokens: {total_input_tokens:,} (${input_cost:.5f})\n"
        email_body += f"Output Tokens: {total_output_tokens:,} (${output_cost:.5f})\n"
        email_body += f"Total Cost: ${total_cost:.5f}\n"
        if total_cost > 0:
            cost_per_message = total_cost / total_messages
            messages_per_cent = 0.01 / cost_per_message if cost_per_message > 0 else 0
            email_body += f"Cost per Message: ${cost_per_message:.5f} (~{messages_per_cent:.1f} msgs/cent)\n"
        email_body += f"Unique Users: {len(user_stats)}\n\n"
        
        if user_stats:
            email_body += "USER BREAKDOWN\n"
            email_body += "-" * 60 + "\n"
            sorted_users = sorted(user_stats.items(), key=lambda x: x[1]['messages'], reverse=True)
            
            for user_id, stats in sorted_users:
                user_type = "Anonymous" if user_id.startswith('anon_') or user_id == 'anonymous' else "Logged In"
                user_input_cost = (stats['input_tokens'] / 1000000) * 0.20
                user_output_cost = (stats['output_tokens'] / 1000000) * 1.20
                user_total_cost = user_input_cost + user_output_cost
                total_user_tokens = stats['input_tokens'] + stats['output_tokens']
                email_body += f"{user_id:<40} {stats['messages']:>3} msgs, {total_user_tokens:>6,} tokens, ${user_total_cost:.5f} ({user_type})\n"
        else:
            email_body += "No AI chat activity in the last 24 hours.\n"
        
        # Add cost projections at bottom
        if total_cost > 0:
            email_body += "\nCOST PROJECTIONS (at current efficiency)\n"
            email_body += "-" * 60 + "\n"
            email_body += f"100 msgs/day:    ${cost_per_message * 100:.2f}/day   ~${cost_per_message * 3000:.2f}/month\n"
            email_body += f"1,000 msgs/day:  ${cost_per_message * 1000:.2f}/day   ~${cost_per_message * 30000:.2f}/month\n"
            email_body += f"10,000 msgs/day: ${cost_per_message * 10000:.2f}/day  ~${cost_per_message * 300000:.2f}/month\n"
        
        # Send email
        ses.send_email(
            Source='usage@stockiq.tech',
            Destination={'ToAddresses': ['openai-usage@stockiq.tech']},
            Message={
                'Subject': {'Data': f'StockIQ: AI Chat Usage - {total_messages} Messages'},
                'Body': {'Text': {'Data': email_body}}
            }
        )
        
        # Delete all items from table (fresh start for next day)
        for item in items:
            dynamodb.delete_item(
                TableName='stockiq-ai-chat-stats',
                Key={'messageId': {'S': item['messageId']['S']}}
            )
        
        print(f"Report sent and table cleared: {total_messages} messages, {total_tokens} tokens, ${total_cost:.5f}")
        return {'statusCode': 200, 'body': json.dumps('Report sent and table cleared')}
    
    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'body': json.dumps(f'Error: {str(e)}')}
