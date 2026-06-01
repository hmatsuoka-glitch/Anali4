import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gspread
from src.sink.sheets import upsert
from src import schema


def make_row(date="2024-01-15", ad_id="111", spend=100.0, breakdown_value=""):
    return schema.Row(
        date=date,
        source="tiktok",
        advertiser_id="7613640650042425345",
        advertiser_name="テスト",
        level="ad",
        ad_id=ad_id,
        spend=spend,
        breakdown_value=breakdown_value,
    )


@pytest.fixture
def mock_gc_ws():
    gc = MagicMock()
    wb = MagicMock()
    ws = MagicMock()
    gc.open_by_key.return_value = wb
    wb.worksheet.return_value = ws
    return gc, wb, ws


@patch("src.sink.sheets._get_client")
def test_upsert_append_new_rows(mock_get_client, mock_gc_ws):
    gc, wb, ws = mock_gc_ws
    mock_get_client.return_value = gc
    ws.get_all_values.return_value = [schema.COLUMNS]

    row = make_row()
    result = upsert("fake-sheet-id", [row])

    assert result == 1
    ws.append_rows.assert_called_once()
    ws.batch_update.assert_not_called()


@patch("src.sink.sheets._get_client")
def test_upsert_update_existing_row(mock_get_client, mock_gc_ws):
    gc, wb, ws = mock_gc_ws
    mock_get_client.return_value = gc

    existing = make_row(spend=50.0)
    ws.get_all_values.return_value = [schema.COLUMNS, existing.to_list()]

    updated = make_row(spend=200.0)
    result = upsert("fake-sheet-id", [updated])

    assert result == 1
    ws.batch_update.assert_called_once()
    ws.append_rows.assert_not_called()


@patch("src.sink.sheets._get_client")
def test_upsert_no_duplicate_on_second_run(mock_get_client, mock_gc_ws):
    gc, wb, ws = mock_gc_ws
    mock_get_client.return_value = gc

    row = make_row()
    ws.get_all_values.return_value = [schema.COLUMNS, row.to_list()]

    result = upsert("fake-sheet-id", [row])

    assert result == 1
    ws.batch_update.assert_called_once()
    ws.append_rows.assert_not_called()


@patch("src.sink.sheets._get_client")
def test_upsert_empty_rows(mock_get_client, mock_gc_ws):
    gc, wb, ws = mock_gc_ws
    mock_get_client.return_value = gc

    result = upsert("fake-sheet-id", [])

    assert result == 0
    gc.open_by_key.assert_not_called()


@patch("src.sink.sheets._get_client")
def test_upsert_creates_sheet_if_not_found(mock_get_client, mock_gc_ws):
    gc, wb, ws = mock_gc_ws
    mock_get_client.return_value = gc
    wb.worksheet.side_effect = gspread.exceptions.WorksheetNotFound
    new_ws = MagicMock()
    wb.add_worksheet.return_value = new_ws
    new_ws.get_all_values.return_value = [schema.COLUMNS]

    row = make_row()
    upsert("fake-sheet-id", [row])

    wb.add_worksheet.assert_called_once()
    new_ws.append_row.assert_called_once_with(schema.COLUMNS, value_input_option="RAW")


@patch("src.sink.sheets._get_client")
def test_upsert_mixed_update_and_append(mock_get_client, mock_gc_ws):
    gc, wb, ws = mock_gc_ws
    mock_get_client.return_value = gc

    existing_row = make_row(ad_id="111")
    ws.get_all_values.return_value = [schema.COLUMNS, existing_row.to_list()]

    updated = make_row(ad_id="111", spend=999.0)
    new_row = make_row(ad_id="999")
    result = upsert("fake-sheet-id", [updated, new_row])

    assert result == 2
    ws.batch_update.assert_called_once()
    ws.append_rows.assert_called_once()
