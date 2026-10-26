# -*- coding: utf-8 -*-
"""ConsultFlow — учебный аналитический дашборд по заказам на консалтинговые услуги.

Этап 3: загрузка CSV, фильтры, карточки, графики и таблица.
"""

from __future__ import annotations

import base64
import io

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dash_table, dcc, html

APP_TITLE = "ConsultFlow — аналитика заказов"
APP_DESCRIPTION = (
    "Анализ заказов на консалтинговые услуги, полученных оплат и расходов"
)

BG = "#f4f6f9"
CARD = "#ffffff"
ACCENT = "#1f5fbf"
TEXT = "#1f2937"
MUTED = "#6b7280"
BORDER = "#dde3ec"

PAGE_STYLE = {
    "minHeight": "100vh",
    "backgroundColor": BG,
    "color": TEXT,
    "fontFamily": "Segoe UI, Arial, sans-serif",
    "padding": "24px 16px 40px",
    "boxSizing": "border-box",
}
CONTAINER_STYLE = {"maxWidth": "1240px", "margin": "0 auto"}
CARD_STYLE = {
    "backgroundColor": CARD,
    "border": f"1px solid {BORDER}",
    "borderRadius": "12px",
    "padding": "18px 20px",
    "boxShadow": "0 1px 3px rgba(15, 23, 42, 0.06)",
}
SECTION_TITLE_STYLE = {
    "fontSize": "17px",
    "fontWeight": "600",
    "margin": "0 0 12px 0",
}
MUTED_STYLE = {"color": MUTED, "fontSize": "13px", "lineHeight": "1.5"}

TABLE_COLUMNS = [
    {"name": "Номер", "id": "order_id"},
    {"name": "Дата заявки", "id": "created_date"},
    {"name": "Клиент", "id": "client"},
    {"name": "Направление", "id": "practice"},
    {"name": "Менеджер", "id": "manager"},
    {"name": "Статус", "id": "status"},
    {"name": "Стоимость, ₽", "id": "amount", "type": "numeric", "format": {"specifier": ",.0f"}},
    {"name": "Полученная оплата, ₽", "id": "paid_amount", "type": "numeric", "format": {"specifier": ",.0f"}},
    {"name": "Расходы, ₽", "id": "expenses", "type": "numeric", "format": {"specifier": ",.0f"}},
    {"name": "Финансовый результат, ₽", "id": "profit", "type": "numeric", "format": {"specifier": ",.0f"}},
]

ALL_PRACTICES = "Все направления"
REQUIRED_COLUMNS = [
    "order_id",
    "created_date",
    "client",
    "practice",
    "manager",
    "status",
    "amount",
    "paid_amount",
    "expenses",
]
TEXT_COLUMNS = ["order_id", "client", "practice", "manager", "status"]
NUMERIC_COLUMNS = ["amount", "paid_amount", "expenses"]
MAX_FILE_SIZE = 5 * 1024 * 1024


def message_box(text: str, kind: str = "info") -> html.Div:
    """Короткое сообщение пользователю вместо traceback."""
    palette = {
        "info": ("#eef3fb", "#1f5fbf"),
        "ok": ("#e8f5e9", "#1b5e20"),
        "error": ("#fdecea", "#b71c1c"),
    }
    background, color = palette.get(kind, palette["info"])
    return html.Div(
        text,
        style={
            "backgroundColor": background,
            "color": color,
            "borderRadius": "8px",
            "padding": "10px 12px",
            "fontSize": "13px",
            "lineHeight": "1.5",
        },
    )


def _row_numbers(indexes) -> str:
    """Номера строк CSV (с учётом заголовка) для сообщения об ошибке."""
    numbers = sorted({int(index) + 2 for index in indexes})
    shown = ", ".join(str(number) for number in numbers[:10])
    if len(numbers) > 10:
        shown += f" и ещё {len(numbers) - 10}"
    return shown


def _decode_csv(contents: str) -> str:
    """Декодировать содержимое dcc.Upload в текст."""
    if not contents:
        raise ValueError("Файл не получен. Выберите CSV-файл и повторите загрузку.")
    try:
        _, encoded = contents.split(",", 1)
        raw = base64.b64decode(encoded)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            "Не удалось прочитать содержимое файла. Выберите CSV-файл повторно."
        ) from exc
    if not raw.strip():
        raise ValueError("Файл пуст. Загрузите CSV-файл с заказами.")
    if len(raw) > MAX_FILE_SIZE:
        raise ValueError(
            "Файл больше 5 МБ. Для учебного дашборда загрузите файл меньшего размера."
        )
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(
        "Не удалось определить кодировку файла. Сохраните CSV в UTF-8 "
        "(подходит также Windows-1251)."
    )


