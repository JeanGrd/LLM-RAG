from __future__ import annotations

import json
from typing import Iterable, List, Optional

import requests

from ..llama_cpp import EndpointPool
from .base import LLM


class LlamaCppLLM(LLM):
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_s: int = 60,
        rpc_targets: Optional[List[str]] = None,
    ):
        self.model = model
        self.timeout_s = timeout_s
        self._pool = EndpointPool.from_config(base_url, rpc_targets)

    def _messages(self, prompt: str, system_prompt: Optional[str]) -> List[dict]:
        messages: List[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _chat(self, prompt: str, system_prompt: Optional[str], stream: bool):
        payload = {
            "model": self.model,
            "messages": self._messages(prompt, system_prompt),
            "stream": stream,
        }
        url = f"{self._pool.next()}/v1/chat/completions"
        resp = requests.post(url, json=payload, stream=stream, timeout=self.timeout_s)
        resp.raise_for_status()
        return resp

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        resp = self._chat(prompt, system_prompt, stream=False)
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "") or ""

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Iterable[str]:
        resp = self._chat(prompt, system_prompt, stream=True)
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8")
            if line.startswith("data: "):
                line = line[len("data: ") :].strip()
            if line.strip() == "[DONE]":
                break
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            choices = data.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            chunk = delta.get("content") or ""
            if chunk:
                yield chunk
