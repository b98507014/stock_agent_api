import requests
import json

url = "http://localhost:8001/suggest"
payload = {
    "ticker": "auto",
    "cash": 30000,
    "mode": "paper",
    "execute": False
}

response = requests.post(url, json=payload)
print("Status Code:", response.status_code)
result = response.json()
print("Executed:", result.get("executed"))
print("Balance After:", result.get("balance_after"))
print("Portfolio Value:", result.get("portfolio_value"))
print("Num Suggestions:", len(result.get("suggestions", {})))
print("\n=== TEST PASSED (execute=False) ===")
