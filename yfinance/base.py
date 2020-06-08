#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Yahoo! Finance market data downloader (+fix for Pandas Datareader)
# https://github.com/ranaroussi/yfinance
#
# Copyright 2017-2019 Ran Aroussi
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from __future__ import print_function

from enum import Enum
import time as _time
from datetime import datetime
import requests
import logging
import pandas as pd
import numpy as np
import re
from typing import Dict, Union
import sys
try:
    from urllib.parse import quote as urlencode
except ImportError:
    from urllib import quote as urlencode

from yfinance import utils, shared, QUARTERLY, YEARLY, TimePeriods, TimeIntervals

_logger = logging.getLogger(__file__)

class TickerBase():
    def __init__(self, ticker: str, proxy: str = None):
        self.ticker = ticker.upper()
        self._history = None
        self._base_url = 'https://query1.finance.yahoo.com'
        self._scrape_url = 'https://finance.yahoo.com/quote'

        self._info = {}
        self._sustainability = pd.DataFrame()
        self._recommendations = pd.DataFrame()
        self._major_holders = pd.DataFrame()
        self._institutional_holders = pd.DataFrame()

        self._calendar = None

        self._earnings = utils.init_financial_df_dict()
        self._financials = utils.init_financial_df_dict()
        self._balancesheet = utils.init_financial_df_dict()
        self._cashflow = utils.init_financial_df_dict()

        self._expirations = {}

        self._fundamentals_data = None
        self._financials_data = None
        self._historical_data = pd.DataFrame()
        self._historical_data_period = None
        self._historical_data_interval = None

         # setup proxy in requests format
        if proxy is not None:
            if isinstance(proxy, dict) and 'https' in proxy:
                proxy = proxy['https']
            proxy = {'https': proxy}
        self._proxy =  proxy

    def get_history(self, 
                    period: TimePeriods = TimePeriods.Month, 
                    interval: TimeIntervals = TimeIntervals.Daily,
                    start: Union[str, datetime, None] = None, 
                    end: Union[str, datetime, None] = None, 
                    prepost: bool=False,
                    auto_adjust: bool=True, 
                    back_adjust: bool=False,
                    rounding: bool=True, 
                    tz=None, 
                    **kwargs) -> pd.DataFrame:
        '''
        Args:
            period : (TimePeriods) How far back to query historical data. 
                Use this or start and end.
            interval : (TimeIntervals) The interval for data queried
            start: (str YYYY-MM-DD or datetime) - default is 1900-01-01
            end: (str YYYY-MM-DD or datetime) - default is 1900-01-01
            prepost : (bool) Include Pre and Post market data in results? Default is False
            auto_adjust: (bool) Adjust all OHLC automatically? Default is True
            back_adjust: (bool) Back-adjusted data to mimic true historical prices
            rounding: (bool) Round values to 2 decimal places?
                Optional. Default is False = precision suggested by Yahoo!
            tz: (str) Optional timezone locale for dates.
                (default data is returned as non-localized dates)
            **kwargs: dict
                debug: bool
                    Optional. If passed as False, will suppress
                    error message printing to console.
        '''
        if start or period == TimePeriods.Max:
            if start is None:
                start = -2208988800
            elif isinstance(start, datetime):
                start = int(_time.mktime(start.timetuple()))
            else:
                start = int(_time.mktime(_time.strptime(str(start), '%Y-%m-%d')))

            if end is None:
                end = int(_time.time())
            elif isinstance(end, datetime):
                end = int(_time.mktime(end.timetuple()))
            else:
                end = int(_time.mktime(_time.strptime(str(end), '%Y-%m-%d')))

            params = {'period1': start, 'period2': end}
        else:
            params = {'range': period.value}
        
        self._historical_data_period = dict(params)
        self._historical_data_interval = interval.name

        params['interval'] = interval.value
        params['includePrePost'] = prepost
        params['events'] = 'div,splits'

        # 1) fix weird bug with Yahoo! - returning 60m for 30m bars
        if params['interval'] == '30m':
            params['interval'] = '15m'

        # Getting data from json
        url = f'{self._base_url}/v8/finance/chart/{self.ticker}'
        data = requests.get(url=url, params=params, proxies=self._proxy)
        if re.search('(?i)will be right back', data.text):
            raise RuntimeError('*** YAHOO! FINANCE IS CURRENTLY DOWN! ***\n'
                               'Our engineers are working quickly to resolve '
                               'the issue. Thank you for your patience.')
        data = data.json()

        # Work with errors
        debug_mode = True
        if 'debug' in kwargs and isinstance(kwargs['debug'], bool):
            debug_mode = kwargs['debug']

        err_msg = 'No data found for this date range, symbol may be delisted'
        if 'chart' in data and data['chart']['error']:
            err_msg = data['chart']['error']['description']
            shared._DFS[self.ticker] = utils.empty_df()
            shared._ERRORS[self.ticker] = err_msg
            if 'many' not in kwargs and debug_mode:
                print('- %s: %s' % (self.ticker, err_msg))
            return shared._DFS[self.ticker]

        elif 'chart' not in data or data['chart']['result'] is None or \
                not data['chart']['result']:
            shared._DFS[self.ticker] = utils.empty_df()
            shared._ERRORS[self.ticker] = err_msg
            if 'many' not in kwargs and debug_mode:
                print('- %s: %s' % (self.ticker, err_msg))
            return shared._DFS[self.ticker]

        # parse quotes
        try:
            quotes = utils.parse_quotes(data['chart']['result'][0], tz)
        except Exception:
            shared._DFS[self.ticker] = utils.empty_df()
            shared._ERRORS[self.ticker] = err_msg
            if 'many' not in kwargs and debug_mode:
                print('- %s: %s' % (self.ticker, err_msg))
            return shared._DFS[self.ticker]

        # 2) fix weird bug with Yahoo! - returning 60m for 30m bars
        if interval.value == '30m':
            quotes2 = quotes.resample('30T')
            quotes = pd.DataFrame(index=quotes2.last().index, data={
                'Open': quotes2['Open'].first(),
                'High': quotes2['High'].max(),
                'Low': quotes2['Low'].min(),
                'Close': quotes2['Close'].last(),
                'Adj Close': quotes2['Adj Close'].last(),
                'Volume': quotes2['Volume'].sum()
            })
            try:
                quotes['Dividends'] = quotes2['Dividends'].max()
            except Exception:
                pass
            try:
                quotes['Stock Splits'] = quotes2['Dividends'].max()
            except Exception:
                pass

        if auto_adjust:
            quotes = utils.auto_adjust(quotes)
        elif back_adjust:
            quotes = utils.back_adjust(quotes)

        if rounding:
            quotes = np.round(quotes, data[
                'chart']['result'][0]['meta']['priceHint'])
        quotes['Volume'] = quotes['Volume'].fillna(0).astype(np.int64)

        quotes.dropna(inplace=True)

        # actions
        dividends, splits = utils.parse_actions(data['chart']['result'][0], tz)

        # combine
        df = pd.concat([quotes, dividends, splits], axis=1, sort=True)
        df['Dividends'].fillna(0, inplace=True)
        df['Stock Splits'].fillna(0, inplace=True)

        # index eod/intraday
        df.index = df.index.tz_localize('UTC').tz_convert(
            data['chart']['result'][0]['meta']['exchangeTimezoneName'])

        if params['interval'][-1] == 'm':
            df.index.name = 'Datetime'
        else:
            df.index = pd.to_datetime(df.index.date)
            if tz is not None:
                df.index = df.index.tz_localize(tz)
            df.index.name = 'Date'

        self._historical_data = df.copy()

        return df

    # ------------------------
        
    def _load_holders_data(self):
        holders_url = f'{self._scrape_url}/{self.ticker}/holders'
        holders = pd.read_html(holders_url)
        if len(holders) > 1:
            self._major_holders = holders[0]
            self._institutional_holders = holders[1]
            if 'Date Reported' in self._institutional_holders:
                self._institutional_holders['Date Reported'] = pd.to_datetime(
                    self._institutional_holders['Date Reported'])
            if '% Out' in self._institutional_holders:
                self._institutional_holders['% Out'] = self._institutional_holders[
                    '% Out'].str.replace('%', '').astype(float)/100
        else:
            _logger.warning("No holders found")
    
    def _load_recommendations(self):
        rec = pd.DataFrame(
                self.fundamentals_data['upgradeDowngradeHistory']['history'])
        rec['earningsDate'] = pd.to_datetime(
            rec['epochGradeDate'], unit='s')
        rec.set_index('earningsDate', inplace=True)
        rec.index.name = 'Date'
        rec.columns = utils.camel2title(rec.columns)
        self._recommendations = rec[[
            'Firm', 'To Grade', 'From Grade', 'Action']].sort_index()
    
    def _load_sustainability(self):
        d = {}
        if isinstance(self.fundamentals_data.get('esgScores'), dict):
            for item in self.fundamentals_data['esgScores']:
                if not isinstance(self.fundamentals_data['esgScores'][item], (dict, list)):
                    d[item] = self.fundamentals_data['esgScores'][item]

            s = pd.DataFrame(index=[0], data=d)[-1:].T
            s.columns = ['Value']
            s.index.name = '%.f-%.f' % (
                s[s.index == 'ratingYear']['Value'].values[0],
                s[s.index == 'ratingMonth']['Value'].values[0])

            self._sustainability = s[~s.index.isin(
                ['maxAge', 'ratingYear', 'ratingMonth'])]
        else:
            _logger.warning('Unable to identify sustainability data')
    
    def _load_info(self):
        self._info = {}
        items = ['summaryProfile', 'summaryDetail', 'quoteType',
                 'defaultKeyStatistics', 'assetProfile', 'summaryDetail']
        for item in items:
            if isinstance(self.fundamentals_data.get(item), dict):
                self._info.update(self.fundamentals_data[item])

        try:
            self._info['regularMarketPrice'] = self.fundamentals_data['financialData']['currentPrice']
        except KeyError:
            _logger.warning('Unable to locate price data!')

        self._info['logo_url'] = ''
        try:
            domain = self._info['website'].split('://')[1].split('/')[0].replace('www.', '')
            self._info['logo_url'] = f'https://logo.clearbit.com/{domain}'
        except Exception:
            _logger.warning('Exception occurred when trying to identify logo url')
    
    def _load_events(self):
        cal = pd.DataFrame(self.fundamentals_data['calendarEvents']['earnings'])
        cal['earningsDate'] = pd.to_datetime(cal['earningsDate'], unit='s')
        self._calendar = cal.T
        self._calendar.index = utils.camel2title(self._calendar.index)
    
    def _load_financials_data(self):
        def _cleanup(data: Dict) -> pd.DataFrame:
            df = pd.DataFrame(data).drop(columns=['maxAge'])
            for col in df.columns:
                df[col] = np.where(
                    df[col].astype(str) == '-', np.nan, df[col])

            df.set_index('endDate', inplace=True)
            try:
                df.index = pd.to_datetime(df.index, unit='s')
            except ValueError:
                df.index = pd.to_datetime(df.index)
            df = df.T
            df.columns.name = ''
            df.index.name = 'Breakdown'

            df.index = utils.camel2title(df.index)
            return df

        for key in (
            (self._cashflow, 'cashflowStatement', 'cashflowStatements'),
            (self._balancesheet, 'balanceSheet', 'balanceSheetStatements'),
            (self._financials, 'incomeStatement', 'incomeStatementHistory')
        ):

            item = key[1] + 'History'
            if isinstance(self.financials_data.get(item), dict):
                key[0][YEARLY] = _cleanup(self.financials_data[item][key[2]])
            else:
                _logger.warning(f'Unable to identify yearly {key[1]}')

            item = key[1]+'HistoryQuarterly'
            if isinstance(self.financials_data.get(item), dict):
                key[0][QUARTERLY] = _cleanup(self.financials_data[item][key[2]])
            else:
                _logger.warning(f'Unable to identify quarterly {key[1]}')

    
    def _load_earnings(self):
        if isinstance(self.financials_data.get('earnings'), dict):
            earnings = self.financials_data['earnings']['financialsChart']
            df = pd.DataFrame(earnings[YEARLY]).set_index('date')
            df.columns = utils.camel2title(df.columns)
            df.index.name = 'Year'
            self._earnings[YEARLY] = df

            df = pd.DataFrame(earnings[QUARTERLY]).set_index('date')
            df.columns = utils.camel2title(df.columns)
            df.index.name = 'Quarter'
            self._earnings[QUARTERLY] = df
        else:
            _logger.warning(f'Unable to locate earnings data')

    
    def _load_dividends(self):
        if self._historical_data is None:
            self.get_history(period=TimePeriods.Max)

        dividends = self._historical_data['Dividends']
        self._dividends = dividends[dividends != 0]
        
    @property
    def fundamentals_data(self) -> Dict:
        if self._fundamentals_data is None:
            self._fundamentals_data = utils.get_json(
                f'{self._scrape_url}/{self.ticker}', self._proxy)

        return self._fundamentals_data
    
    @property
    def financials_data(self) -> Dict:
        if self._financials_data is None:
            self._financials_data = utils.get_json(
                f'{self._scrape_url}/{self.ticker}/financials', self._proxy)

        return self._financials_data
