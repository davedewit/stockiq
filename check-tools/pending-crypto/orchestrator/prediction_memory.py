import json
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal

class PredictionMemory:
    """Track predictions vs actual performance to identify true predictive signals
    
    Coinspot-inspired prediction tracking system for StockIQ Option 7.1
    """
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table_name = 'stockiq-coinspot-predictions'
        
        # Test table access
        try:
            table = self.dynamodb.Table(self.table_name)
            table.load()
            print(f"✅ DynamoDB table '{self.table_name}' accessible")
        except Exception as e:
            print(f"❌ DynamoDB table access failed: {e}")
        
    def store_prediction(self, symbol: str, score: float, price: float, recommendation: str, 
                        prediction_time: str, timeframe: str = "1-3 months"):
        """Store a prediction when stock is identified as top pick"""
        try:
            table = self.dynamodb.Table(self.table_name)
            
            # Create unique prediction record with milliseconds
            import time
            prediction_id = f"{symbol}_{prediction_time}_{int(time.time()*1000)}"
            
            # Convert to Decimal for DynamoDB
            price = Decimal(str(price)) if price else Decimal('0')
            score = Decimal(str(score)) if score else Decimal('0')
            
            item = {
                'prediction_id': prediction_id,
                'symbol': str(symbol),
                'prediction_time': str(prediction_time),
                'prediction_price': price,
                'prediction_score': score,
                'recommendation': str(recommendation),
                'timeframe': str(timeframe),
                'status': 'ACTIVE',
                'created_at': datetime.now().isoformat(),
                'ttl': int((datetime.now() + timedelta(hours=25)).timestamp())  # Auto-expire after 25 hours
            }
            
            table.put_item(Item=item)
            return True
            
        except Exception as e:
            print(f"Error storing prediction: {e}")
            return False
    
    def check_prediction_history(self, symbol: str, current_price: float, 
                               lookback_hours: int = 24, threshold_hours: float = 0.1) -> Dict:
        """Check if this stock was predicted before recent price moves"""
        try:
            table = self.dynamodb.Table(self.table_name)
            
            # Look for predictions in the last X hours
            cutoff_time = (datetime.now() - timedelta(hours=lookback_hours)).isoformat()
            
            response = table.scan(
                FilterExpression='symbol = :symbol AND prediction_time > :cutoff',
                ExpressionAttributeValues={
                    ':symbol': symbol,
                    ':cutoff': cutoff_time
                }
            )
            
            predictions = response.get('Items', [])
            
            if not predictions:
                return {
                    'was_predicted': False,
                    'prediction_type': 'REACTIVE',
                    'message': f"🔴 REACTIVE: {symbol} appears in top 10 AFTER price move"
                }
            
            # Find the most recent prediction
            latest_prediction = max(predictions, key=lambda x: x['prediction_time'])
            
            # Calculate performance since prediction
            prediction_price = float(latest_prediction['prediction_price'])
            price_change = ((current_price - prediction_price) / prediction_price) * 100
            
            # Determine if this was truly predictive
            hours_since_prediction = (datetime.now() - datetime.fromisoformat(latest_prediction['prediction_time'])).total_seconds() / 3600
            
            if hours_since_prediction >= threshold_hours:  # Configurable lead time threshold
                return {
                    'was_predicted': True,
                    'prediction_type': 'PREDICTIVE',
                    'prediction_time': latest_prediction['prediction_time'],
                    'prediction_price': prediction_price,
                    'current_price': current_price,
                    'price_change_since_prediction': price_change,
                    'hours_since_prediction': round(hours_since_prediction, 1),
                    'original_score': latest_prediction['prediction_score'],
                    'original_recommendation': latest_prediction['recommendation'],
                    'message': f"🟢 PREDICTIVE: {symbol} was identified {hours_since_prediction:.1f}h ago at ${prediction_price:.2f} (now +{price_change:+.1f}%)"
                }
            else:
                return {
                    'was_predicted': True,
                    'prediction_type': 'RECENT',
                    'message': f"🟡 RECENT: {symbol} was identified {hours_since_prediction:.1f}h ago (too recent to be predictive)"
                }
                
        except Exception as e:
            print(f"Error checking prediction history: {e}")
            return {
                'was_predicted': False,
                'prediction_type': 'RECENT',
                'message': f"🟡 RECENT: {symbol} (first analysis)"
            }
    
    def get_prediction_performance(self, days_back: int = 7) -> List[Dict]:
        """Get performance of all predictions in the last N days"""
        try:
            table = self.dynamodb.Table(self.table_name)
            
            cutoff_time = (datetime.now() - timedelta(days=days_back)).isoformat()
            
            response = table.scan(
                FilterExpression='prediction_time > :cutoff',
                ExpressionAttributeValues={
                    ':cutoff': cutoff_time
                }
            )
            
            predictions = response.get('Items', [])
            
            # Add performance metrics to each prediction
            for pred in predictions:
                pred['age_hours'] = (datetime.now() - datetime.fromisoformat(pred['prediction_time'])).total_seconds() / 3600
                # Note: Would need current price to calculate actual performance
            
            return sorted(predictions, key=lambda x: x['prediction_time'], reverse=True)
            
        except Exception as e:
            print(f"Error getting prediction performance: {e}")
            return []

