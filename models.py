from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Meta(BaseModel):
    title: str = ""
    description: str = ""
    language: str = "en"
    canonical: Optional[str] = None

class Link(BaseModel):
    text: str
    href: str

class Image(BaseModel):
    src: str
    alt: str

class Content(BaseModel):
    headings: List[str] = []
    text: str = ""
    links: List[Link] = []
    images: List[Image] = []
    lists: List[List[str]] = []
    tables: List[Any] = []

class Section(BaseModel):
    id: str
    type: str = "section"
    label: str
    sourceUrl: str
    content: Content
    rawHtml: str
    truncated: bool = False

class Interactions(BaseModel):
    clicks: List[str] = []
    scrolls: int = 0
    pages: List[str] = []

class Error(BaseModel):
    message: str
    phase: str

class ScrapeResult(BaseModel):
    url: str
    scrapedAt: str
    meta: Meta
    sections: List[Section]
    interactions: Interactions = Field(default_factory=Interactions)
    errors: List[Error] = []

class ScrapeRequest(BaseModel):
    url: str

class ScrapeResponse(BaseModel):
    result: ScrapeResult