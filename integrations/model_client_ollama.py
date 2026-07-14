import requests

class OllamaModelClient:

    def __init__(self, host="http://localhost:11434", timeout_seconds=300):
        self.host = host.rstrip("/")
        self.timeout_seconds = timeout_seconds

    # The function to send instructions and data to the model
    def generate(self, model_name, prompt, system_prompt=None, json_mode=False, context=None):
        """
        Generate a single response from Ollama (non-streaming) with needed parameters given.
        If system_prompt is provided, it is sent as a top-level system instruction.
        If json_mode is True, Ollama is told to force JSON output (no prose or code fences).
        """

        # Create an empty messages list
        messages = []

        #If a system prompt var has a value
        if system_prompt:
            # Add it to the messages list as a dictionary list
            messages.append({"role": "system", "content": system_prompt})

        # If context has a value or is not None
        if context:
            messages.extend(context)

        # Add current prompt from outside to messages list
        messages.append({"role": "user", "content": prompt}) 

        #The packet of data to send to ollama
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False
        } 

        # If json_mode is not None or has a value
        if json_mode:
            # Forces Ollama to return clean JSON — no prose, no code fences
            payload["format"] = "json" 

        # Send the chat request to Ollama's /api/chat endpoint and wait up to timeout_seconds.
        response = requests.post(
            f"{self.host}/api/chat",
            json=payload, #specifying the payload to be json
            timeout=self.timeout_seconds
        )


        # If Ollama returns 4xx/5xx (error) this will raise, and the runtime will mark stage FAILED.
        response.raise_for_status()


        # converting JSON into a readable python object
        response_converted  = response.json() if response.content else {} 

        # Only retreive the "message" portion of the response
        AI_message = response_converted.get("message") or {}

        # Then get the "content" portion of the message
        response_text = (AI_message.get("content") or "").strip() #

        if not response_text:
            # Empty responses are treated as failed stages.
            raise Exception("Ollama returned an empty response.")

        # Retrun the "content"
        return response_text
