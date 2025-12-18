from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from models import ScrapeRequest, ScrapeResponse
from scraper import scrape_smart
import os

app = FastAPI()

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest):
    result = await scrape_smart(request.url)
    return ScrapeResponse(result=result)

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()