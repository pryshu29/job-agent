def format_recent_messages(
    recent_messages: list,
) -> str:

    if not recent_messages:

        return "No previous conversation."

    lines = []

    for item in recent_messages:

        role = item.get(
            "role",
            "unknown",
        )

        message = item.get(
            "message",
            "",
        )

        if not message:
            continue

        lines.append(
            f"{role}: {message}"
        )

    if not lines:

        return "No previous conversation."

    return "\n".join(lines)