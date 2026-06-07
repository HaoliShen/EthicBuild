from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI


@dataclass
class ModelOption:
    id: str
    label: str
    source: str = "remote"


EXCLUDED_MODEL_KEYWORDS = (
    "embedding",
    "image",
    "vision",
    "audio",
    "speech",
    "tts",
    "asr",
    "video",
    "seedance",
    "i2v",
    "t2v",
    "rerank",
    "moderation",
)

LOW_COST_HINTS = ("lite", "flash", "mini", "turbo")
CHAT_HINTS = ("doubao", "deepseek", "qwen", "glm", "gpt", "claude", "moonshot", "kimi")

QUALITY_PREFERRED_BY_PROVIDER = {
    "ark": [
        "doubao-1-5-pro-32k-character-250715",
        "doubao-1-5-pro-32k-250115",
        "deepseek-v3-2-251201",
        "doubao-seed-2-0-pro-260215",
        "doubao-seed-1-6-251015",
    ],
    "deepseek": ["deepseek-chat"],
    "dashscope": ["qwen-plus", "qwen-max", "qwen-turbo"],
    "openai": ["gpt-4.1", "gpt-4.1-mini", "gpt-4o"],
}


FALLBACK_MODELS = {
    "ark": [
        "doubao-lite-32k-240828",
        "doubao-lite-128k-240828",
        "doubao-pro-32k-240828",
    ],
    "deepseek": [
        "deepseek-chat",
    ],
    "dashscope": [
        "qwen-turbo",
        "qwen-plus",
    ],
    "openai": [
        "gpt-4o-mini",
        "gpt-4.1-mini",
    ],
}


def infer_provider(api_key: str | None, base_url: str | None = None) -> str:
    key = api_key or ""
    url = (base_url or "").lower()
    if key.startswith("ark-") or "volces.com" in url:
        return "ark"
    if "deepseek" in url:
        return "deepseek"
    if "dashscope" in url or "aliyuncs" in url:
        return "dashscope"
    return "openai"


def discover_model_options(
    api_key: str | None,
    base_url: str | None,
    provider: str | None = None,
    timeout: float = 10.0,
) -> tuple[list[ModelOption], str]:
    provider = provider or infer_provider(api_key, base_url)
    if not api_key:
        return _fallback_options(provider), "未检测到 API Key，展示内置候选模型。"

    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        models = client.models.list()
        ids = sorted({model.id for model in models.data})
        filtered = [model_id for model_id in ids if _looks_like_chat_model(model_id)]
        if not filtered:
            filtered = ids
        ordered = _rank_models(filtered, provider)
        return [ModelOption(id=model_id, label=_label(model_id), source="remote") for model_id in ordered], (
            f"已从 {provider} /models 获取 {len(ordered)} 个候选模型。"
        )
    except Exception as exc:
        return _fallback_options(provider), f"模型列表获取失败，展示内置候选模型：{type(exc).__name__}: {str(exc)[:120]}"


def choose_default_model(model_options: list[ModelOption], preferred_model: str | None = None) -> str | None:
    if preferred_model and any(option.id == preferred_model for option in model_options):
        return preferred_model
    if preferred_model and not model_options:
        return preferred_model
    if not model_options:
        return preferred_model
    option_ids = {option.id for option in model_options}
    for provider_candidates in QUALITY_PREFERRED_BY_PROVIDER.values():
        for candidate in provider_candidates:
            if candidate in option_ids:
                return candidate
    for option in model_options:
        if "pro" in option.id.lower() and "character" not in option.id.lower():
            return option.id
    return model_options[0].id


def _looks_like_chat_model(model_id: str) -> bool:
    lowered = model_id.lower()
    if any(keyword in lowered for keyword in EXCLUDED_MODEL_KEYWORDS):
        return False
    return any(hint in lowered for hint in CHAT_HINTS)


def _rank_models(model_ids: list[str], provider: str) -> list[str]:
    def key(model_id: str) -> tuple[int, int, int, str]:
        lowered = model_id.lower()
        provider_preferred = 0
        if provider == "ark":
            provider_preferred = 0 if lowered.startswith("doubao") else 1
        elif provider == "dashscope":
            provider_preferred = 0 if lowered.startswith("qwen") else 1
        elif provider == "deepseek":
            provider_preferred = 0 if lowered.startswith("deepseek") else 1
        low_cost = 0 if any(hint in lowered for hint in LOW_COST_HINTS) else 1
        older = 1 if any(token in lowered for token in ("2403", "2404", "2405", "2406", "2407")) else 0
        return (provider_preferred, low_cost, older, model_id)

    return sorted(model_ids, key=key)


def _fallback_options(provider: str) -> list[ModelOption]:
    return [ModelOption(id=model_id, label=f"{model_id}（内置候选）", source="fallback") for model_id in FALLBACK_MODELS.get(provider, FALLBACK_MODELS["openai"])]


def _label(model_id: str) -> str:
    lowered = model_id.lower()
    tags = []
    if any(model_id == candidate for candidates in QUALITY_PREFERRED_BY_PROVIDER.values() for candidate in candidates[:2]):
        tags.append("推荐：完整增强")
    if any(hint in lowered for hint in LOW_COST_HINTS):
        tags.append("轻量")
    if "pro" in lowered:
        tags.append("较强")
    if "128k" in lowered:
        tags.append("长上下文")
    if "functioncall" in lowered:
        tags.append("函数调用")
    suffix = f"（{'，'.join(tags)}）" if tags else ""
    return f"{model_id}{suffix}"
