# ==========================================
# File: model_client_ollama.py
# Updated in iteration: 4
# Author: Karl Concha
#
# Lightweight client for calling a locally hosted Ollama instance.
#
# Notes:
# - Uses the /api/chat endpoint with stream=False
# - Raises exceptions for HTTP/network errors so the runtime can mark stages FAILED
#
# #ChatGPT (OpenAI, 2025) – Assisted in structuring a minimal Ollama model
# client abstraction with explicit error propagation to support safe
# stop-on-failure behaviour during stage execution.
# Conversation Topic: "Integrating Ollama into Rainn"
# Date: January 2026
#
# Used by StageRunner to generate stage output within agent_runtime_service
# ==========================================

import requests

class OllamaModelClient:
    """
    Minimal Ollama HTTP client for localhost.
    """

    def __init__(self, host="http://localhost:11434", timeout_seconds=300):
        self.host = host.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def generate(self, model_name, prompt, system_prompt=None, json_mode=False):
        """
        Generate a single response from Ollama (non-streaming) with needed parameters given.
        If system_prompt is provided, it is sent as a top-level system instruction.
        If json_mode is True, Ollama is told to force JSON output (no prose or code fences).
        """

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False
        } #The packet of data to send to ollama

        if json_mode:
            payload["format"] = "json" # Forces Ollama to return clean JSON — no prose, no code fences

        r = requests.post(
            f"{self.host}/api/chat",
            json=payload, #specifying the payload to be json
            timeout=self.timeout_seconds
        )

        # If Ollama returns 4xx/5xx this will raise, and the runtime will mark stage FAILED.
        r.raise_for_status()

        data = r.json() if r.content else {} #converting JSON into a readable python object
        message = data.get("message") or {}
        response_text = (message.get("content") or "").strip() #response within the object is only collected

        if not response_text:
            # Empty responses are treated as failed stages.
            raise Exception("Ollama returned an empty response.")

        return response_text
