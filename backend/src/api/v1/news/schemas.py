from pydantic import BaseModel


class PromptRequest(BaseModel):
    prompt: str


class NewsSummaryRequestSchema(BaseModel):
    content: str


class NewsArticleResponse(BaseModel):
    id: int
    url: str
    title: str
    time: str
    content: str
    summary: str
    reason: str
    upvotes: int = 0
    is_upvoted: bool = False
    
    class Config:
        from_attributes = True