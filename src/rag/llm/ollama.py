from __future__ import annotations

from typing import Optional

import requests

from .base import LLM


class OllamaLLM(LLM):
    def __init__(self, base_url: str, model: str, timeout_s: int = 60):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        try:
            return self._generate_v1(prompt, system_prompt)
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code in (404, 405):
                return self._generate_openai(prompt, system_prompt)
            raise

    def _generate_v1(self, prompt: str, system_prompt: Optional[str]) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
        }
        resp = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")

    def _generate_openai(self, prompt: str, system_prompt: Optional[str]) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        resp = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={"model": self.model, "messages": messages},
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""
