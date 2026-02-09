from __future__ import annotations

from typing import Optional

import requests

from .base import LLM


class CloudLLM(LLM):
    """
    Generic cloud LLM client. Adjust payload/response mapping for your provider.
    """

    def __init__(self, api_url: str, api_key: str, model: str, timeout_s: int = 30):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = requests.post(self.api_url, json=payload, headers=headers, timeout=self.timeout_s)
        resp.raise_for_status()
        data = resp.json()
        # Expecting: {"text": "..."}
        return data.get("text", "")
