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
        return f'yfinance.Ticker object <{self.ticker}>'

    def _download_options(self, date=None) -> Dict:
        url = f'{self._base_url}/v7/finance/options/{self.ticker}'
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

    def option_chain(self, date: Union[str, None] = None, tz=None):
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
    def history(self) -> pd.DataFrame:
        """Get ticker price data for a given period.

        To update the time periods or interval of data, call get_history with custom time period

        Eg.:
                      Open    High     Low   Close    Volume  Dividends  Stock Splits
            Date
            2020-03-06  162.16  162.66  155.57  161.12  72821100        0.0             0
            2020-03-09  150.58  157.31  149.58  150.20  70419300        0.0             0
            ...            ...     ...     ...     ...       ...        ...           ...
        """
        if self._historical_data.empty:
            self.get_history(period=TimePeriods.Max)

        _logger.info(f'Returning {self._historical_data_interval} interval history'
                     f' for period {self._historical_data_period}')

        return self._historical_data

    @property
    def major_holders(self) -> pd.DataFrame:
        """General Info about major holders

        Eg.:
                0                                      1
            0   1.42%        % of Shares Held by All Insider
            1  74.09%       % of Shares Held by Institutions
            2  75.16%        % of Float Held by Institutions
            3    4630  Number of Institutions Holding Shares
        """
        if self._major_holders.empty:
            self._load_holders_data()

        return self._major_holders

    @property
    def institutional_holders(self) -> pd.DataFrame:
        """Institutional holders

        Eg.:
                                      Holder     Shares Date Reported   % Out         Value
            0         Vanguard Group, Inc. (The)  640172572    2020-03-30  0.0844  100961616330
            1                     Blackrock Inc.  517578906    2020-03-30  0.0683   81627369265
        """
        if self._institutional_holders.empty:
            self._load_holders_data()

        return self._institutional_holders

    @property
    def dividends(self) -> pd.Series:
        """Dividends by date

        To update the time periods or interval of data, call get_history with custom time period

        Eg.:
            Date
            2003-02-19    0.08
            2003-10-15    0.16
        """
        if self._historical_data.empty:
            self.get_history(period=TimePeriods.Max)

        _logger.info(f'Returning {self._historical_data_interval} interval dividend history'
                     f' for period {self._historical_data_period}')

        dividends = self._historical_data["Dividends"]
        return dividends[dividends != 0]

    @property
    def splits(self) -> pd.Series:
        """Splits by date

        To update the time periods or interval of data, call get_history with custom time period

        Eg.:
            Date
            1987-09-21    2.0
            1990-04-16    2.0
        """
        if self._historical_data.empty:
            self.get_history(period=TimePeriods.Max)

        _logger.info(f'Returning {self._historical_data_interval} interval split history'
                     f' for period {self._historical_data_period}')

        splits = self._historical_data["Stock Splits"]
        return splits[splits != 0]

    @property
    def actions(self) -> pd.DataFrame:
        """Dividends and Stock Splits by date

        To update the time periods or interval of data, call get_history with custom time period

        Eg.:
                        Dividends  Stock Splits
            Date
            1987-09-21       0.00           2.0
            1990-04-16       0.00           2.0
            ...               ...           ...
            2020-02-19       0.51           0.0
            2020-05-20       0.51           0.0
        """
        if self._historical_data.empty:
            self.get_history(period=TimePeriods.Max)

        _logger.info(f'Returning {self._historical_data_interval} interval action history'
                     f' for period {self._historical_data_period}')

        actions = self._historical_data[["Dividends", "Stock Splits"]]
        self._actions = actions[(actions['Dividends' != 0]) | (actions['Stock Splits'] != 0)]

    @property
    def info(self) -> Dict:
        """
        Get info about Ticker object.
        Keys include:
            zip, sector, fullTimeEmployees, longBusinessSummary, city, phone, state, country,
            companyOfficers, website, maxAge, address1, fax, industry, previousClose,
            regularMarketOpen, twoHundredDayAverage, trailingAnnualDividendYield,
            payoutRatio, volume24Hr, regularMarketDayHigh, navPrice, averageDailyVolume10Day,
            totalAssets, regularMarketPreviousClose, fiftyDayAverage, trailingAnnualDividendRate,
            open, toCurrency, averageVolume10days, expireDate, yield, algorithm,
            dividendRate, exDividendDate, beta, circulatingSupply, startDate, regularMarketDayLow,
            priceHint, currency, trailingPE, regularMarketVolume, lastMarket, maxSupply,
            openInterest, marketCap, volumeAllCurrencies, strikePrice, averageVolume,
            priceToSalesTrailing12Months, dayLow, ask, ytdReturn, askSize, volume, fiftyTwoWeekHigh,
            forwardPE, fromCurrency, fiveYearAvgDividendYield, fiftyTwoWeekLow, bid, tradeable,
            dividendYield, bidSize, dayHigh, exchange, shortName, longName,
            exchangeTimezoneName, exchangeTimezoneShortName, isEsgPopulated, gmtOffSetMilliseconds,
            quoteType, symbol, messageBoardId, market, annualHoldingsTurnover, enterpriseToRevenue,
            beta3Year, profitMargins, enterpriseToEbitda, 52WeekChange, morningStarRiskRating,
            forwardEps, revenueQuarterlyGrowth, sharesOutstanding, fundInceptionDate,
            annualReportExpenseRatio, bookValue, sharesShort, sharesPercentSharesOut, fundFamily,
            lastFiscalYearEnd, heldPercentInstitutions, netIncomeToCommon, trailingEps,
            lastDividendValue, SandP52WeekChange, priceToBook, heldPercentInsiders,
            nextFiscalYearEnd, mostRecentQuarter, shortRatio, sharesShortPreviousMonthDate,
            floatShares, enterpriseValue, threeYearAverageReturn, lastSplitDate,
            lastSplitFactor, legalType, morningStarOverallRating, earningsQuarterlyGrowth,
            dateShortInterest, pegRatio, lastCapGain, shortPercentOfFloat, sharesShortPriorMonth,
            category, fiveYearAverageReturn, regularMarketPrice, logo_url
        """
        if not self._info:
            self._load_info()

        return self._info

    @property
    def calendar(self) -> pd.DataFrame:
        """

        Eg.:
                                            0                    1
            Earnings Date     2020-07-16 00:00:00  2020-07-20 00:00:00
            Earnings Average                 1.39                 1.39
            Earnings Low                     1.35                 1.35
            Earnings High                    1.51                 1.51
            Revenue Average           36496400000          36496400000
            Revenue Low               36053000000          36053000000
            Revenue High              37098000000          37098000000
        """
        if not self._calendar:
            self._load_events()

        return self._calendar

    @property
    def recommendations(self) -> pd.DataFrame:
        """Economist recommendations

        Eg.:
                                       Firm       To Grade From Grade Action
            Date
            2012-03-16 08:19:00  Argus Research            Buy                up
            2012-03-19 14:00:00  Hilliard Lyons  Long-Term Buy              main
            ...                             ...            ...        ...    ...
            2020-04-30 15:47:20     Wells Fargo     Overweight              main
            2020-05-18 13:45:46     RBC Capital     Outperform              reit
        """
        if self._recommendations.empty:
            self._load_recommendations()

        return self._recommendations

    @property
    def earnings(self) -> pd.DataFrame:
        """Earnings by year for last 4 years

        Eg.:
                       Revenue     Earnings
            Year
            2016   91154000000  20539000000
            2017   96571000000  25489000000
            2018  110360000000  16571000000
            2019  125843000000  39240000000
        """
        if self._earnings[YEARLY].empty:
            self._load_earnings()

        return self._earnings[YEARLY]

    @property
    def quarterly_earnings(self):
        """Earnings by quarter for last 4 quarters

        Eg.:
                     Revenue     Earnings
            Quarter
            2Q2019   33717000000  13187000000
            3Q2019   33055000000  10678000000
            4Q2019   36906000000  11649000000
            1Q2020   35021000000  10752000000
        """
        if self._earnings[QUARTERLY].empty:
            self._load_earnings()

        return self._earnings[QUARTERLY]

    @property
    def financials(self) -> pd.DataFrame:
        """Financial Data for last 4 years

        Eg.:
                                                 2019-06-30  2018-06-30  2017-06-30  2016-06-30
            Research Development                     1.6876e+10  1.4726e+10  1.3037e+10  1.1988e+10
            Effect Of Accounting Charges                   None        None        None        None
            Income Before Tax                        4.3688e+10  3.6474e+10  2.9901e+10  2.5639e+10
            Minority Interest                              None        None        None        None
            Net Income                                3.924e+10  1.6571e+10  2.5489e+10  2.0539e+10
            Selling General Administrative           2.3098e+10  2.2223e+10  1.9942e+10  1.9198e+10
            Gross Profit                             8.2933e+10  7.2007e+10   6.231e+10  5.8374e+10
            Ebit                                     4.2959e+10  3.5058e+10  2.9331e+10  2.7188e+10
            Operating Income                         4.2959e+10  3.5058e+10  2.9331e+10  2.7188e+10
            Other Operating Expenses                       None        None        None        None
            Interest Expense                         -2.686e+09  -2.733e+09  -2.222e+09  -1.243e+09
            Extraordinary Items                            None        None        None        None
            Non Recurring                                  None        None        None        None
            Other Items                                    None        None        None        None
            Income Tax Expense                        4.448e+09  1.9903e+10   4.412e+09     5.1e+09
            Total Revenue                           1.25843e+11  1.1036e+11  9.6571e+10  9.1154e+10
            Total Operating Expenses                 8.2884e+10  7.5302e+10   6.724e+10  6.3966e+10
            Cost Of Revenue                           4.291e+10  3.8353e+10  3.4261e+10   3.278e+10
            Total Other Income Expense Net             7.29e+08   1.416e+09     5.7e+08  -1.549e+09
            Discontinued Operations                        None        None        None        None
            Net Income From Continuing Ops            3.924e+10  1.6571e+10  2.5489e+10  2.0539e+10
            Net Income Applicable To Common Shares    3.924e+10  1.6571e+10  2.5489e+10  2.0539e+10
        """
        if self._financials[YEARLY].empty:
            self._load_financials_data()

        return self._financials[YEARLY]

    @property
    def quarterly_financials(self) -> pd.DataFrame:
        """Financial Data for last 4 quarters

        Eg.:
                                                2020-03-31  2019-12-31  2019-09-30  2019-06-30
            Research Development                     4.887e+09   4.603e+09   4.565e+09   4.513e+09
            Effect Of Accounting Charges                  None        None        None        None
            Income Before Tax                       1.2843e+10  1.4085e+10  1.2686e+10  1.2596e+10
            Minority Interest                             None        None        None        None
            Net Income                              1.0752e+10  1.1649e+10  1.0678e+10  1.3187e+10
            Selling General Administrative           6.184e+09   6.054e+09   5.398e+09   6.387e+09
            Gross Profit                            2.4046e+10  2.4548e+10  2.2649e+10  2.3305e+10
            Ebit                                    1.2975e+10  1.3891e+10  1.2686e+10  1.2405e+10
            Operating Income                        1.2975e+10  1.3891e+10  1.2686e+10  1.2405e+10
            Other Operating Expenses                      None        None        None        None
            Interest Expense                         -6.15e+08   -6.55e+08   -6.37e+08   -6.69e+08
            Extraordinary Items                           None        None        None        None
            Non Recurring                                 None        None        None        None
            Other Items                                   None        None        None        None
            Income Tax Expense                       2.091e+09   2.436e+09   2.008e+09   -5.91e+08
            Total Revenue                           3.5021e+10  3.6906e+10  3.3055e+10  3.3717e+10
            Total Operating Expenses                2.2046e+10  2.3015e+10  2.0369e+10  2.1312e+10
            Cost Of Revenue                         1.0975e+10  1.2358e+10  1.0406e+10  1.0412e+10
            Total Other Income Expense Net           -1.32e+08    1.94e+08           0    1.91e+08
            Discontinued Operations                       None        None        None        None
            Net Income From Continuing Ops          1.0752e+10  1.1649e+10  1.0678e+10  1.3187e+10
            Net Income Applicable To Common Shares  1.0752e+10  1.1649e+10  1.0678e+10  1.3187e+10
        """
        if self._financials[QUARTERLY].empty:
            self._load_financials_data()

        return self._financials[QUARTERLY]

    @property
    def balance_sheet(self) -> pd.DataFrame:
        """Balance sheet for last 4 years

        Eg.:
                                            2019-06-30    2018-06-30    2017-06-30    2016-06-30
            Intangible Assets                 7.750000e+09  8.053000e+09  1.010600e+10  3.733000e+09
            Total Liab                        1.842260e+11  1.761300e+11  1.626010e+11  1.214710e+11
            Total Stockholder Equity          1.023300e+11  8.271800e+10  8.771100e+10  7.199700e+10
            Other Current Liab                4.586000e+10  3.819500e+10  3.087900e+10  3.397200e+10
            Total Assets                      2.865560e+11  2.588480e+11  2.503120e+11  1.934680e+11
            Common Stock                      7.852000e+10  7.122300e+10  6.931500e+10  6.817800e+10
            Other Current Assets              1.013300e+10  6.855000e+09  5.183000e+09  6.091000e+09
            Retained Earnings                 2.415000e+10  1.368200e+10  1.776900e+10  2.282000e+09
            Other Liab                        3.569900e+10  3.570700e+10  2.298600e+10  2.079600e+10
            Good Will                         4.202600e+10  3.568300e+10  3.512200e+10  1.787200e+10
            Treasury Stock                   -3.400000e+08 -2.187000e+09  6.270000e+08  1.537000e+09
            Other Assets                      1.472300e+10  7.442000e+09  6.076000e+09  3.409000e+09
            Cash                              1.135600e+10  1.194600e+10  7.663000e+09  6.510000e+09
            Total Current Liabilities         6.942000e+10  5.848800e+10  5.574500e+10  5.935700e+10
            Deferred Long Term Asset Charges  7.536000e+09  1.369000e+09  2.480000e+08  2.190000e+08
            Short Long Term Debt              5.516000e+09  3.998000e+09  1.049000e+09           NaN
            Other Stockholder Equity         -3.400000e+08 -2.187000e+09  6.270000e+08  1.537000e+09
            Property Plant Equipment          4.385600e+10  3.614600e+10  3.028900e+10  1.835600e+10
            Total Current Assets              1.755520e+11  1.696620e+11  1.626960e+11  1.396600e+11
            Long Term Investments             2.649000e+09  1.862000e+09  6.023000e+09  1.043800e+10
            Net Tangible Assets               5.255400e+10  3.898200e+10  4.248300e+10  5.039200e+10
            Short Term Investments            1.224760e+11  1.217180e+11  1.252380e+11  1.065310e+11
            Net Receivables                   2.952400e+10  2.648100e+10  2.243100e+10  1.827700e+10
            Long Term Debt                    6.666200e+10  7.224200e+10  7.607300e+10  4.055700e+10
            Inventory                         2.063000e+09  2.662000e+09  2.181000e+09  2.251000e+09
            Accounts Payable                  9.382000e+09  8.617000e+09  7.390000e+09  6.898000e+09
        """
        if self._balancesheet[YEARLY].empty:
            self._load_financials_data()

        return self._balancesheet[YEARLY]

    @property
    def quarterly_balance_sheet(self) -> pd.DataFrame:
        """Balance sheet for last 4 quarters

        Eg.:
                                            2020-03-31    2019-12-31    2019-09-30    2019-06-30
            Intangible Assets                 6.855000e+09  7.126000e+09  7.508000e+09  7.750000e+09
            Total Liab                        1.709480e+11  1.726850e+11  1.728940e+11  1.842260e+11
            Total Stockholder Equity          1.145010e+11  1.101090e+11  1.060610e+11  1.023300e+11
            Other Current Liab                3.743200e+10  3.708100e+10  3.989600e+10  4.586000e+10
            Total Assets                      2.854490e+11  2.827940e+11  2.789550e+11  2.865560e+11
            Common Stock                      7.981300e+10  7.962500e+10  7.888200e+10  7.852000e+10
            Other Current Assets              8.520000e+09  7.495000e+09  7.578000e+09  1.013300e+10
            Retained Earnings                 3.201200e+10  3.073900e+10  2.724000e+10  2.415000e+10
            Other Liab                        3.399100e+10  3.422500e+10  3.417800e+10  3.569900e+10
            Good Will                         4.206400e+10  4.224800e+10  4.211300e+10  4.202600e+10
            Treasury Stock                    2.676000e+09 -2.550000e+08 -6.100000e+07 -3.400000e+08
            Other Assets                      1.369600e+10  1.463000e+10  1.445500e+10  1.472300e+10
            Cash                              1.171000e+10  8.864000e+09  1.311700e+10  1.135600e+10
            Total Current Liabilities         5.870700e+10  5.964000e+10  5.811800e+10  6.942000e+10
            Short Long Term Debt              3.748000e+09  6.247000e+09  3.017000e+09  5.516000e+09
            Other Stockholder Equity          2.676000e+09 -2.550000e+08 -6.100000e+07 -3.400000e+08
            Property Plant Equipment          4.966900e+10  4.896100e+10  4.629900e+10  4.385600e+10
            Total Current Assets              1.705050e+11  1.670740e+11  1.658960e+11  1.755520e+11
            Long Term Investments             2.660000e+09  2.755000e+09  2.684000e+09  2.649000e+09
            Net Tangible Assets               6.558200e+10  6.073500e+10  5.644000e+10  5.255400e+10
            Short Term Investments            1.259320e+11  1.253670e+11  1.234920e+11  1.224760e+11
            Net Receivables                   2.269900e+10  2.352500e+10  1.908700e+10  2.952400e+10
            Long Term Debt                    6.286200e+10  6.336100e+10  6.647800e+10  6.666200e+10
            Inventory                         1.644000e+09  1.823000e+09  2.622000e+09  2.063000e+09
            Accounts Payable                  9.246000e+09  8.811000e+09  8.574000e+09  9.382000e+09
            Deferred Long Term Asset Charges           NaN           NaN           NaN  7.536000e+09
        """
        if self._balancesheet[QUARTERLY].empty:
            self._load_financials_data()

        return self._balancesheet[QUARTERLY]

    @property
    def cashflow(self) -> pd.DataFrame:
        """Cashflow for last 4 years

        Eg.:
                                                     2019-06-30    2018-06-30    2017-06-30    2016-06-30
            Investments                                5.400000e+08  6.557000e+09 -1.251100e+10 -1.441700e+10
            Change To Liabilities                      4.694000e+09  7.070000e+09  3.901000e+09  2.653000e+09
            Total Cashflows From Investing Activities -1.577300e+10 -6.061000e+09 -4.678100e+10 -2.395000e+10
            Net Borrowings                            -4.000000e+09 -1.020100e+10  3.145900e+10  1.828300e+10
            Total Cash From Financing Activities      -3.688700e+10 -3.359000e+10  8.408000e+09 -8.393000e+09
            Change To Operating Activities            -1.542000e+09 -4.590000e+08  3.490000e+08 -2.907000e+09
            Issuance Of Stock                          1.142000e+09  1.002000e+09  7.720000e+08  6.680000e+08
            Net Income                                 3.924000e+10  1.657100e+10  2.548900e+10  2.053900e+10
            Change In Cash                            -5.900000e+08  4.283000e+09  1.153000e+09  9.150000e+08
            Repurchase Of Stock                       -1.954300e+10 -1.072100e+10 -1.178800e+10 -1.596900e+10
            Effect Of Exchange Rate                   -1.150000e+08  5.000000e+07  1.900000e+07 -6.700000e+07
            Total Cash From Operating Activities       5.218500e+10  4.388400e+10  3.950700e+10  3.332500e+10
            Depreciation                               1.160000e+10  9.900000e+09  7.800000e+09  5.878000e+09
            Dividends Paid                            -1.381100e+10 -1.269900e+10 -1.184500e+10 -1.100600e+10
            Change To Inventory                        5.970000e+08 -4.650000e+08  5.000000e+07  6.000000e+08
            Change To Account Receivables             -2.812000e+09 -3.862000e+09 -1.216000e+09  5.620000e+08
            Other Cashflows From Financing Activities -6.750000e+08 -9.710000e+08 -1.900000e+08 -3.690000e+08
            Change To Netincome                       -2.521000e+09 -3.054000e+09  1.342000e+09  6.229000e+09
            Capital Expenditures                      -1.392500e+10 -1.163200e+10 -8.129000e+09 -8.343000e+09
            Other Cashflows From Investing Activities           NaN -9.800000e+07 -1.970000e+08  2.030000e+08
        """
        if self._cashflow[YEARLY].empty:
            self._load_financials_data()

        return self._cashflow[YEARLY]

    @property
    def quarterly_cashflow(self) -> pd.DataFrame:
        """Cashflow for last 4 quarters

        Eg.:
                                                     2020-03-31    2019-12-31    2019-09-30    2019-06-30
            Investments                                4.147000e+09 -2.411000e+09  2.071000e+09 -2.925000e+09
            Change To Liabilities                     -1.900000e+08 -2.943000e+09 -3.439000e+09  1.026900e+10
            Total Cashflows From Investing Activities  5.100000e+07 -6.036000e+09 -1.776000e+09 -7.257000e+09
            Net Borrowings                            -3.000000e+09 -1.800000e+07 -2.500000e+09 -1.000000e+09
            Total Cash From Financing Activities      -1.464500e+10 -8.915000e+09 -1.020900e+10 -8.686000e+09
            Change To Operating Activities             8.030000e+08  1.562000e+09 -3.681000e+09  9.580000e+08
            Issuance Of Stock                          3.420000e+08  2.340000e+08  4.270000e+08  3.080000e+08
            Net Income                                 1.075200e+10  1.164900e+10  1.067800e+10  1.318700e+10
            Change In Cash                             2.846000e+09 -4.253000e+09  1.761000e+09  1.440000e+08
            Repurchase Of Stock                       -7.059000e+09 -5.206000e+09 -4.912000e+09 -4.633000e+09
            Effect Of Exchange Rate                   -6.400000e+07  1.800000e+07 -7.200000e+07 -2.100000e+07
            Total Cash From Operating Activities       1.750400e+10  1.068000e+10  1.381800e+10  1.610800e+10
            Depreciation                               3.118000e+09  3.203000e+09  2.971000e+09  2.842000e+09
            Dividends Paid                            -3.876000e+09 -3.886000e+09 -3.510000e+09 -3.521000e+09
            Change To Inventory                        1.810000e+08  7.990000e+08 -5.610000e+08 -1.130000e+08
            Change To Account Receivables              8.910000e+08 -4.203000e+09  1.009000e+10 -1.007000e+10
            Other Cashflows From Financing Activities -1.052000e+09 -3.900000e+07  2.860000e+08  1.600000e+08
            Change To Netincome                        1.184000e+09  1.084000e+09  1.096000e+09 -4.773000e+09
            Capital Expenditures                      -3.767000e+09 -3.545000e+09 -3.385000e+09 -4.051000e+09
        """
        if self._cashflow[QUARTERLY].empty:
            self._load_financials_data()

        return self._cashflow[QUARTERLY]

    @property
    def sustainability(self) -> pd.DataFrame:
        """

        Eg.:
                                             Value
            2020-3
            palmOil                              False
            controversialWeapons                 False
            gambling                             False
            socialScore                           9.87
            nuclear                              False
            furLeather                           False
            alcoholic                            False
            gmo                                  False
            catholic                             False
            socialPercentile                         0
            peerCount                              100
            governanceScore                       5.24
            environmentPercentile                    0
            animalTesting                        False
            tobacco                              False
            totalEsg                             15.55
            highestControversy                       3
            esgPerformance                  UNDER_PERF
            coal                                 False
            pesticides                           False
            adult                                False
            percentile                            7.96
            peerGroup              Software & Services
            smallArms                            False
            environmentScore                      0.44
            governancePercentile                     0
            militaryContract                     False
        """
        if self._sustainability.empty:
            self._load_sustainability()

        return self._sustainability

    @property
    def options_expiration_dates(self):
        if not self._expirations:
            self._download_options()
        return tuple(self._expirations.keys())
