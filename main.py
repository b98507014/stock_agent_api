from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Union, List

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


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)},
    )

