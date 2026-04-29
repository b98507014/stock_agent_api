import requests
import json

url = "http://localhost:8001/suggest"
payload = {
    "ticker": "auto",
    "cash": 30000,
    "mode": "paper",
    "execute": False
}

print("[TEST] Verify telegram_text field functionality")
print("=" * 60)

# Test 1: Basic response structure
print("\n[TEST 1] Check response structure")
response = requests.post(url, json=payload)
if response.status_code == 200:
    result = response.json()
    required_fields = ['mode', 'cash', 'executed', 'balance_after', 'portfolio_value', 
                      'holdings', 'suggestions', 'current_prices', 'telegram_text']
    
    all_present = all(field in result for field in required_fields)
    if all_present:
        print("[OK] All required fields present")
    else:
        missing = [f for f in required_fields if f not in result]
        print("[ERROR] Missing fields:", missing)
else:
    print("[ERROR] HTTP", response.status_code)

# Test 2: Verify telegram_text is a string
print("\n[TEST 2] Check telegram_text is a string")
if isinstance(result.get('telegram_text'), str):
    print("[OK] telegram_text is a string")
    print("[INFO] Length:", len(result['telegram_text']), "characters")
else:
    print("[ERROR] telegram_text is not a string:", type(result.get('telegram_text')))

# Test 3: Verify telegram_text contains expected content
print("\n[TEST 3] Check telegram_text content")
report = result.get('telegram_text', '')
expected_patterns = [
    'AI Stock Suggestion',
    'Paper Trading Simulation',
    'Current Balance',
    'Current Portfolio Value',
    'Current Holdings',
    'AI Suggestions',
    'After Trading',
    'Daily simulation completed'
]

missing_patterns = [p for p in expected_patterns if p not in report]
if not missing_patterns:
    print("[OK] All expected content patterns found")
else:
    print("[ERROR] Missing patterns:", missing_patterns)

# Test 4: Verify suggestions are in the report
print("\n[TEST 4] Check BUY/SELL/HOLD actions in report")
actions = ['BUY', 'SELL', 'HOLD']
found_actions = [a for a in actions if a in report]
if found_actions:
    print("[OK] Found actions in report:", found_actions)
else:
    print("[ERROR] No BUY/SELL/HOLD actions found in report")

print("\n" + "=" * 60)
print("[OK] All tests completed!")
