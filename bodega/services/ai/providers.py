"""AI providers: which ones Bodega knows, their live model lists, and asking one a question.

Two kinds of API cover them all:
- "anthropic": Anthropic's Messages API
- "openai":    the OpenAI-style Chat Completions API, which OpenAI, Google Gemini (its compatibility
               endpoint), Kimi (Moonshot AI), OpenRouter, DeepSeek, Mistral, xAI, Groq and local servers
               (Ollama, LM Studio) all speak. "Other" takes any address that speaks it.

Model lists are always asked of the provider (never written down here), so they're never out of date.

Safety:
- your key goes only to the provider's own address, over https (plain http only to this computer, for
  a model running locally), and never follows a redirect anywhere else
- the key lives in the keychain (services/secrets.py), is sent only in the request header, and is
  never logged or shown in an error
- answers are capped in size and read as plain text or JSON; nothing in them is ever run
"""

from __future__ import annotations

import ipaddress
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

from bodega import __version__
from bodega.core import web
from bodega.core.log import get_logger
from bodega.services import secrets

log = get_logger(__name__)

TIMEOUT_S = 90  # thinking models can take a while
MAX_ANSWER_BYTES = 2_000_000
ANTHROPIC_VERSION = "2023-06-01"  # the Messages API version header (a fixed API contract, not a model)
MAX_TOKENS = 4096  # Anthropic needs a cap on the answer's length


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    base_url: str  # "" = you type it (Other)
    kind: str  # "anthropic" or "openai"
    keys_page: str = ""  # where to make a key
    needs_key: bool = True


