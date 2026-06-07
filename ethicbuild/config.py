from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-1-5-pro-32k-character-250715"


@dataclass
class LLMConfig:
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    timeout: float = 15.0

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.model)


def _extract_key_from_api_txt(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return None
    for separator in ("=", "：", ":"):
        if separator in text:
            text = text.split(separator, 1)[1].strip()
            break
    return text or None


def load_llm_config() -> LLMConfig:
    api_key = (
        os.getenv("ETHICBUILD_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ARK_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
        or _extract_key_from_api_txt(PROJECT_ROOT / "api.txt")
    )
    base_url = os.getenv("ETHICBUILD_BASE_URL")
    model = os.getenv("ETHICBUILD_MODEL") or DEFAULT_MODEL

    if api_key and api_key.startswith("ark-"):
        base_url = base_url or DEFAULT_ARK_BASE_URL
    elif os.getenv("DEEPSEEK_API_KEY"):
        base_url = base_url or "https://api.deepseek.com"
    elif os.getenv("DASHSCOPE_API_KEY"):
        base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"

    return LLMConfig(api_key=api_key, base_url=base_url, model=model)
