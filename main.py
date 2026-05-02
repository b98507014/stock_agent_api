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

    @validator("mode")
    def validate_mode(cls, value):
        if value != "paper":
            raise ValueError("mode must be 'paper'")
        return value


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/suggest")
async def suggest(request: SuggestRequest):
    try:
        result = make_suggestion(
            ticker=request.ticker,
            cash=request.cash,
            mode=request.mode,
            execute=request.execute
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
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, timeout=5, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        data_count = len(data.get("data", []))
        
        return {
            "status": "ok",
            "data_count": data_count
        }
    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc)
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

