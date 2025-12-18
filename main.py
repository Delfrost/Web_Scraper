from fastapi import FastAPI
from models import ScrapeRequest, ScrapeResponse
from scraper import scrape_smart

app = FastAPI()

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest):
    result = await scrape_smart(request.url)
    return ScrapeResponse(result=result)