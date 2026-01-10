import re
import re

_float_re = re.compile(r"""
    ^\s*
    [+-]?
    (?:
        (?:\d+([.,]\d*)?) |
        (?:[.,]\d+)
    )
    (?:[eE][+-]?\d+)?   # exponent
    \s*$
""", re.VERBOSE)

def parse_float(s: str):
    """
    Robust float parsing:
    - supports decimal comma: "3,14"
    - supports thousands separators: "1,234.56" or "1 234,56"
    - returns None if not parseable
    """
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None

    # Remove surrounding quotes
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()

    # Remove spaces used as thousands separators
    s = s.replace(" ", "")

    # If both ',' and '.' exist, assume one is thousands separator.
    # Common cases:
    #  - "1,234.56" -> ',' thousands, '.' decimal
    #  - "1.234,56" -> '.' thousands, ',' decimal
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            # decimal comma
            s = s.replace(".", "")
            s = s.replace(",", ".")
        else:
            # decimal dot
            s = s.replace(",", "")
    else:
        # Only comma present -> treat as decimal comma
        if "," in s and "." not in s:
            s = s.replace(",", ".")

    # Quick validation (avoid ValueError spam)
    if not _float_re.match(s):
        return None

    try:
        return float(s)
    except Exception:
        return None

def detect_delimiter(line):
    if ";" in line:
        return ";"
    if "," in line:
        return ","
    if "\t" in line:
        return "\t"
    return None  # whitespace


def split_line(line, delimiter):
    if delimiter:
        return [x.strip() for x in line.split(delimiter)]
    else:
        return re.split(r"\s+", line.strip())


def is_number(s):
    try:
        float(s.replace(",", "."))
        return True
    except ValueError:
        return False