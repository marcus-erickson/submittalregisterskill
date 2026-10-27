"""Output and input adapters for the register.

Each adapter module has:
    write(register, out_path, layout) -> (item_count, flagged_count)
    read(path, layout) -> register          (optional: sheets has no reader)

To support a new format, add a module here with those functions and one line below.
"""
from adapters import csv_adapter, json_adapter, sheets_adapter, xlsx_adapter

ADAPTERS = {
    "xlsx": xlsx_adapter,
    "csv": csv_adapter,
    "json": json_adapter,
    "sheets": sheets_adapter,
}
EXTENSIONS = {".xlsx": "xlsx", ".xlsm": "xlsx", ".csv": "csv", ".json": "json"}
