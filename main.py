from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Union, List
import requests

from ai_stock_suggestion import make_suggestion

app = FastAPI(title="Stock RL Suggestion API")


class SuggestRequest(BaseModel):
	ticker: Optional[Union[str, List[str]]] = None
	cash: Optional[float] = Field(default=30000, gt=0)
	mode: str = Field(default="paper")
	execute: bool = Field(default=True)
	# update_data: bool = Field(default=False)  # Removed update_data control

	@validator("mode")
	def validate_mode(cls, value):
		if value != "paper":
			raise ValueError("mode must be 'paper'")
		return value


@app.get("/health")
async def health():
	return {"status": "ok"}


@app.get("/test-network")
async def test_network():
	"""Test basic network connectivity"""
	try:
		# Test DNS resolution
		import socket
		ip = socket.gethostbyname('www.twse.com.tw')
		
		# Test basic HTTP connection
		response = requests.get("https://www.google.com", timeout=5)
		
		return {
			"status": "ok",
			"twse_ip": ip,
			"google_status": response.status_code
		}
	except Exception as e:
		return {
			"status": "failed",
			"error": str(e)
		}


@app.post("/suggest")
async def suggest(request: SuggestRequest):
	try:
		result = make_suggestion(
			ticker=request.ticker,
			cash=request.cash,
			mode=request.mode,
			execute=request.execute
			# update_data=request.update_data  # Removed update_data parameter
		)
		return result
	except ValueError as exc:
		raise HTTPException(
			status_code=400,
			detail={"error": "Invalid input", "message": str(exc)}
		)
	except FileNotFoundError as exc:
		raise HTTPException(
			status_code=500,
			detail={"error": "Missing required file", "message": str(exc)}
		)
	except Exception as exc:
		return JSONResponse(
			status_code=500,
			content={"error": "Internal server error", "message": str(exc)},
		)


@app.get("/fetch-simple")
async def fetch_simple():
	"""Simple test endpoint to fetch TWSE API data for stock 2330"""
	try:
		url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date=20240101&stockNo=2330"
		headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
			"Accept": "application/json, text/plain, */*",
			"Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
			"Referer": "https://www.twse.com.tw/",
			"Connection": "keep-alive"
		}
		
		print(f"Testing TWSE API connection to: {url}")
		response = requests.get(url, timeout=10, headers=headers)
		print(f"Response status: {response.status_code}")
		print(f"Response headers: {dict(response.headers)}")
		
		response.raise_for_status()
		
		data = response.json()
		data_count = len(data.get("data", []))
		print(f"Successfully received {data_count} data records")
		
		return {
			"status": "ok",
			"data_count": data_count,
			"response_status": response.status_code,
			"url": url
		}
	except requests.Timeout:
		return {
			"status": "failed",
			"error": "Timeout after 10 seconds",
			"url": url
		}
	except requests.ConnectionError as e:
		return {
			"status": "failed", 
			"error": f"Connection error: {str(e)}",
			"url": url
		}
	except Exception as exc:
		return {
			"status": "failed",
			"error": str(exc),
			"url": url
		}


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
	return JSONResponse(
		status_code=500,
		content={"error": "Internal server error", "message": str(exc)},
	)


if __name__ == "__main__":
	import uvicorn
	import os
	# Set working directory to script location
	os.chdir(os.path.dirname(os.path.abspath(__file__)))
	uvicorn.run(app, host="0.0.0.0", port=8001)