def read_orders_csv(contents: str) -> pd.DataFrame:
    """Прочитать и проверить CSV. При ошибке выбрасывает ValueError.

    Некорректные данные не исправляются молча: пользователь получает
    сообщение с номерами строк.
    """
    text = _decode_csv(contents)
    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    except Exception as exc:  # noqa: BLE001 - сообщение важнее типа исключения
        raise ValueError(
            "Не удалось разобрать CSV. Проверьте, что используется обычный CSV "
            "с разделителем «запятая» и одной строкой заголовка."
        ) from exc

    df.columns = [str(column).strip() for column in df.columns]
    if df.empty:
        raise ValueError(
            "В файле нет строк с заказами. Добавьте данные под строкой заголовка."
        )
    if len(df.columns) == 1 and ";" in df.columns[0]:
        raise ValueError(
            "Похоже, в файле разделитель «точка с запятой». Сохраните CSV "
            "с разделителем «запятая» и повторите загрузку."
        )

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            "В файле отсутствуют обязательные столбцы: "
            + ", ".join(missing)
            + ". Ожидаемые столбцы: "
            + ", ".join(REQUIRED_COLUMNS)
            + "."
        )

    df = df[REQUIRED_COLUMNS].copy()
    for column in TEXT_COLUMNS:
        df[column] = df[column].astype("string").str.strip().fillna("")

    blank_rows = df.index[(df[TEXT_COLUMNS] == "").any(axis=1)]
    if len(blank_rows):
        raise ValueError(
            "Пустые значения в обязательных столбцах в строках CSV: "
            f"{_row_numbers(blank_rows)}. Заполните номер, клиента, направление, "
            "менеджера и статус."
        )

    raw_dates = df["created_date"].astype("string").str.strip()
    wrong_format = df.index[~raw_dates.fillna("").str.fullmatch(r"\d{4}-\d{2}-\d{2}")]
    if len(wrong_format):
        raise ValueError(
            f"Некорректная дата в строках CSV: {_row_numbers(wrong_format)}. "
            "Ожидается формат ГГГГ-ММ-ДД, например 2025-03-14."
        )

    parsed_dates = pd.to_datetime(raw_dates, format="%Y-%m-%d", errors="coerce")
    invalid_dates = df.index[parsed_dates.isna()]
    if len(invalid_dates):
        raise ValueError(
            f"Некорректная дата в строках CSV: {_row_numbers(invalid_dates)}. "
            "Проверьте календарные даты в формате ГГГГ-ММ-ДД."
        )
    df["created_date"] = parsed_dates

    for column in NUMERIC_COLUMNS:
        values = pd.to_numeric(df[column], errors="coerce")
        invalid = df.index[values.isna()]
        if len(invalid):
            raise ValueError(
                f"Некорректное число в столбце «{column}» в строках CSV: "
                f"{_row_numbers(invalid)}. Укажите число без пробелов и текста, "
                "например 250000."
            )
        negative = df.index[values < 0]
        if len(negative):
            raise ValueError(
                f"Отрицательные суммы в столбце «{column}» в строках CSV: "
                f"{_row_numbers(negative)}. Суммы не могут быть отрицательными."
            )
        df[column] = values.astype(float)

    overpaid = df.index[df["paid_amount"] > df["amount"]]
    if len(overpaid):
        raise ValueError(
            "Полученная оплата превышает стоимость заказа в строках CSV: "
            f"{_row_numbers(overpaid)}. Проверьте столбцы amount и paid_amount."
        )

    duplicates = df.loc[df["order_id"].duplicated(keep=False), "order_id"]
    if len(duplicates):
        ids = ", ".join(sorted(set(duplicates))[:10])
        raise ValueError(
            "Повторяющиеся номера заказов (order_id): "
            f"{ids}. Номер заказа должен быть уникальным."
        )

    df["profit"] = df["paid_amount"] - df["expenses"]
    return df.sort_values(["created_date", "order_id"]).reset_index(drop=True)


