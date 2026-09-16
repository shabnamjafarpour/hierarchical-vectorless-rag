import json

from src.utils.llm_utils import response_to_text


def parse_llm_json(response):
    content = response_to_text(response).strip()

    if content.startswith("```"):
        content = content.replace("```json", "")
        content = content.replace("```", "")
        content = content.strip()

    return json.loads(content)