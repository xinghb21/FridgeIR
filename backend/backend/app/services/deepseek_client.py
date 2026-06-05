import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings


class DeepSeekError(RuntimeError):
    """DeepSeek 调用失败时抛出的轻量错误。"""


def deepseek_available(settings: Settings) -> bool:
    """判断当前配置是否具备调用 DeepSeek 的基本条件。"""
    return bool(settings.deepseek_api_key.strip())


def _chat_completions_url(settings: Settings) -> str:
    """拼出 DeepSeek 的 OpenAI 兼容聊天接口地址。"""
    return f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"


def _extract_json_object(content: str) -> dict[str, Any]:
    """从模型文本中提取 JSON 对象。

    DeepSeek 支持 JSON Output，但模型偶尔仍可能包一层 Markdown 代码块。
    这里做一个保守兜底，避免前端请求因为格式小偏差直接失败。
    """
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            preview = text[:120].replace("\n", "\\n")
            raise DeepSeekError(f"模型没有返回可解析的 JSON，返回片段：{preview}")
        parsed = json.loads(text[start : end + 1])

    if not isinstance(parsed, dict):
        raise DeepSeekError("模型 JSON 顶层不是对象")
    return parsed


def chat_json(
    settings: Settings,
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    timeout_seconds: int | None = None,
    use_response_format: bool = True,
) -> dict[str, Any]:
    """调用 DeepSeek 聊天接口，并返回解析后的 JSON 对象。"""
    if not deepseek_available(settings):
        raise DeepSeekError("未配置 DEEPSEEK_API_KEY")

    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if use_response_format:
        payload["response_format"] = {"type": "json_object"}
    request = Request(
        _chat_completions_url(settings),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        timeout = timeout_seconds or settings.deepseek_timeout_seconds
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        message = exc.read().decode("utf-8", errors="ignore")
        raise DeepSeekError(f"DeepSeek HTTP {exc.code}: {message}") from exc
    except (URLError, TimeoutError) as exc:
        raise DeepSeekError(f"DeepSeek 网络请求失败: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DeepSeekError("DeepSeek 响应不是合法 JSON") from exc

    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DeepSeekError("DeepSeek 响应缺少 choices[0].message.content") from exc

    if not str(content or "").strip():
        finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else None
        raise DeepSeekError(f"模型返回空内容，finish_reason={finish_reason}")

    return _extract_json_object(content)
