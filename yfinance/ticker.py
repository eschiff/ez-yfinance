#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Yahoo! Finance market data downloader (+fix for Pandas Datareader)
# https://github.com/ranaroussi/yfinance
#
# Copyright 2017-2019 Ran Aroussi
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from __future__ import print_function

# import time as _time
import datetime as datetime
import requests as requests
import pandas as pd
import logging
from typing import Union, Dict

from collections import namedtuple as _namedtuple

from yfinance.base import TickerBase
from yfinance.constants import TimePeriods, QUARTERLY, YEARLY

_logger = logging.getLogger(__file__)

class Ticker(TickerBase):

    def __repr__(self):
        return 'yfinance.Ticker object <%s>' % self.ticker

    def _download_options(self, date=None) -> Dict:
        url = f"{self._base_url}/v7/finance/options/{self.ticker}"
        if date:
            url += f'?date={date}'

        r = requests.get(url=url, proxies=self._proxy).json()
        if r['optionChain']['result']:
            for exp in r['optionChain']['result'][0]['expirationDates']:
                self._expirations[datetime.datetime.fromtimestamp(
                    exp).strftime('%Y-%m-%d')] = exp
            return r['optionChain']['result'][0]['options'][0]
        return {}

    def _options2df(self, opt: Dict, tz=None) -> pd.DataFrame:
        data = pd.DataFrame(opt).reindex(columns=[
            'contractSymbol',
            'lastTradeDate',
            'strike',
            'lastPrice',
            'bid',
            'ask',
            'change',
            'percentChange',
            'volume',
            'openInterest',
            'impliedVolatility',
            'inTheMoney',
            'contractSize',
            'currency'])

        data['lastTradeDate'] = pd.todatetime(data['lastTradeDate'], unit='s')
        if tz is not None:
            data['lastTradeDate'] = data['lastTradeDate'].tz_localize(tz)
        return data

    def option_chain(self, date: Union[str, None]=None, tz=None):
        if not self._expirations:
            self._download_options()

        if date is not None:
            if date not in self._expirations:
                raise ValueError(f"Expiration `{date}` cannot be found. "
                                 f"Available expiration are: {', '.join(self._expirations)}")
            expirations_date = self._expirations[date]
            options = self._download_options(expirations_date)

        return _namedtuple('Options', ['calls', 'puts'])(**{
            "calls": self._options2df(options['calls'], tz=tz),
            "puts": self._options2df(options['puts'], tz=tz)
        })

    # ------------------------

    @property
    def major_holders(self):
        if not self._major_holders:
            self._load_holders_data()

        return self._major_holders

    @property
    def institutional_holders(self):
        if not self._institutional_holders:
            self._load_holders_data()
        
        return self._institutional_holders

    @property
    def dividends(self):
        if not self._historical_data:
            self.get_historical_data(period=TimePeriods.Max)

        _logger.info(f'Returning dividends for period {self._historical_data_period}'
                     f' with interval {self._historical_data_interval}')

        dividends = self._historical_data["Dividends"]
        return dividends[dividends != 0]

    @property
    def splits(self):
        if not self._historical_data:
            self.get_historical_data(period=TimePeriods.Max)
        
        _logger.info(f'Returning splits for period {self._historical_data_period}'
                     f' with interval {self._historical_data_interval}')

        splits = self._historical_data["Stock Splits"]
        return splits[splits != 0]

    @property
    def actions(self):
        if not self._historical_data:
            self.get_historical_data(period=TimePeriods.Max)

        _logger.info(f'Returning actions for period {self._historical_data_period}'
                     f' with interval {self._historical_data_interval}')

        actions = self._historical_data[["Dividends", "Stock Splits"]]
        self._actions = actions[actions != 0].dropna(how='all').fillna(0)

    @property
    def info(self):
        if not self._info:
            self._load_info()
        
        return self._info

    @property
    def calendar(self):
        if not self._calendar:
            self._load_events()
        
        return self._calendar

    @property
    def recommendations(self):
        if not self._recommendations:
            self._load_recommendations()
        
        return self._recommendations

    @property
    def earnings(self):
        if self._earnings[YEARLY].empty:
            self._load_earnings()
        
        return self._earnings[YEARLY]

    @property
    def quarterly_earnings(self):
        if self._earnings[QUARTERLY].empty:
            self._load_earnings()
        
        return self._earnings[QUARTERLY]

    @property
    def financials(self):
        if self._financials[YEARLY].empty:
            self._load_financials_data()
        
        return self._financials[YEARLY]

    @property
    def quarterly_financials(self):
        if self._financials[QUARTERLY].empty:
            self._load_financials_data()
        
        return self._financials[QUARTERLY]

    @property
    def balance_sheet(self):
        if self._balancesheet[YEARLY].empty:
            self._load_financials_data()
        
        return self._balancesheet[YEARLY]

    @property
    def quarterly_balance_sheet(self):
        if self._balancesheet[QUARTERLY].empty:
            self._load_financials_data()
        
        return self._balancesheet[QUARTERLY]

    @property
    def cashflow(self):
        if self._cashflow[YEARLY].empty:
            self._load_financials_data()
        
        return self._cashflow[YEARLY]

    @property
    def quarterly_cashflow(self):
        if self._cashflow[QUARTERLY].empty:
            self._load_financials_data()
        
        return self._cashflow[QUARTERLY]

    @property
    def sustainability(self):
        if not self._sustainability:
            self._load_sustainability()

        return self._sustainability

    @property
    def options_expiration_dates(self):
        if not self._expirations:
            self._download_options()
        return tuple(self._expirations.keys())