def dataframe_to_records(df: pd.DataFrame) -> list[dict]:
    """Преобразовать DataFrame в JSON-совместимые записи для dcc.Store."""
    records = []
    for row in df.itertuples(index=False):
        records.append(
            {
                "order_id": str(row.order_id),
                "created_date": row.created_date.strftime("%Y-%m-%d"),
                "client": str(row.client),
                "practice": str(row.practice),
                "manager": str(row.manager),
                "status": str(row.status),
                "amount": float(row.amount),
                "paid_amount": float(row.paid_amount),
                "expenses": float(row.expenses),
                "profit": float(row.profit),
            }
        )
    return records


def format_money(value: float) -> str:
    """Сумма в рублях с разделением тысяч пробелом."""
    return f"{value:,.0f}".replace(",", " ") + " ₽"


def format_date(value) -> str:
    """Дата из ISO-строки в формат ДД.ММ.ГГГГ."""
    return pd.Timestamp(value).strftime("%d.%m.%Y")


def records_to_frame(records: list[dict]) -> pd.DataFrame:
    """Собрать DataFrame из записей dcc.Store."""
    df = pd.DataFrame(records)
    df["created_date"] = pd.to_datetime(df["created_date"], format="%Y-%m-%d")
    for column in [*NUMERIC_COLUMNS, "profit"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)
    return df


def filter_orders(
    df: pd.DataFrame, start_date, end_date, practice
) -> pd.DataFrame:
    """Отфильтровать заказы по диапазону дат и направлению."""
    filtered = df
    if start_date:
        filtered = filtered[filtered["created_date"] >= pd.Timestamp(start_date)]
    if end_date:
        filtered = filtered[filtered["created_date"] <= pd.Timestamp(end_date)]
    if practice and practice != ALL_PRACTICES:
        filtered = filtered[filtered["practice"] == practice]
    return filtered


def line_figure(df: pd.DataFrame) -> dict:
    """Оплата и расходы по месяцам регистрации заказов."""
    months = df["created_date"].dt.to_period("M").dt.to_timestamp()
    grouped = (
        df.groupby(months)[["paid_amount", "expenses"]]
        .sum()
        .reset_index(names="month")
    )
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=grouped["month"],
            y=grouped["paid_amount"],
            mode="lines+markers",
            name="Полученная оплата",
            line={"color": ACCENT, "width": 3},
            marker={"size": 7},
            hovertemplate="%{x|%m.%Y}<br>Оплата: %{y:,.0f} ₽<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=grouped["month"],
            y=grouped["expenses"],
            mode="lines+markers",
            name="Расходы",
            line={"color": "#d97706", "width": 3},
            marker={"size": 7},
            hovertemplate="%{x|%m.%Y}<br>Расходы: %{y:,.0f} ₽<extra></extra>",
        )
    )
    figure.update_layout(
        template="plotly_white",
        margin={"l": 60, "r": 20, "t": 30, "b": 40},
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        xaxis={"tickformat": "%m.%Y", "dtick": "M1", "title": None},
        yaxis={
            "tickformat": ",.0f",
            "ticksuffix": " ₽",
            "rangemode": "tozero",
            "title": None,
        },
    )
    return figure


def pie_figure(df: pd.DataFrame) -> dict:
    """Структура расходов по направлениям."""
    expenses = df.groupby("practice")["expenses"].sum()
    expenses = expenses[expenses > 0]
    if expenses.empty:
        return empty_figure("Расходы по выбранным заказам не учитывались")
    figure = go.Figure(
        go.Pie(
            labels=expenses.index,
            values=expenses.values,
            hole=0.35,
            textinfo="percent",
            hovertemplate="%{label}<br>%{value:,.0f} ₽<extra></extra>",
        )
    )
    figure.update_layout(
        template="plotly_white",
        margin={"l": 20, "r": 20, "t": 30, "b": 60},
        legend={"orientation": "h", "yanchor": "top", "y": -0.1, "x": 0},
    )
    return figure


def bar_figure(df: pd.DataFrame) -> dict:
    """Финансовый результат по направлениям."""
    profits = df.groupby("practice")["profit"].sum().sort_values()
    colors = ["#c62828" if value < 0 else "#2e7d32" for value in profits.values]
    figure = go.Figure(
        go.Bar(
            x=profits.index,
            y=profits.values,
            marker_color=colors,
            text=[format_money(value) for value in profits.values],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}<br>Результат: %{y:,.0f} ₽<extra></extra>",
        )
    )
    figure.update_layout(
        template="plotly_white",
        margin={"l": 60, "r": 20, "t": 40, "b": 60},
        xaxis={"title": None},
        yaxis={
            "tickformat": ",.0f",
            "ticksuffix": " ₽",
            "title": None,
            "zeroline": True,
            "zerolinecolor": BORDER,
        },
    )
    return figure


