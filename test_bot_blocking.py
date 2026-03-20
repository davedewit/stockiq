#!/usr/bin/env python3
"""Test bot blocking logic locally before deploying"""

import json

# Copy the lambda handler logic
def test_bot_blocking():
    """Test various User-Agent strings"""
    
    test_cases = [
        {
            'name': 'Googlebot',
            'user_agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'should_block': True
        },
        {
            'name': 'Bingbot',
            'user_agent': 'Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)',
            'should_block': True
        },
        {
            'name': 'Real Chrome User',
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'should_block': False
        },
        {
            'name': 'Real Firefox User',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'should_block': False
        },
        {
            'name': 'Yahoo Slurp',
            'user_agent': 'Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)',
            'should_block': True
        },
        {
            'name': 'Empty User-Agent',
            'user_agent': '',
            'should_block': False
        }
    ]
    
    bot_patterns = ['bot', 'crawler', 'spider', 'google', 'bing', 'yahoo', 'baidu']
    
    print("Testing Bot Blocking Logic\n" + "="*50)
    
    all_passed = True
    for test in test_cases:
        user_agent = test['user_agent']
        is_blocked = any(pattern in user_agent.lower() for pattern in bot_patterns)
        expected = test['should_block']
        passed = is_blocked == expected
        
        status = "✅ PASS" if passed else "❌ FAIL"
        action = "BLOCKED" if is_blocked else "ALLOWED"
        
        print(f"\n{status} | {test['name']}")
        print(f"  Action: {action}")
        print(f"  Expected: {'BLOCK' if expected else 'ALLOW'}")
        print(f"  User-Agent: {user_agent[:80]}...")
        
        if not passed:
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("✅ All tests passed! Safe to deploy.")
    else:
        print("❌ Some tests failed. Review logic before deploying.")
    
    return all_passed

if __name__ == '__main__':
    test_bot_blocking()
