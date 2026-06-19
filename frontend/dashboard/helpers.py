JsonObject = dict[str, object]


def format_percentage(value: float) -> str:
    return f"{value * 100:.0f}%"


def format_count(value: int | float) -> str:
    return f"{int(value):,}"


def format_float_metric(value: float | None, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}" if value is not None else "N/A"


def format_display_value(value: object) -> str:
    if value is None:
        return "null"

    if isinstance(value, bool):
        return str(value).lower()

    return str(value)


def format_gear(reverse_state: object) -> str:
    if reverse_state is True:
        return "Reverse"
    if reverse_state is False:
        return "Forward"

    return format_display_value(reverse_state)


def format_validation_error_messages(validation_errors: object) -> str:
    if not isinstance(validation_errors, list) or not validation_errors:
        return ""

    messages: list[str] = []
    for validation_error in validation_errors:
        if not isinstance(validation_error, dict):
            continue

        message = validation_error.get("message")
        if message is None or not str(message).strip():
            continue

        formatted_message = str(message)
        raw_value = validation_error.get("raw_value")
        if raw_value is not None:
            formatted_message = f"{formatted_message} (raw: {raw_value})"

        messages.append(formatted_message)

    return "; ".join(messages)
