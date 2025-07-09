import os
import json
import re

import httpx
from config import open_router_api_key, gemini_api_key
from google import genai
from google.genai import types

OPENROUTER_API_KEY = open_router_api_key
GEMINI_API_KEY = gemini_api_key

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

MODELS = [
    "mistralai/devstral-small:free",
    "google/gemma-3n-e4b-it:free",
    "nousresearch/deephermes-3-mistral-24b-preview:free"
]

SYSTEM_PROMPT = """You are a Telegram bot assistant that classifies group messages about job posts.

Your job is to label the sender as one of:
- "employer": offering remote virtual assistant or technical/dev work
- "freelancer": advertising their own services
- "spam": scammy or promotional content
- "unclear": not enough info
- "skip": irrelevant (e.g., looking for team leads, agencies, location/language (philippines, PH, USA, singapore etc) exclusions)

You’re only interested in remote VA/dev roles, not team leads, sales, or region/language-specific (asides Nigeria) jobs.
You can also make some exceptions to the criteria if it is dev/tech role.

Reply ONLY with a JSON object like:
{
  "label": "employer|freelancer|spam|unclear|skip",
  "reason": "brief reason",
  "response": "Hey! I just saw your job posting and I'm really interested.[ If a keyword or trivia question is required, add a natural reply here. ]"
}

Leave "response" empty unless label is "employer". Only respond if confident.
"""

# --- PRIMARY: Google GenAI LLM ---
def classify_with_google(message: str) -> dict | None:
    try:
        # Set up Gemini client
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        model = "gemma-3-12b-it"

        # Prepare the prompt
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(
                    text=f"{SYSTEM_PROMPT}\nMessage: \"{message.strip()}\"")]
            )
        ]

        config = types.GenerateContentConfig(response_mime_type="text/plain")

        # Generate response (non-streaming)
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )

        # Extract full text
        full_response = response.text.strip()

        # Attempt to extract JSON inside ```json ... ```
        match = re.search(r"```json\s*(.*?)\s*```", full_response, re.DOTALL)
        if match:
            json_text = match.group(1).strip()
        else:
            # Try fallback: see if the whole response is just JSON
            json_text = full_response

        # Attempt to parse
        parsed = json.loads(json_text)

        # Validate result (optional but useful)
        if not isinstance(parsed, dict) or "label" not in parsed:
            raise ValueError("Parsed output missing required keys.")

        return parsed

    except json.JSONDecodeError as e:
        print(f"⚠️ Google LLM JSON decode error: {e}")
        print(f"🪵 Raw text returned:\n---\n{full_response}\n---")
        return None
    except Exception as e:
        print(f"⚠️ Google LLM failed: {e}")
        return None


# --- FALLBACK: OpenRouter LLM ---
async def classify_with_openrouter(message: str) -> dict:
    payload = {
        "models": MODELS,
        "temperature": 0.2,
        "max_tokens": 300,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Message: \"{message.strip()}\""}
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=HEADERS,
                json=payload
            )
            response.raise_for_status()
            output = response.json()
            content = output["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception as e:
        print(f"❌ OpenRouter fallback also failed: {e}")
        return {"label": "unclear", "reason": "LLM error", "response": ""}


# --- UNIFIED CLASSIFIER ---
async def classify_message_llm(message: str) -> dict:
    result = classify_with_google(message)
    if result is None or result.get("label") not in {"employer", "freelancer", "spam", "unclear", "skip"}:
        print("🔁 Falling back to OpenRouter...")
        result = await classify_with_openrouter(message)
    return result
