# -*- coding: utf-8 -*-
"""ConsultFlow — учебный аналитический дашборд по заказам на консалтинговые услуги.

Этап 1: структура страницы и запускаемая базовая разметка.
Загрузка CSV, фильтры и графики добавляются на следующих этапах.
"""

from dash import Dash, dash_table, dcc, html

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
    {"name": "Стоимость, ₽", "id": "amount", "type": "numeric"},
    {"name": "Полученная оплата, ₽", "id": "paid_amount", "type": "numeric"},
    {"name": "Расходы, ₽", "id": "expenses", "type": "numeric"},
    {"name": "Финансовый результат, ₽", "id": "profit", "type": "numeric"},
]


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
                                        "кодировка UTF-8. Одна строка — один заказ.",
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
                        html.Div(id="upload-message", style={"marginTop": "10px"}),
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
                                            "label": "Все направления",
                                            "value": "Все направления",
                                        }
                                    ],
                                    value="Все направления",
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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=False)

