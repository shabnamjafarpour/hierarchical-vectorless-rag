def response_to_text(response) -> str:
    """Normalize model response content into plain text across supported response shapes."""
    content = response.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []

        for item in content:
            if isinstance(item, str):
                text_parts.append(item)

            elif isinstance(item, dict):
                text_parts.append(
                    item.get("text", "")
                )

        return "".join(text_parts)

    return str(content)
