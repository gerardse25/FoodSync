def contains_control_characters(value: str) -> bool:
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in value)


def contains_escape_sequences(value: str) -> bool:
    return "\\n" in value or "\\t" in value or "\\r" in value


def validate_text(value: str, field_name: str, min_len: int, max_len: int) -> str:
    value = value.strip()

    if not value:
        raise ValueError(f"El camp {field_name} no pot estar buit")

    if len(value) < min_len or len(value) > max_len:
        raise ValueError(
            f"El camp {field_name} ha de tenir entre {min_len} i {max_len} caràcters"
        )

    if contains_control_characters(value):
        raise ValueError(f"El camp {field_name} no pot contenir caràcters de control")

    if contains_escape_sequences(value):
        raise ValueError(f"El camp {field_name} no pot contenir seqüències d'escape")

    if any(ch.isspace() for ch in value):
        raise ValueError(f"El camp {field_name} no pot contenir espais interns")

    return value
