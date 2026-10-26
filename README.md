# ConsultFlow — Wiki цифрового продукта

**Слоган:** От заявки до акта — один процесс

**Тема:** Процесс обработки заказов на консалтинговые услуги

## Разделы Wiki

- [Главная](consultflow-wiki/Home.md)
- [01. Определение продукта](consultflow-wiki/01-product.md)
- [02. Состояние продукта](consultflow-wiki/02-state.md)
- [03. Развитие продукта](consultflow-wiki/03-development.md)
- [04. Артефакты](consultflow-wiki/04-artifacts.md)
- [05. Таблица ролей](consultflow-wiki/05-roles.md)
- [06. Техническая часть](consultflow-wiki/06-technical.md)
- [07. Тестирование](consultflow-wiki/07-testing.md)
- [08. Безопасность](consultflow-wiki/08-security.md)

## О продукте

ConsultFlow автоматизирует полный цикл обработки заказов на консалтинговые услуги: от заявки до акта выполненных работ.

## Ответственные за Wiki

| Раздел            | Ответственный |
| ----------------- | ------------- |
| Продуктовая часть | Иванов И.     |
| Техническая часть | Петров П.     |
| Тестирование      | Сидорова С.   |
| Безопасность      | Кузнецов К.   |

## Дашборд

В папке `dashboard` находится учебный Dash-дашборд по заказам: карточки показателей, графики и таблица с фильтрами. Инструкция запуска и описание графиков — в [dashboard/README.md](dashboard/README.md).

```powershell
pip install -r dashboard/requirements.txt
python dashboard/app.py
```

После запуска откройте <http://127.0.0.1:8050> и загрузите `dashboard/orders.csv`.
