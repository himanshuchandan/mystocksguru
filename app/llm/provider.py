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


def get_llm() -> LLMProvider:
    """Factory function to get the configured LLM provider."""
    if settings.llm_provider == "openai":
        return OpenAIProvider()
    return AnthropicProvider()