PROVIDERS: dict[str, Provider] = {
    p.key: p
    for p in (
        Provider("anthropic", "Anthropic", "https://api.anthropic.com/v1", "anthropic",
                 "https://console.anthropic.com/settings/keys"),
        Provider("openai", "OpenAI (ChatGPT)", "https://api.openai.com/v1", "openai",
                 "https://platform.openai.com/api-keys"),
        Provider("gemini", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta/openai", "openai",
                 "https://aistudio.google.com/apikey"),
        Provider("kimi", "Kimi (Moonshot AI)", "https://api.moonshot.ai/v1", "openai",
                 "https://platform.moonshot.ai/console/api-keys"),
        Provider("kimi-cn", "Kimi (Moonshot AI, China)", "https://api.moonshot.cn/v1", "openai",
                 "https://platform.moonshot.cn/console/api-keys"),
        Provider("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "openai", "https://openrouter.ai/keys"),
        Provider("deepseek", "DeepSeek", "https://api.deepseek.com/v1", "openai",
                 "https://platform.deepseek.com/api_keys"),
        Provider("mistral", "Mistral", "https://api.mistral.ai/v1", "openai", "https://console.mistral.ai/api-keys"),
        Provider("xai", "xAI (Grok)", "https://api.x.ai/v1", "openai", "https://console.x.ai"),
        Provider("groq", "Groq", "https://api.groq.com/openai/v1", "openai", "https://console.groq.com/keys"),
        Provider("custom", "Other (OpenAI-compatible)", "", "openai", "", needs_key=False),
    )
}  # fmt: skip

# model ids that can't hold a conversation (pictures, speech, search indexes…), left out of the list
NOT_CHAT = (
    "embed",
    "tts",
    "whisper",
    "dall-e",
    "moderation",
    "transcribe",
    "audio",
    "realtime",
    "image",
    "rerank",
)


class AIError(OSError):
    """Something went wrong talking to the provider, in plain words (never containing the key)."""


@dataclass
class Setup:
    """Which provider and model to use (kept in settings; the key is in the keychain)."""

    provider: str = ""
    model: str = ""
    base_url: str = ""  # Other only

    @classmethod
    def from_settings(cls, settings: dict) -> Setup:
        d = settings.get("ai") if isinstance(settings.get("ai"), dict) else {}
        return cls(str(d.get("provider") or ""), str(d.get("model") or ""), str(d.get("base_url") or ""))

    def to_settings(self, settings: dict) -> None:
        settings["ai"] = {"provider": self.provider, "model": self.model, "base_url": self.base_url}

    @property
    def p(self) -> Provider | None:
        return PROVIDERS.get(self.provider)

    def url(self) -> str:
        p = self.p
        base = (self.base_url if p and p.key == "custom" else (p.base_url if p else "")).strip().rstrip("/")
        return base

    def ready(self) -> bool:
        p = self.p
        return bool(p and self.model and self.url() and (key_for(p.key) or not p.needs_key))


def secret_name(provider: str) -> str:
    return f"ai:{provider}"


def key_for(provider: str) -> str:
    return secrets.get(secret_name(provider))


def save_key(provider: str, key: str) -> None:
    secrets.put(secret_name(provider), key.strip())


# ---------------------------------------------------------------- the address
def check_address(url: str) -> str:
    """The provider's address, checked: https to anywhere, or http only to this computer (a local model).
    Returns it without a trailing /. Raises AIError."""
    try:
        u = urlparse(url.strip())
        host = u.hostname
        _port = u.port
    except ValueError:
        raise AIError("That address isn't right. It should look like https://api.example.com/v1") from None
    if u.scheme not in ("https", "http") or not host or "@" in u.netloc:
        raise AIError("That address should start with https://")
    if u.scheme == "http" and not _local(host):
        raise AIError("Use https:// (plain http is only for a model running on this computer).")
    return url.strip().rstrip("/")


def _local(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


# ---------------------------------------------------------------- talking to it
def _headers(setup: Setup, key: str) -> dict[str, str]:
    h = {"Content-Type": "application/json", "User-Agent": f"Bodega/{__version__}"}
    if setup.p and setup.p.kind == "anthropic":
        h["x-api-key"] = key
        h["anthropic-version"] = ANTHROPIC_VERSION
    elif key:
        h["Authorization"] = f"Bearer {key}"
    if setup.provider == "openrouter":
        h["X-Title"] = "Bodega"
    return h


def _call(setup: Setup, path: str, body: dict | None = None, key: str | None = None) -> dict:
    base = check_address(setup.url())
    key = key_for(setup.provider) if key is None else key
    if setup.p and setup.p.needs_key and not key:
        raise AIError("Add your API key first.")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        base + path, data=data, headers=_headers(setup, key), method="POST" if body else "GET"
    )
    try:
        with web.open_no_redirect(req, TIMEOUT_S, direct=_local(urlparse(base).hostname or "")) as r:
            raw = r.read(MAX_ANSWER_BYTES + 1)
    except urllib.error.HTTPError as e:
        detail = _error_text(e).replace(key, "…") if key else _error_text(e)
        raise AIError(_why(e.code, detail)) from None
    except Exception as e:  # no internet, timeouts, TLS problems…
        log.info("AI request to %s failed: %s", urlparse(base).hostname, type(e).__name__)
        raise AIError(
            f"Couldn't reach {setup.p.label if setup.p else 'the provider'}. Check your internet."
        ) from None
    if len(raw) > MAX_ANSWER_BYTES:
        raise AIError("The answer was too long.")
    try:
        d = json.loads(raw.decode("utf-8", errors="replace"))
    except (ValueError, RecursionError):
        raise AIError("The provider sent something Bodega couldn't read.") from None
    if not isinstance(d, dict):
        raise AIError("The provider sent something Bodega couldn't read.")
    return d


def _error_text(e: urllib.error.HTTPError) -> str:
    """The provider's own short reason, if it gave one (never echoed back raw: it's trimmed and plain)."""
    try:
        d = json.loads(e.read(20_000).decode("utf-8", errors="replace"))
    except Exception:
        return ""
    err = d.get("error") if isinstance(d, dict) else None
    msg = err.get("message") if isinstance(err, dict) else (err if isinstance(err, str) else "")
    return " ".join(str(msg or "").split())[:200]


def _why(code: int, detail: str) -> str:
    plain = {
        400: "The provider didn't accept the request",
        401: "The key wasn't accepted. Check it, or make a new one",
        403: "This key isn't allowed to use that model",
        404: "That model or address wasn't found",
        429: "Too many requests, or the account is out of credit. Try again in a minute",
    }.get(code, f"The provider had a problem (error {code})")
    if 300 <= code < 400:
        plain = "The provider's address redirects somewhere else, so Bodega stopped (your key stays private)"
    return plain + (f": {detail}" if detail and code not in (401,) else ".")


def list_models(setup: Setup, key: str | None = None) -> list[str]:
    """The models this key can use, asked of the provider just now (newest names first where it says)."""
    try:
        return _models(_call(setup, "/models", key=key))
    except (KeyError, AttributeError, TypeError, IndexError):
        raise AIError("The provider's list of models came back in a shape Bodega couldn't read.") from None


def _models(d: dict) -> list[str]:
    rows = d.get("data") if isinstance(d, dict) else None
    if not isinstance(rows, list):
        rows = d.get("models") if isinstance(d, dict) else []
    ids = []
    for m in rows or []:
        mid = str((m.get("id") or m.get("name") or "") if isinstance(m, dict) else m).strip()
        mid = mid.removeprefix("models/")
        if mid and not any(word in mid.lower() for word in NOT_CHAT):
            ids.append(mid)
    return list(dict.fromkeys(ids))


def ask(setup: Setup, system: str, user: str, key: str | None = None) -> str:
    """One question, one answer (plain text). `key`: use this one instead of the saved one (Test)."""
    if not setup.model:
        raise AIError("Pick a model first.")
    try:
        return _ask(setup, system, user, key)
    except (KeyError, AttributeError, TypeError, IndexError):
        raise AIError("The model's answer came back in a shape Bodega couldn't read.") from None


def _ask(setup: Setup, system: str, user: str, key: str | None) -> str:
    if setup.p and setup.p.kind == "anthropic":
        d = _call(
            setup,
            "/messages",
            {"model": setup.model, "max_tokens": MAX_TOKENS, "system": system,
             "messages": [{"role": "user", "content": user}]},
            key=key,
        )  # fmt: skip
        parts = d.get("content") if isinstance(d, dict) else None
        text = "".join(
            p.get("text", "") for p in parts or [] if isinstance(p, dict) and p.get("type") == "text"
        )
    else:
        d = _call(
            setup,
            "/chat/completions",
            {"model": setup.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            key=key,
        )  # fmt: skip
        choices = d.get("choices") if isinstance(d, dict) else None
        msg = choices[0].get("message", {}) if choices and isinstance(choices[0], dict) else {}
        text = msg.get("content") or ""
        if isinstance(text, list):  # some providers send parts
            text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
    text = str(text).strip()
    if not text:
        raise AIError("The model didn't answer. Try again, or pick another model.")
    return text


def read_json(text: str):
    """The JSON in a model's answer (models sometimes wrap it in ``` or a sentence: the first {…} or […]
    wins), or None if there isn't any."""
    starts = [i for i in (text.find("["), text.find("{")) if i != -1]
    for start in sorted(starts):  # whichever comes first is the answer's outside ([…] or {…})
        closer = "]" if text[start] == "[" else "}"
        end = text.rfind(closer)
        if end > start:
            try:
                return json.loads(text[start : end + 1])
            except (ValueError, RecursionError):
                continue
    return None


def ask_json(setup: Setup, system: str, user: str):
    """Ask for JSON and read it."""
    got = read_json(ask(setup, system + "\n\nAnswer with JSON only, no other words.", user))
    if got is None:
        raise AIError(
            "The model's answer wasn't in the shape Bodega asked for. Try again, or pick another model."
        )
    return got
