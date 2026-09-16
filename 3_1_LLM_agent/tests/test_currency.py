import time
from unittest.mock import patch, MagicMock

import pytest

from llm_agent.tool_currency import CurrencyConverterTool


def _mock_response(rates, status=200):
    """Хелпер: делает фейковый ответ requests.get."""
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = {"result": "success", "rates": rates}
    mock.raise_for_status = MagicMock()
    return mock

# ЮНИТ-ТЕСТЫ (без сети, без Ollama — работают в CI)


@patch("llm_agent.tool_currency.requests.get")
def test_convert_usd_to_rub(mock_get):
    """Базовая конвертация: 100 USD -> RUB при курсе 92."""
    mock_get.return_value = _mock_response({"RUB": 92.0})

    tool = CurrencyConverterTool()
    result = tool.use("USD", "RUB", 100)

    assert "9200.00 RUB" in result
    assert "100.00 USD" in result
    mock_get.assert_called_once()


@patch("llm_agent.tool_currency.requests.get")
def test_cache_hit_avoids_second_request(mock_get):
    """Второй вызов в пределах TTL не должен дёргать API снова."""
    mock_get.return_value = _mock_response({"RUB": 92.0})

    tool = CurrencyConverterTool()
    tool.use("USD", "RUB", 100)
    tool.use("USD", "RUB", 200)

    assert mock_get.call_count == 1, "Второй запрос не должен идти в API (кеш)"


@patch("llm_agent.tool_currency.requests.get")
def test_cache_expires_after_ttl(mock_get):
    """После истечения TTL кеш должен обновиться (новый запрос к API)."""
    mock_get.return_value = _mock_response({"RUB": 92.0})

    tool = CurrencyConverterTool()
    tool.use("USD", "RUB", 100)

    # Сдвигаем время вперёд на 2 часа
    with patch("llm_agent.tool_currency.time.time", return_value=time.time() + 7200):
        tool.use("USD", "RUB", 100)

    assert mock_get.call_count == 2, "После TTL должен быть новый запрос"


@patch("llm_agent.tool_currency.requests.get")
def test_unknown_currency_returns_error(mock_get):
    """Неизвестная валюта -> понятное сообщение об ошибке."""
    mock_get.return_value = _mock_response({"RUB": 92.0})

    tool = CurrencyConverterTool()
    result = tool.use("USD", "XYZ", 100)

    assert "Ошибка" in result
    assert "XYZ" in result


@patch("llm_agent.tool_currency.requests.get")
def test_api_failure_returns_error(mock_get):
    """Если API упал — инструмент возвращает ошибку, а не падает."""
    import requests
    mock_get.side_effect = requests.RequestException("network down")

    tool = CurrencyConverterTool()
    result = tool.use("USD", "RUB", 100)

    assert "Ошибка" in result


def test_all_unit_tests_runner():
    """Общий прогон всех юнит-тестов внутри одной функции (требование лабы)."""
    test_convert_usd_to_rub()
    test_cache_hit_avoids_second_request()
    test_cache_expires_after_ttl()
    test_unknown_currency_returns_error()
    test_api_failure_returns_error()