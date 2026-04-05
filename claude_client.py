import anthropic
import base64
import json
import os
import asyncio
from prompts import build_system_prompt, build_user_prompt

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


async def analyze_fridge_and_get_recipes(
    image_bytes: bytes,
    diet: str | None = None,
) -> dict:
    """
    Send fridge image to Claude, get back structured recipes.

    Returns:
        {
            "ingredients": "список ингредиентов (строка)",
            "recipes": [
                {
                    "name": str,
                    "time": str,
                    "difficulty": str,
                    "ingredients": str,
                    "steps": str,
                }
            ]
        }
    """
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    # Run sync Anthropic client in thread pool so we don't block asyncio
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=build_system_prompt(diet),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": build_user_prompt(diet),
                        },
                    ],
                }
            ],
        ),
    )

    raw_text = response.content[0].text
    return parse_response(raw_text)


def parse_response(raw: str) -> dict:
    """Parse Claude's JSON response into a clean dict."""
    # Strip markdown fences if present
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip().rstrip("```").strip()

    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        # Fallback: return raw text as a single "recipe"
        return {
            "ingredients": "Не удалось распознать список продуктов.",
            "recipes": [
                {
                    "name": "Ответ ИИ",
                    "time": "—",
                    "difficulty": "—",
                    "ingredients": "—",
                    "steps": raw,
                }
            ],
        }

    # Normalise ingredients list to a readable string
    ingredients_raw = data.get("ingredients", [])
    if isinstance(ingredients_raw, list):
        ingredients_str = "\n".join(f"• {item}" for item in ingredients_raw)
    else:
        ingredients_str = str(ingredients_raw)

    recipes = []
    for r in data.get("recipes", []):
        ing = r.get("ingredients", [])
        if isinstance(ing, list):
            ing = "\n".join(f"• {i}" for i in ing)

        steps = r.get("steps", [])
        if isinstance(steps, list):
            steps = "\n".join(f"{idx}. {s}" for idx, s in enumerate(steps, 1))

        recipes.append(
            {
                "name": r.get("name", "Рецепт"),
                "time": r.get("time", "~30 мин"),
                "difficulty": r.get("difficulty", "средняя"),
                "ingredients": ing,
                "steps": steps,
            }
        )

    return {"ingredients": ingredients_str, "recipes": recipes}
