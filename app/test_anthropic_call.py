from __future__ import annotations

import json
import os

from anthropic import Anthropic, APIConnectionError, APIStatusError, RateLimitError
from dotenv import load_dotenv


def main() -> None:
    load_dotenv(".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print(json.dumps({"ok": False, "message": "Missing ANTHROPIC_API_KEY"}, indent=2))
        return

    client = Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=128,
            messages=[{"role": "user", "content": "what does kafka do"}],
        )
        text_parts = [
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ]
        print(
            json.dumps(
                {
                    "ok": True,
                    "model": response.model,
                    "reply": "\n".join(text_parts).strip(),
                },
                indent=2,
            )
        )
    except RateLimitError as exc:
        print(
            json.dumps(
                {"ok": False, "type": "RateLimitError", "message": str(exc)},
                indent=2,
            )
        )
    except APIConnectionError as exc:
        print(
            json.dumps(
                {"ok": False, "type": "APIConnectionError", "message": str(exc)},
                indent=2,
            )
        )
    except APIStatusError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "type": exc.__class__.__name__,
                    "status_code": exc.status_code,
                    "message": str(exc),
                },
                indent=2,
            )
        )
    except Exception as exc:
        print(
            json.dumps(
                {"ok": False, "type": exc.__class__.__name__, "message": str(exc)},
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
