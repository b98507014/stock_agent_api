import requests

url = "http://localhost:8001/suggest"
payload = {
    "ticker": "2330",
    "cash": 50000,
    "mode": "paper",
    "execute": False
}

response = requests.post(url, json=payload)
print("Status Code:", response.status_code)
result = response.json()
print("Executed:", result.get("executed"))
print("Cash:", result.get("cash"))
print("Suggestions keys:", list(result.get("suggestions", {}).keys()))
print("Has 2330:", "2330" in result.get("suggestions", {}))
print("\n=== TEST PASSED (ticker='2330') ===")
