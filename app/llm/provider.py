"""LLM Provider abstraction - supports Anthropic Claude and OpenAI."""

from abc import ABC, abstractmethod
from app.config import settings


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
        pass


class AnthropicProvider(LLMProvider):
    def __init__(self):
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text


class OpenAIProvider(LLMProvider):
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content


# --- Portkey Provider (optional, remove this block if not needed) ---
class PortkeyProvider(LLMProvider):
    """Uses Portkey SDK to route to Claude/GPT via Portkey gateway."""

    def __init__(self):
        from portkey_ai import AsyncPortkey
        self.client = AsyncPortkey(
            api_key=settings.portkey_api_key,
            provider="anthropic",
        )

    async def generate(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
        response = await self.client.chat.completions.create(
            model="claude-sonnet-4-20250514",
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content
# --- End Portkey Provider ---


# --- Gemini Provider ---
class GeminiProvider(LLMProvider):
    """Uses Google Gemini API with Google Search grounding for real-time data."""

    def __init__(self):
        from google import genai
        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def generate(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
        from google.genai import types

        # Enable Google Search grounding - Gemini will search the internet
        # for real-time market data from trusted sources
        response = self.client.models.generate_content(
            model=settings.gemini_model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        return response.text
# --- End Gemini Provider ---


def get_llm() -> LLMProvider:
    """Factory function to get the configured LLM provider."""
    if settings.llm_provider == "gemini":
        return GeminiProvider()
    if settings.llm_provider == "portkey":
        return PortkeyProvider()
    if settings.llm_provider == "openai":
        return OpenAIProvider()
    return AnthropicProvider()
