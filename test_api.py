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

print("Testing API with Telegram report...")
response = requests.post(url, json=payload)
print("Status Code:", response.status_code)

if response.status_code == 200:
    result = response.json()
    print("[OK] API working correctly!")
    
    # Check for telegram_text
    if 'telegram_text' in result:
        print("[OK] telegram_text field exists!")
        print("\n=== TELEGRAM REPORT ===")
        print(result['telegram_text'])
    else:
        print("[ERROR] telegram_text field missing!")
        print("Keys:", list(result.keys()))
else:
    print("[ERROR] API error:", response.json())

print("\n[OK] Test completed!")

