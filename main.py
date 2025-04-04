from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import os

app = FastAPI()

# Serve static files and HTML templates
#app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=".")

# Raspberry Pi IP address through Tailscale and exposed FastAPI port
PI_API_URL = os.getenv("PI_API_URL", "http://100.111.203.36:8000")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/breaker/{breaker_id}/on")
async def turn_on_breaker(breaker_id: int):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{PI_API_URL}/toggle", json={
                "breaker_id": breaker_id,
                "state": True
            })
            return response.json()
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Failed to toggle breaker {breaker_id} ON", "error": str(e)})

@app.post("/breaker/{breaker_id}/off")
async def turn_off_breaker(breaker_id: int):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{PI_API_URL}/toggle", json={
                "breaker_id": breaker_id,
                "state": False
            })
            return response.json()
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Failed to toggle breaker {breaker_id} OFF", "error": str(e)})

@app.get("/breaker/{breaker_id}/status")
async def breaker_status(breaker_id: int):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PI_API_URL}/breaker/{breaker_id}/status")
            return response.json()
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Failed to fetch status for breaker {breaker_id}", "error": str(e)})