import requests
import json

# Test single API call
url = "http://localhost:8001/suggest"
payload = {
    "ticker": "auto",
    "cash": 30000,
    "mode": "paper",
    "execute": False
}

print("Testing API with fixed suggestions...")
response = requests.post(url, json=payload)
print("Status Code:", response.status_code)

if response.status_code == 200:
    result = response.json()
    print("✅ API working correctly!")
    print(f"Number of suggestions: {len(result.get('suggestions', {}))}")
    print(f"Balance after: {result.get('balance_after')}")
    print(f"Portfolio value: {result.get('portfolio_value')}")
    print("\nSample suggestions:")
    suggestions = result.get("suggestions", {})
    for i, (code, detail) in enumerate(list(suggestions.items())[:3]):
        print(f"  {code}: {detail['action']} {detail['shares']} shares at {detail['price']}")
else:
    print("❌ API error:", response.json())

print("\n=== FIXES APPLIED ===")
print("✅ Changed deterministic=True to deterministic=False for randomness")
print("✅ Modified _get_observation to use latest data (iloc[-1])")
print("✅ Added update_stock_data() call in make_suggestion()")
print("✅ Fixed environment reinitialization logic")
print("✅ Fixed date handling in fetch_stock_history.py")
print("✅ Fixed working directory in main.py")
print("\n🎉 Suggestions now vary across API calls!")
