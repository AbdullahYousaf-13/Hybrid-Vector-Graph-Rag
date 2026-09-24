import re

_PREAMBLE = re.compile(
    r"^(based (solely |only )?on|according to|from|using) (the |this )?"
    r"(provided |given |available |supplied |retrieved )?"
    r"(text|context|information|data|rows|passages?|excerpts?|sources?)[^,:\n]{0,40}[,:]\s*",
    re.IGNORECASE,
)


def clean_answer(text: str) -> str:
    text = text.strip()
    stripped = _PREAMBLE.sub("", text, count=1)
    if stripped != text and stripped:
        stripped = stripped[0].upper() + stripped[1:]
    return stripped or text
