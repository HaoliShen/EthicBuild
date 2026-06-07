from __future__ import annotations

import json
import re
from typing import Any

from .config import LLMConfig


class LLMUnavailableError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    @property
    def available(self) -> bool:
        return self.config.available

    def _ensure_client(self):
        if not self.available:
            raise LLMUnavailableError("LLM is not configured. Set ETHICBUILD_MODEL and API key.")
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise LLMUnavailableError("Missing dependency: openai. Run pip install -r requirements.txt.") from exc
            kwargs: dict[str, Any] = {
                "api_key": self.config.api_key,
                "timeout": self.config.timeout,
                "max_retries": 0,
            }
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> str:
        client = self._ensure_client()
        kwargs: dict[str, Any] = {}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if timeout:
            kwargs["timeout"] = timeout
        response = client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    def stream_complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> str:
        client = self._ensure_client()
        kwargs: dict[str, Any] = {"stream": True}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if timeout:
            kwargs["timeout"] = timeout
        stream = client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            **kwargs,
        )
        chunks: list[str] = []
        for event in stream:
            if not event.choices:
                continue
            delta = event.choices[0].delta.content or ""
            if delta:
                chunks.append(delta)
        return "".join(chunks)

    def json_complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int | None = 800,
    ) -> dict[str, Any]:
        text = self.complete(system=system, user=user, temperature=temperature, max_tokens=max_tokens)
        return extract_json_object(text)


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM output.")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("LLM output JSON is not an object.")
    return data
