import os
import numpy as np

from Helpers import detect_delimiter, split_line, parse_float

class DataFile:
    def __init__(self, path, headers, data):
        self.path = path
        self.headers = headers
        self.data = data

    def get_column(self, name):
        idx = self.headers.index(name)
        return self.data[:, idx]


def _is_pure_numeric_row(line: str, delimiter) -> bool:
    """
    STRICT rule:
    Return True only if EVERY field in the row is numeric.
    If any field is not numeric => False.
    """
    parts = split_line(line, delimiter)
    if not parts:
        return False
    for p in parts:
        if parse_float(p) is None:
            return False
    return True


def load_data_file(path: str) -> DataFile:
    ext = os.path.splitext(path)[1].lower()

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw_lines = f.readlines()

    # Clean lines: strip BOM, remove empties
    lines = []
    for l in raw_lines:
        l = l.replace("\ufeff", "").rstrip("\n").strip()
        if l:
            lines.append(l)

    if not lines:
        raise ValueError("No data found in file")

    # Remove comment-only lines
    comment_prefixes = ("#", "%", "//")
    filtered = [l for l in lines if not l.lstrip().startswith(comment_prefixes)]
    if not filtered:
        raise ValueError("No data found in file (only comments)")

    # Detect delimiter from first non-comment line (simple + predictable)
    delimiter = detect_delimiter(filtered[0])

    # Find first purely numeric row
    data_start = None
    for i, line in enumerate(filtered):
        if _is_pure_numeric_row(line, delimiter):
            data_start = i
            break

    if data_start is None:
        raise ValueError("No purely numeric data row detected")

    # Preamble (text) lines above numeric data
    preamble = filtered[:data_start]
    header_line = preamble[-1] if preamble else None

    # Determine number of columns from first numeric row
    first_parts = split_line(filtered[data_start], delimiter)
    ncols = len(first_parts)

    # Build headers:
    if header_line is not None:
        hp = split_line(header_line, delimiter)
        headers = [h.strip().strip('"').strip("'") for h in hp]
        # Reconcile length with ncols
        if len(headers) < ncols:
            headers += [f"col_{i}" for i in range(len(headers), ncols)]
        elif len(headers) > ncols:
            headers = headers[:ncols]
    else:
        headers = [f"col_{i}" for i in range(ncols)]

    # Parse numeric rows (only rows that are purely numeric)
    data_rows = []
    for line in filtered[data_start:]:
        if not _is_pure_numeric_row(line, delimiter):
            # Stop if you want strict “numeric block only”, or just skip footer junk.
            # Your requirement didn't mention footers; safest is "skip".
            continue

        parts = split_line(line, delimiter)
        if len(parts) != ncols:
            # If column count changes, skip this row
            continue

        row = [parse_float(p) for p in parts]
        # parse_float is guaranteed non-None here, but keep safe:
        row = [np.nan if v is None else v for v in row]
        data_rows.append(row)

    if not data_rows:
        raise ValueError("Failed to parse numeric data (no valid numeric rows)")

    data = np.array(data_rows, dtype=float)
    return DataFile(path, headers, data)
