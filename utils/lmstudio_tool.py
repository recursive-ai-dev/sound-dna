#!/usr/bin/env python3
"""
lmstudio_tool.py

Utility for interacting with the LM Studio local API.
Supports chat completions with retry logic and robust error handling.
"""

import requests
import time
import logging
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger("LMStudioTool")

class LMStudioTool:
    """
    Client for LM Studio Local Server (OpenAI-compatible API).
    """
    def __init__(
        self,
        model: str = "deepseek-r1-0528-qwen3-8b@q3_k_l",
        port: int = 1234,
        max_retries: int = 3,
        timeout: int = 30
    ):
        self.api_url = f"http://localhost:{port}/v1/chat/completions"
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout

    def ask(
        self,
        prompt: str,
        system_msg: str = "You are an expert in Sonic DNA encoding. Reply with precision and conciseness.",
        temperature: float = 0.2,
        max_tokens: int = 512
    ) -> str:
        """
        Send a prompt to the LLM and return the string response.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Sending prompt to LM Studio (Attempt {attempt}/{self.max_retries})")
                resp = requests.post(self.api_url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                content = data['choices'][0]['message']['content'].strip()
                return content
            except requests.exceptions.RequestException as e:
                logger.error(f"LM Studio API error (attempt {attempt}): {e}")
                if attempt < self.max_retries:
                    time.sleep(2)
                else:
                    raise RuntimeError(f"Failed to connect to LM Studio after {self.max_retries} attempts.") from e
            except (KeyError, IndexError, ValueError) as e:
                logger.error(f"Failed to parse LM Studio response: {e}")
                raise RuntimeError("Invalid response format from LM Studio.") from e

        return ""

# ---- USAGE EXAMPLE ----
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    lm = LMStudioTool()
    try:
        # Example query:
        test_prompt = "What is Sonic DNA? Answer in one sentence."
        print(f"Querying: {test_prompt}")
        result = lm.ask(test_prompt)
        print(f"LLM Response: {result}")
    except Exception as ex:
        print(f"Demo failed: {ex}")
