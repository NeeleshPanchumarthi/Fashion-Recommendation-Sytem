import httpx

from app.config.settings import Settings

_settings = Settings()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def extract_sentiment(text: str) -> str:
    """
    Extract sentiment from a product review using a Groq-hosted LLM.

    Returns:
        "positive"
        "neutral"
        "negative"

    If the API request fails, the function returns "neutral"
    so that one failed review does not stop the ingestion pipeline.
    """

    # Handle empty reviews
    if text is None or not str(text).strip():
        return "neutral"

    review = str(text).strip()

    prompt = f"""
Classify the sentiment of the following product review.

You must return exactly ONE of these three labels:
positive
neutral
negative

Do not provide any explanation.

Review:
{review}
""".strip()

    payload = {
        "model": _settings.GROQ_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0,
        "max_tokens": 5,
    }

    headers = {
        "Authorization": f"Bearer {_settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(
            GROQ_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )

        # Print the actual Groq error instead of only showing "400 Bad Request"
        if response.status_code != 200:
            print(
                f"Groq API error [{response.status_code}]: "
                f"{response.text}"
            )

        response.raise_for_status()

        data = response.json()

        result = (
            data["choices"][0]["message"]["content"]
            .strip()
            .lower()
        )

        # Normalize the model response
        if "positive" in result:
            return "positive"

        if "negative" in result:
            return "negative"

        if "neutral" in result:
            return "neutral"

        # Unexpected model output
        return "neutral"

    except httpx.HTTPError as exc:
        print(f"Groq HTTP error: {exc}")
        return "neutral"

    except (KeyError, IndexError, TypeError) as exc:
        print(f"Unexpected Groq response: {exc}")
        return "neutral"