def empty_figure(message: str) -> dict:
    """Пустой график с поясняющей подписью вместо осей."""
    return {
        "data": [],
        "layout": {
            "template": "plotly_white",
            "margin": {"l": 40, "r": 20, "t": 60, "b": 40},
            "xaxis": {"visible": False},
            "yaxis": {"visible": False},
            "annotations": [
                {
                    "text": message,
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 14, "color": MUTED},
                }
            ],
        },
    }


def kpi_card(title: str, value_id: str, hint: str) -> html.Div:
    """Карточка показателя."""
    return html.Div(
        style={**CARD_STYLE, "flex": "1 1 220px", "minWidth": "200px"},
        children=[
            html.Div(title, style={"fontSize": "13px", "color": MUTED}),
            html.Div(
                "—",
                id=value_id,
                style={
                    "fontSize": "26px",
                    "fontWeight": "700",
                    "color": TEXT,
                    "margin": "6px 0 4px",
                },
            ),
            html.Div(hint, style={"fontSize": "12px", "color": MUTED}),
        ],
    )


def chart_card(title: str, graph_id: str) -> html.Div:
    """Карточка с графиком."""
    return html.Div(
        style={**CARD_STYLE, "flex": "1 1 460px", "minWidth": "300px"},
        children=[
            html.Div(title, style=SECTION_TITLE_STYLE),
            dcc.Graph(
                id=graph_id,
                figure=empty_figure("Загрузите CSV-файл, чтобы построить график"),
                config={"displayModeBar": False, "responsive": True},
                style={"height": "380px"},
            ),
        ],
    )


app = Dash(__name__, title=APP_TITLE)
server = app.server

