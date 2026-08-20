import csv
import os
import tempfile

from openpyxl.workbook import Workbook

from src.data.models import Batch


class BatchExportService:
    @staticmethod
    def build_excel(batches: list[Batch]) -> tuple[str, str]:
        workbook = Workbook()

        worksheet = workbook.active
        worksheet.title = "Партии"

        worksheet.append(
            [
                "ID",
                "НомерПартии",
                "ДатаПартии",
                "СтатусЗакрытия",
                "РабочийЦентр",
                "Смена",
                "Бригада",
                "Номенклатура",
                "КодЕКН",
                "ДатаВремяНачалаСмены",
                "ДатаВремяОкончанияСмены",
            ]
        )

        for batch in batches:
            worksheet.append(
                [
                    batch.id,
                    batch.batch_number,
                    batch.batch_date.isoformat(),
                    batch.is_closed,
                    batch.work_center.name if batch.work_center else "",
                    batch.shift,
                    batch.team,
                    batch.nomenclature,
                    batch.ekn_code,
                    batch.shift_start.isoformat(),
                    batch.shift_end.isoformat(),
                ]
            )

        file_name = "batches_export.xlsx"

        file_path = os.path.join(
            tempfile.gettempdir(),
            file_name,
        )

        workbook.save(file_path)

        return file_path, file_name

    @staticmethod
    def build_csv(
        batches: list[Batch],
    ) -> tuple[str, str]:
        file_name = "batches_export.csv"

        file_path = os.path.join(
            tempfile.gettempdir(),
            file_name,
        )

        with open(
            file_path,
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            writer = csv.writer(file)

            writer.writerow(
                [
                    "ID",
                    "НомерПартии",
                    "ДатаПартии",
                    "СтатусЗакрытия",
                    "РабочийЦентр",
                    "Смена",
                    "Бригада",
                    "Номенклатура",
                    "КодЕКН",
                    "ДатаВремяНачалаСмены",
                    "ДатаВремяОкончанияСмены",
                ]
            )

            for batch in batches:
                writer.writerow(
                    [
                        batch.id,
                        batch.batch_number,
                        batch.batch_date.isoformat(),
                        batch.is_closed,
                        batch.work_center.name if batch.work_center else "",
                        batch.shift,
                        batch.team,
                        batch.nomenclature,
                        batch.ekn_code,
                        batch.shift_start.isoformat(),
                        batch.shift_end.isoformat(),
                    ]
                )

        return file_path, file_name
