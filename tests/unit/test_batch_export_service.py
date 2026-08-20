from datetime import date, datetime, timezone
from unittest.mock import MagicMock
import csv
from openpyxl import load_workbook

from src.domain.services.batch_export_service import BatchExportService


def make_export_batch():
    batch = MagicMock()

    batch.id = 1
    batch.batch_number = 22222
    batch.batch_date = date(2026, 8, 18)
    batch.is_closed = False

    batch.work_center.name = "Цех №1"

    batch.shift = "1 смена"
    batch.team = "Бригада Иванова"
    batch.nomenclature = "Болт М10"
    batch.ekn_code = "EKN-123"

    batch.shift_start = datetime(2026, 8, 18, 8, 0, tzinfo=timezone.utc)
    batch.shift_end = datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc)

    return batch


def test_build_excel():
    batch = make_export_batch()

    file_path, file_name = BatchExportService.build_excel([batch])

    assert file_name == "batches_export.xlsx"

    workbook = load_workbook(file_path)

    sheet = workbook["Партии"]

    assert sheet["A1"].value == "ID"
    assert sheet["B1"].value == "НомерПартии"

    assert sheet["A2"].value == 1
    assert sheet["B2"].value == 22222
    assert sheet["E2"].value == "Цех №1"


def test_build_csv():
    batch = make_export_batch()

    file_path, file_name = BatchExportService.build_csv([batch])

    assert file_name == "batches_export.csv"

    with open(
        file_path,
        encoding="utf-8-sig",
        newline="",
    ) as file:
        rows = list(csv.reader(file))

    assert rows[0][0] == "ID"
    assert rows[0][1] == "НомерПартии"

    assert rows[1][0] == "1"
    assert rows[1][1] == "22222"