app.layout = html.Div(
    style=PAGE_STYLE,
    children=[
        html.Div(
            style=CONTAINER_STYLE,
            children=[
                # Заголовок
                html.Div(
                    style={"marginBottom": "20px"},
                    children=[
                        html.H1(
                            APP_TITLE,
                            style={"fontSize": "28px", "margin": "0 0 6px 0"},
                        ),
                        html.P(
                            APP_DESCRIPTION,
                            style={**MUTED_STYLE, "fontSize": "15px", "margin": "0"},
                        ),
                    ],
                ),
                # Хранилище загруженных данных в сессии страницы
                dcc.Store(id="orders-store", storage_type="session"),
                # Загрузка файла
                html.Div(
                    style={**CARD_STYLE, "marginBottom": "16px"},
                    children=[
                        html.Div("Загрузка данных", style=SECTION_TITLE_STYLE),
                        dcc.Upload(
                            id="upload-data",
                            accept=".csv",
                            multiple=False,
                            children=html.Div(
                                [
                                    html.Div(
                                        "Перетащите CSV-файл сюда или нажмите для выбора",
                                        style={"fontWeight": "600", "color": ACCENT},
                                    ),
                                    html.Div(
                                        "Формат: CSV с разделителем «запятая», "
                                        "кодировка UTF-8 (допускается Windows-1251). "
                                        "Одна строка — один заказ.",
                                        style={**MUTED_STYLE, "marginTop": "4px"},
                                    ),
                                ]
                            ),
                            style={
                                "border": f"2px dashed {ACCENT}",
                                "borderRadius": "10px",
                                "padding": "22px",
                                "textAlign": "center",
                                "cursor": "pointer",
                                "backgroundColor": "#f8faff",
                            },
                        ),
                        html.Div(
                            id="upload-message",
                            children=message_box(
                                "CSV ещё не загружен. Выберите файл dashboard/orders.csv "
                                "или другой файл в описанном формате — все показатели "
                                "будут рассчитаны по загруженным данным."
                            ),
                            style={"marginTop": "10px"},
                        ),
                    ],
                ),
                # Фильтры
                html.Div(
                    style={
                        **CARD_STYLE,
                        "marginBottom": "16px",
                        "display": "flex",
                        "flexWrap": "wrap",
                        "gap": "18px",
                        "alignItems": "flex-end",
                    },
                    children=[
                        html.Div(
                            style={"flex": "1 1 320px", "minWidth": "260px"},
                            children=[
                                html.Div(
                                    "Диапазон дат регистрации заявок",
                                    style={**SECTION_TITLE_STYLE, "fontSize": "14px"},
                                ),
                                dcc.DatePickerRange(
                                    id="date-range",
                                    display_format="DD.MM.YYYY",
                                    clearable=False,
                                    disabled=True,
                                ),
                            ],
                        ),
                        html.Div(
                            style={"flex": "1 1 260px", "minWidth": "240px"},
                            children=[
                                html.Div(
                                    "Направление консалтинга",
                                    style={**SECTION_TITLE_STYLE, "fontSize": "14px"},
                                ),
                                dcc.Dropdown(
                                    id="practice-filter",
                                    options=[
                                        {
                                            "label": ALL_PRACTICES,
                                            "value": ALL_PRACTICES,
                                        }
                                    ],
                                    value=ALL_PRACTICES,
                                    clearable=False,
                                    disabled=True,
                                ),
                            ],
                        ),
                    ],
                ),
                # Карточки показателей
                html.Div(
                    style={
                        "display": "flex",
                        "flexWrap": "wrap",
                        "gap": "16px",
                        "marginBottom": "16px",
                    },
                    children=[
                        kpi_card("Количество заказов", "kpi-orders", "шт."),
                        kpi_card(
                            "Полученная оплата",
                            "kpi-paid",
                            "фактически получено, ₽",
                        ),
                        kpi_card("Расходы", "kpi-expenses", "учтённые расходы, ₽"),
                        kpi_card(
                            "Финансовый результат",
                            "kpi-profit",
                            "оплата минус расходы, ₽",
                        ),
                    ],
                ),
                # Графики
                html.Div(
                    style={
                        "display": "flex",
                        "flexWrap": "wrap",
                        "gap": "16px",
                        "marginBottom": "16px",
                    },
                    children=[
                        chart_card(
                            "Оплата и расходы по месяцам регистрации заказов",
                            "chart-line",
                        ),
                        chart_card(
                            "Структура расходов по направлениям",
                            "chart-pie",
                        ),
                    ],
                ),
                html.Div(
                    style={**CARD_STYLE, "marginBottom": "16px"},
                    children=[
                        html.Div(
                            "Финансовый результат по направлениям",
                            style=SECTION_TITLE_STYLE,
                        ),
                        dcc.Graph(
                            id="chart-bar",
                            figure=empty_figure(
                                "Загрузите CSV-файл, чтобы построить график"
                            ),
                            config={"displayModeBar": False, "responsive": True},
                            style={"height": "340px"},
                        ),
                    ],
                ),
                # Таблица заказов
                html.Div(
                    style=CARD_STYLE,
                    children=[
                        html.Div("Заказы", style=SECTION_TITLE_STYLE),
                        html.Div(
                            "После загрузки файла здесь появится таблица с "
                            "сортировкой и постраничным выводом.",
                            id="table-hint",
                            style={**MUTED_STYLE, "marginBottom": "8px"},
                        ),
                        dash_table.DataTable(
                            id="orders-table",
                            columns=TABLE_COLUMNS,
                            data=[],
                            sort_action="native",
                            page_action="native",
                            page_size=10,
                            style_table={"overflowX": "auto"},
                            style_cell={
                                "fontFamily": "Segoe UI, Arial, sans-serif",
                                "fontSize": "13px",
                                "padding": "8px 10px",
                                "textAlign": "left",
                                "whiteSpace": "normal",
                                "height": "auto",
                            },
                            style_header={
                                "backgroundColor": "#eef3fb",
                                "fontWeight": "600",
                                "border": f"1px solid {BORDER}",
                            },
                            style_data={"border": f"1px solid {BORDER}"},
                            style_data_conditional=[
                                {
                                    "if": {
                                        "filter_query": "{profit} < 0",
                                        "column_id": "profit",
                                    },
                                    "color": "#b71c1c",
                                    "fontWeight": "600",
                                },
                                {
                                    "if": {
                                        "filter_query": "{profit} >= 0",
                                        "column_id": "profit",
                                    },
                                    "color": "#1b5e20",
                                },
                            ],
                        ),
                    ],
                ),
                html.P(
                    "Учебный проект. Финансовый результат рассчитан как "
                    "«полученная оплата − расходы» и не является бухгалтерской "
                    "прибылью.",
                    style={**MUTED_STYLE, "marginTop": "16px"},
                ),
            ],
        )
    ],
)


