import re
import os
import csv
import numpy as np
from Helpers import *

class DataFile:
    def __init__(self, path, headers, data):
        self.path = path
        self.headers = headers
        self.data = data

    def get_column(self, name):
        idx = self.headers.index(name)
        return self.data[:, idx]


def load_data_file(path):
    ext = os.path.splitext(path)[1].lower()

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    # Remove empty lines
    lines = [l.strip() for l in lines if l.strip()]

    # Remove comment lines
    comment_chars = ("#", "%", "//")
    data_lines = [l for l in lines if not l.startswith(comment_chars)]

    if not data_lines:
        raise ValueError("No data found in file")

    # Detect delimiter
    delimiter = detect_delimiter(data_lines[0])

    # Split first line
    first_row = split_line(data_lines[0], delimiter)

    # Header detection
    has_header = not all(is_number(x) for x in first_row)

    if has_header:
        headers = first_row
        data_start = 1
    else:
        ncols = len(first_row)
        headers = [f"col_{i}" for i in range(ncols)]
        data_start = 0

    data = []
    for line in data_lines[data_start:]:
        parts = split_line(line, delimiter)
        if len(parts) != len(headers):
            continue
        try:
            data.append([float(x.replace(",", ".")) for x in parts])
        except ValueError:
            continue

    if not data:
        raise ValueError("Failed to parse numeric data")

    return DataFile(path, headers, np.array(data))
