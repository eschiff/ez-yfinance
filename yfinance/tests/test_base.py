from unittest.mock import patch
import pandas as pd
import pytest

from yfinance.base import TickerBase


def test_TickerBase_init(ticker_symbol):
    ticker = TickerBase(ticker_symbol.lower())

    assert ticker.ticker == ticker_symbol
    assert ticker._historical_data is None
    assert ticker._fundamentals_data is None
    assert ticker._financials_data is None



@patch('yfinance.base.requests')
def test_TickerBase_get_historical_data(requests_mock, ticker_symbol, historical_data_resp):
    requests_mock.get.return_value = historical_data_resp

    ticker = TickerBase(ticker_symbol)
    ticker.get_historical_data()

    assert isinstance(ticker._historical_data, pd.DataFrame)


@patch('yfinance.base.utils')
def test_TickerBase_fundamentals_data(utils_mock, ticker_symbol):
    utils_mock.get_json.return_value = 'Fake Fundamentals Data'

    ticker = TickerBase(ticker_symbol)
    assert ticker._fundamentals_data is None

    assert ticker.fundamentals_data == 'Fake Fundamentals Data'
    assert utils_mock.get_json.called


@patch('yfinance.base.utils')
def test_TickerBase_financials_data(utils_mock, ticker_symbol):
    utils_mock.get_json.return_value = 'Fake Financials Data'

    ticker = TickerBase(ticker_symbol)
    assert ticker._financials_data is None

    assert ticker.financials_data == 'Fake Financials Data'
    assert utils_mock.get_json.called


@patch('yfinance.base.requests')
def test_TickerBase_get_historical_data_fails_yahoo_down(requests_mock, ticker_symbol, yahoo_down_resp):
    requests_mock.get.return_value = yahoo_down_resp

    ticker = TickerBase(ticker_symbol)
    with pytest.raises(RuntimeError):
        ticker.get_historical_data()