@app.callback(
    Output("orders-store", "data"),
    Output("date-range", "min_date_allowed"),
    Output("date-range", "max_date_allowed"),
    Output("date-range", "start_date"),
    Output("date-range", "end_date"),
    Output("date-range", "disabled"),
    Output("practice-filter", "options"),
    Output("practice-filter", "value"),
    Output("practice-filter", "disabled"),
    Output("upload-message", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    prevent_initial_call=True,
)
def handle_upload(contents, filename):
    """Загрузить CSV, проверить его и сбросить фильтры под новый файл."""
    all_options = [{"label": ALL_PRACTICES, "value": ALL_PRACTICES}]

    def fail(text: str):
        # Данные предыдущего файла не остаются активными.
        return (
            None,
            None,
            None,
            None,
            None,
            True,
            all_options,
            ALL_PRACTICES,
            True,
            message_box(text, "error"),
        )

    if not contents:
        return fail("Файл не выбран. Нажмите на область загрузки и выберите CSV.")

    try:
        df = read_orders_csv(contents)
    except ValueError as exc:
        return fail(f"Ошибка в CSV: {exc}")
    except Exception:  # noqa: BLE001 - пользователю не показываем traceback
        return fail(
            "Не удалось обработать файл. Проверьте формат CSV и повторите загрузку."
        )

    min_date = df["created_date"].min().strftime("%Y-%m-%d")
    max_date = df["created_date"].max().strftime("%Y-%m-%d")
    practices = sorted(df["practice"].unique().tolist())
    store = {
        "records": dataframe_to_records(df),
        "practices": practices,
        "filename": filename or "orders.csv",
        "rows": len(df),
        "min_date": min_date,
        "max_date": max_date,
    }
    message = message_box(
        f"Файл «{filename or 'orders.csv'}» загружен: {len(df)} заказов, "
        f"период {format_date(min_date)} — {format_date(max_date)}. "
        "Данные проверены, фильтры сброшены на диапазон нового файла.",
        "ok",
    )
    return (
        store,
        min_date,
        max_date,
        min_date,
        max_date,
        False,
        all_options
        + [{"label": practice, "value": practice} for practice in practices],
        ALL_PRACTICES,
        False,
        message,
    )


EMPTY_CARDS = ("—", "—", "—", "—")


@app.callback(
    Output("kpi-orders", "children"),
    Output("kpi-paid", "children"),
    Output("kpi-expenses", "children"),
    Output("kpi-profit", "children"),
    Output("chart-line", "figure"),
    Output("chart-pie", "figure"),
    Output("chart-bar", "figure"),
    Output("orders-table", "data"),
    Output("orders-table", "page_current"),
    Output("table-hint", "children"),
    Input("orders-store", "data"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("practice-filter", "value"),
)
def update_dashboard(store, start_date, end_date, practice):
    """Пересчитать карточки, графики и таблицу по загруженным данным."""
    if not store or not store.get("records"):
        message = "Загрузите CSV-файл, чтобы построить график"
        return (
            *EMPTY_CARDS,
            empty_figure(message),
            empty_figure(message),
            empty_figure(message),
            [],
            0,
            "Загрузите CSV-файл, чтобы увидеть заказы.",
        )

    df = records_to_frame(store["records"])
    filtered = filter_orders(df, start_date, end_date, practice)
    if filtered.empty:
        message = "Нет заказов за выбранный период и направление"
        return (
            "0",
            "0 ₽",
            "0 ₽",
            "0 ₽",
            empty_figure(message),
            empty_figure(message),
            empty_figure(message),
            [],
            0,
            "За выбранный период заказов нет. Измените диапазон дат "
            "или направление консалтинга.",
        )

    hint = (
        f"Показано {len(filtered)} из {len(df)} заказов. "
        "Сортировка — по клику на заголовок столбца."
    )
    return (
        f"{len(filtered)}",
        format_money(filtered["paid_amount"].sum()),
        format_money(filtered["expenses"].sum()),
        format_money(filtered["profit"].sum()),
        line_figure(filtered),
        pie_figure(filtered),
        bar_figure(filtered),
        dataframe_to_records(filtered),
        0,
        hint,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=False)

