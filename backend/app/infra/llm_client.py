"""OpenAI / Claude API 호출 클라이언트"""

from openai import AsyncOpenAI
from app.config import settings

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
