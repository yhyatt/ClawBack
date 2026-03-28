"""Tests for live Frankfurter exchange rates: get_rate, convert, get_display_amount."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import requests

from clawback.fx import FXCache, FXError, convert, get_rate
from clawback.templates import get_display_amount


class TestGetRateReturnsFloat:
    """get_rate returns a usable Decimal (not int, not float)."""

    def setup_method(self) -> None:
        FXCache.clear()

    @patch("clawback.fx.requests.get")
    def test_get_rate_returns_float(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"ILS": 3.63}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        rate = get_rate("EUR", "ILS")

        assert isinstance(rate, Decimal)
        assert float(rate) == pytest.approx(3.63)


class TestConvertEurToIls:
    """convert() multiplies by the live rate and rounds to 2dp."""

    def setup_method(self) -> None:
        FXCache.clear()

    @patch("clawback.fx.requests.get")
    def test_convert_eur_to_ils(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"ILS": 3.63}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = convert(Decimal("250"), "EUR", "ILS")

        assert result == Decimal("907.50")


class TestCachePreventsRequests:
    """Second call to get_rate must hit the cache, not the network."""

    def setup_method(self) -> None:
        FXCache.clear()

    @patch("clawback.fx.requests.get")
    def test_cache_prevents_duplicate_requests(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"ILS": 3.63}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        get_rate("EUR", "ILS")
        get_rate("EUR", "ILS")

        assert mock_get.call_count == 1


class TestFallbackOnNetworkError:
    """convert() must not crash when Frankfurter is unreachable — returns original amount."""

    def setup_method(self) -> None:
        FXCache.clear()

    @patch("clawback.fx.requests.get")
    def test_fallback_on_network_error(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.RequestException("timeout")

        result = convert(Decimal("250"), "EUR", "ILS")

        # Returns original amount unchanged (rate treated as 1.0)
        assert result == Decimal("250")


class TestGetDisplayAmountFormat:
    """get_display_amount returns 'primary (≈ base)' when currencies differ."""

    def setup_method(self) -> None:
        FXCache.clear()

    @patch("clawback.fx.requests.get")
    def test_get_display_amount_format(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"ILS": 3.63}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = get_display_amount(Decimal("250"), "EUR", "ILS")

        assert result == "€250 (≈ ₪907.50)"

    def test_same_currency_no_annotation(self) -> None:
        result = get_display_amount(Decimal("250"), "ILS", "ILS")
        assert result == "₪250"

    @patch("clawback.fx.requests.get")
    def test_fallback_on_rate_error(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.RequestException("timeout")

        result = get_display_amount(Decimal("250"), "EUR", "ILS")

        # Graceful degradation: no annotation, no crash
        assert result == "€250"
