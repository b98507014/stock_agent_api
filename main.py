from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Union, List

from ai_stock_suggestion import make_suggestion

app = FastAPI(title="Stock RL Suggestion API")


class SuggestRequest(BaseModel):
    ticker: Optional[Union[str, List[str]]] = None
    cash: float = Field(..., gt=0)
    mode: str = "paper"

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
        result = make_suggestion(request.ticker, request.cash, request.mode)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )
