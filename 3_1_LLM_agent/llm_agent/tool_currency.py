import time
import requests


class CurrencyConverterTool:
    """
    Инструмент для конвертации валют через публичное API open.er-api.com.
    Курсы кешируются на 1 час, чтобы не долбить API лишними запросами.
    """

    name = "currency_converter"
    description = (
        "Конвертирует сумму из одной валюты в другую. "
        "Пример: use('USD', 'RUB', 100) -> '100 USD = 9200 RUB'. "
        "Поддерживает любые коды валют ISO 4217 (USD, EUR, RUB, CNY и т.д.)."
    )

    API_URL = "https://open.er-api.com/v6/latest/{base}"
    CACHE_TTL = 3600  # 1 час

    def __init__(self):
        # Кеш: {base_currency: (rates_dict, timestamp)}
        self._cache = {}

    def use(self, query: str, to_currency: str = None, amount: float = None) -> str:
        """
        Конвертирует валюту.

        Поддерживает два формата вызова:
            1) use("USD RUB 100")   — строка "FROM TO AMOUNT"
            2) use("USD", "RUB", 100) — три аргумента

        Returns:
            str: Строка с результатом или сообщением об ошибке.
        """
        # Вариант 1: одна строка "FROM TO AMOUNT"
        if to_currency is None and amount is None:
            parts = query.strip().split()
            if len(parts) != 3:
                return (
                    f"Ошибка: неверный формат '{query}'. "
                    "Ожидается 'FROM TO AMOUNT', например 'USD RUB 100'."
                )
            from_currency, to_currency, amount_str = parts
            try:
                amount = float(amount_str)
            except ValueError:
                return f"Ошибка: сумма '{amount_str}' не является числом."
        else:
            # Вариант 2: три аргумента
            from_currency = query

        from_currency = from_currency.upper().strip()
        to_currency = to_currency.upper().strip()

        if amount <= 0:
            return f"Ошибка: сумма должна быть положительной, получено {amount}."

        rates = self._get_rates(from_currency)
        if rates is None:
            return f"Ошибка: не удалось получить курс для валюты '{from_currency}'."

        if to_currency not in rates:
            return f"Ошибка: неизвестная валюта '{to_currency}'."

        rate = rates[to_currency]
        result = amount * rate
        return (
            f"{amount:.2f} {from_currency} = {result:.2f} {to_currency} "
            f"(курс: 1 {from_currency} = {rate:.4f} {to_currency})"
        )

    def _get_rates(self, base_currency: str):
        """
        Возвращает словарь курсов для базовой валюты.
        Использует кеш, если данные моложе CACHE_TTL секунд.
        """
        now = time.time()
        cached = self._cache.get(base_currency)

        if cached is not None:
            rates, ts = cached
            if now - ts < self.CACHE_TTL:
                return rates

        rates = self._fetch_rates(base_currency)
        if rates is not None:
            self._cache[base_currency] = (rates, now)
        return rates

    def _fetch_rates(self, base_currency: str):
        """Делает HTTP-запрос к API и возвращает словарь курсов или None."""
        url = self.API_URL.format(base=base_currency)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("result") != "success":
                return None

            return data.get("rates")
        except (requests.RequestException, ValueError):
            return None