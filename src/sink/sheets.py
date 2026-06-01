import json
import os
import tempfile
from typing import List

import gspread
from google.oauth2.service_account import Credentials

from src import schema

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SHEET_TAB = "raw_tiktok"


def _get_client() -> gspread.Client:
    sa_json = os.environ["GOOGLE_SA_JSON"]
    sa_dict = json.loads(sa_json)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sa_dict, f)
        tmp_path = f.name
    creds = Credentials.from_service_account_file(tmp_path, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_or_create_worksheet(spreadsheet: gspread.Spreadsheet) -> gspread.Worksheet:
    try:
        ws = spreadsheet.worksheet(SHEET_TAB)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=SHEET_TAB, rows=1000, cols=len(schema.COLUMNS)
        )
        ws.append_row(schema.COLUMNS, value_input_option="RAW")
    return ws


def upsert(sheet_id: str, rows: List[schema.Row]) -> int:
    if not rows:
        return 0

    client = _get_client()
    spreadsheet = client.open_by_key(sheet_id)
    ws = _get_or_create_worksheet(spreadsheet)

    existing = ws.get_all_values()
    # Ensure header row exists
    if not existing or existing[0] != schema.COLUMNS:
        ws.insert_row(schema.COLUMNS, index=1)
        existing = ws.get_all_values()

    data_rows = existing[1:]  # skip header
    header_offset = 2         # 1-based sheet row where data starts

    # Build key -> sheet_row_index (1-based) from existing data
    key_to_sheet_row: dict[str, int] = {}
    for i, existing_row in enumerate(data_rows):
        padded = existing_row + [""] * (len(schema.COLUMNS) - len(existing_row))
        d = dict(zip(schema.COLUMNS, padded))
        row_key = (
            f"{d.get('date','')}|"
            f"{d.get('source','')}|"
            f"{d.get('advertiser_id','')}|"
            f"{d.get('level','')}|"
            f"{d.get('ad_id','')}|"
            f"{d.get('breakdown_value','')}"
        )
        if row_key and row_key != "|||||": 
            key_to_sheet_row[row_key] = header_offset + i

    update_requests = []
    new_rows = []

    for row in rows:
        row_values = row.to_list()
        key = row.key()
        if key in key_to_sheet_row:
            sheet_row = key_to_sheet_row[key]
            col_end = gspread.utils.rowcol_to_a1(sheet_row, len(schema.COLUMNS))
            col_start = gspread.utils.rowcol_to_a1(sheet_row, 1)
            update_requests.append({
                "range": f"{col_start}:{col_end}",
                "values": [row_values],
            })
        else:
            new_rows.append(row_values)

    written = 0
    if update_requests:
        ws.batch_update(update_requests, value_input_option="RAW")
        written += len(update_requests)
    if new_rows:
        ws.append_rows(new_rows, value_input_option="RAW")
        written += len(new_rows)

    return written
