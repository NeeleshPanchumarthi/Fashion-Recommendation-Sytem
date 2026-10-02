import httpx
from ..config.settings import Settings

_settings = Settings()


def extract_sentiment(text: str) -> str:
    """Return a sentiment label ('positive', 'neutral', 'negative') using the Groq LLM.

    The function sends a short prompt to the model defined in ``Settings.GROQ_MODEL``
    and parses the response.  It expects the model to return one of the three labels.
    """
    if not text:
        return "neutral"
    prompt = (
        "Classify the sentiment of the following product review as Positive, Neutral, or Negative."
        " Return only the label.\n\nReview: \"" + text + "\""
    )
    response = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        json={"model": _settings.GROQ_MODEL, "messages": [{"role": "user", "content": prompt}]},
        headers={"Authorization": f"Bearer {_settings.GROQ_API_KEY}"},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()["choices"][0]["message"]["content"].strip().lower()
    if "positive" in result:
        return "positive"
    if "negative" in result:
        return "negative"
    return "neutral"
