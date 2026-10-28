"""Read a register from any supported file: reviewed or draft CSV, register .xlsx, register .csv or register .json."""
import csv
import os

import columns as colmod
import register_model as model
from adapters import ADAPTERS


def input_kind(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        return "xlsx"
    if ext == ".json":
        return "json"
    with open(path, newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh), [])
    # extraction CSVs use snake_case names; a register export uses the layout headers
    return "extraction" if "section" in header and "description" in header or "requirement" in header else "csv"


def load_input(path, layout=None, keep_div01=False):
    """Return a register dict (rules plus items). Raises ValueError with a readable message."""
    layout = layout or colmod.load(None)
    kind = input_kind(path)
    if kind == "extraction":
        return model.new_register(items=model.load_rows(path, keep_div01))
    return ADAPTERS["csv" if kind == "csv" else kind].read(path, layout)
