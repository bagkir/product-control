import os
import tempfile
import uuid

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build_batch_pdf_report(batch) -> tuple[str, str]:
    """
    Строит PDF-отчёт по партии: инфо о партии, статистика, график
    аггрегации по времени, полный список продукции.

    Ожидает batch с eager-loaded products и work_center (тот же объект,
    что get_full_for_report отдаёт в generate_batch_report).
    Возвращает (путь_к_файлу, имя_файла).
    """
    file_name = f"batch_{batch.id}_report.pdf"
    file_path = os.path.join(tempfile.gettempdir(), file_name)

    chart_path = _build_aggregation_chart(batch)

    try:
        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
        )
        styles = getSampleStyleSheet()
        elements = []

        elements.append(
            Paragraph(f"Отчёт по партии №{batch.batch_number}", styles["Title"])
        )
        elements.append(Spacer(1, 0.5 * cm))

        # --- Информация о партии ---
        info_rows = [
            ["Номер партии", str(batch.batch_number)],
            ["Дата партии", batch.batch_date.isoformat()],
            ["Статус", "Закрыта" if batch.is_closed else "Открыта"],
            ["Рабочий центр", batch.work_center.name if batch.work_center else ""],
            ["Смена", batch.shift],
            ["Бригада", batch.team],
            ["Номенклатура", batch.nomenclature],
            ["Начало смены", batch.shift_start.strftime("%Y-%m-%d %H:%M:%S")],
            ["Окончание смены", batch.shift_end.strftime("%Y-%m-%d %H:%M:%S")],
        ]
        info_table = Table(info_rows, colWidths=[5 * cm, 10 * cm])
        info_table.setStyle(_default_table_style())
        elements.append(info_table)
        elements.append(Spacer(1, 0.7 * cm))

        # --- Статистика ---
        total = len(batch.products)
        aggregated = sum(1 for p in batch.products if p.is_aggregated)
        remaining = total - aggregated
        rate = (aggregated / total * 100) if total else 0.0

        elements.append(Paragraph("Статистика", styles["Heading2"]))
        stats_rows = [
            ["Всего продукции", str(total)],
            ["Аггрегировано", str(aggregated)],
            ["Осталось", str(remaining)],
            ["Процент выполнения", f"{rate:.1f}%"],
        ]
        stats_table = Table(stats_rows, colWidths=[5 * cm, 10 * cm])
        stats_table.setStyle(_default_table_style())
        elements.append(stats_table)
        elements.append(Spacer(1, 0.7 * cm))

        # --- График аггрегации по времени ---
        if chart_path:
            elements.append(Paragraph("Аггрегация по времени", styles["Heading2"]))
            elements.append(Image(chart_path, width=16 * cm, height=8 * cm))
            elements.append(Spacer(1, 0.7 * cm))
        else:
            elements.append(
                Paragraph(
                    "Аггрегированной продукции пока нет — график недоступен.",
                    styles["Normal"],
                )
            )
            elements.append(Spacer(1, 0.7 * cm))

        # --- Продукция ---
        elements.append(Paragraph("Продукция", styles["Heading2"]))
        product_rows = [["ID", "Уникальный код", "Аггрегирована", "Дата аггрегации"]]
        for product in batch.products:
            product_rows.append(
                [
                    str(product.id),
                    product.unique_code,
                    "Да" if product.is_aggregated else "Нет",
                    (
                        product.aggregated_at.strftime("%Y-%m-%d %H:%M:%S")
                        if product.aggregated_at
                        else "-"
                    ),
                ]
            )

        products_table = Table(
            product_rows,
            colWidths=[2 * cm, 6 * cm, 3 * cm, 5 * cm],
            repeatRows=1,
        )
        products_table.setStyle(_default_table_style(header=True))
        elements.append(products_table)

        doc.build(elements)
    finally:
        if chart_path and os.path.exists(chart_path):
            os.remove(chart_path)

    return file_path, file_name


def _build_aggregation_chart(batch) -> str | None:
    """
    Кумулятивный график количества аггрегированной продукции по времени.
    Возвращает путь к PNG, либо None, если аггрегированных продуктов ещё нет.
    """
    aggregated_products = sorted(
        (p for p in batch.products if p.aggregated_at is not None),
        key=lambda p: p.aggregated_at,
    )

    if not aggregated_products:
        return None

    timestamps = [p.aggregated_at for p in aggregated_products]
    cumulative = list(range(1, len(timestamps) + 1))

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(timestamps, cumulative, marker="o", markersize=3, linewidth=1.5)
    ax.set_xlabel("Время")
    ax.set_ylabel("Аггрегировано (накопительно)")
    ax.set_title("Динамика аггрегации продукции")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()

    chart_path = os.path.join(
        tempfile.gettempdir(), f"chart_{batch.id}_{uuid.uuid4().hex}.png"
    )
    fig.savefig(chart_path, dpi=120)
    plt.close(fig)

    return chart_path


def _default_table_style(header: bool = False) -> TableStyle:
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E4053")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    else:
        style += [
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F3F4")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ]
    return TableStyle(style)