def set_prediction_status_and_queue_storage(all_coins: List[Dict], threshold_hours: float = 0.1, enable_predictions: bool = True) -> List[Dict]:
    """Check all coins for prediction history, store new predictions after display"""
    memory = PredictionMemory()
    
    print(f"Processing {len(all_coins)} coins for prediction memory")
    
    if enable_predictions:
        # Check ALL coins for prediction history (so coins can return as PREDICTIVE)
        for coin in all_coins:
            try:
                prediction_info = memory.check_prediction_history(coin['symbol'], coin['price'], lookback_hours=24, threshold_hours=threshold_hours)
                coin['prediction_status'] = prediction_info['prediction_type']
                coin['prediction_message'] = prediction_info['message']
                coin['is_predictive'] = prediction_info.get('was_predicted', False) and prediction_info['prediction_type'] == 'PREDICTIVE'
            except:
                coin['prediction_status'] = 'RECENT'
                coin['prediction_message'] = f"🟡 RECENT: {coin['symbol']} (first analysis)"
                coin['is_predictive'] = False
    else:
        # Prediction analysis disabled - all coins RECENT (fastest)
        for coin in all_coins:
            coin['prediction_status'] = 'RECENT'
            coin['prediction_message'] = f"🟡 RECENT: {coin['symbol']} (predictions disabled)"
            coin['is_predictive'] = False
    
    return all_coins

def store_new_predictions(all_coins: List[Dict]) -> None:
    """Store predictions for ALL coins with score > 0 (called after results displayed)"""
    memory = PredictionMemory()
    
    # Store ALL coins with non-zero scores, not just top 10
    coins_with_scores = [coin for coin in all_coins if coin.get('score', 0) > 0]
    print(f"📊 Storing predictions for {len(coins_with_scores)} coins with scores > 0")
    
    for coin in coins_with_scores:
        try:
            memory.store_prediction(
                symbol=coin.get('symbol', 'UNKNOWN'),
                score=coin.get('score', 0),
                price=coin.get('price', 0),
                recommendation=coin.get('recommendation', 'HOLD'),
                prediction_time=datetime.now().isoformat(),
                timeframe=coin.get('timeframe', '1-3 months')
            )
        except:
            pass

# Usage example for Lambda function
def lambda_handler(event, context):
    """Enhanced Option 7.1 with prediction memory"""
    
    # ... existing Option 7.1 logic to get top 10 stocks ...
    
    # Enhance results with prediction memory
    enhanced_top_10 = enhance_top_10_with_memory(top_10_results)
    
    # Format response with prediction context
    formatted_results = []
    for stock in enhanced_top_10:
        prediction_ctx = stock['prediction_context']
        
        result = {
            **stock,  # All existing stock data
            'prediction_status': prediction_ctx['prediction_type'],
            'prediction_message': prediction_ctx['message'],
            'is_predictive': prediction_ctx.get('was_predicted', False) and prediction_ctx['prediction_type'] == 'PREDICTIVE'
        }
        
        # Add detailed prediction info if available
        if prediction_ctx.get('was_predicted') and prediction_ctx['prediction_type'] == 'PREDICTIVE':
            result.update({
                'predicted_at': prediction_ctx['prediction_time'],
                'predicted_price': prediction_ctx['prediction_price'],
                'prediction_performance': prediction_ctx['price_change_since_prediction'],
                'prediction_lead_time_hours': prediction_ctx['hours_since_prediction']
            })
        
        formatted_results.append(result)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'results': formatted_results,
            'predictive_count': len([r for r in formatted_results if r.get('is_predictive', False)]),
            'reactive_count': len([r for r in formatted_results if r.get('prediction_status') == 'REACTIVE']),
            'timestamp': datetime.now().isoformat()
        })
    }