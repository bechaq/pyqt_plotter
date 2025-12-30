import re

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