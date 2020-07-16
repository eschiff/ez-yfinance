Yahoo! Finance market data downloader
=====================================

.. image:: https://img.shields.io/badge/python-2.7,%203.4+-blue.svg?style=flat
    :target: https://pypi.python.org/pypi/yfinance_ez
    :alt: Python version

.. image:: https://img.shields.io/pypi/v/yfinance_ez.svg?maxAge=60
    :target: https://pypi.python.org/pypi/yfinance_ez
    :alt: PyPi version

.. image:: https://img.shields.io/pypi/status/yfinance_ez.svg?maxAge=60
    :target: https://pypi.python.org/pypi/yfinance_ez
    :alt: PyPi status

.. image:: https://img.shields.io/pypi/dm/yfinance_ez.svg?maxAge=2592000&label=installs&color=%2327B1FF
    :target: https://pypi.python.org/pypi/yfinance_ez
    :alt: PyPi downloads

.. image:: https://img.shields.io/travis/ranaroussi/yfinance_ez/master.svg?maxAge=1
    :target: https://travis-ci.com/ranaroussi/yfinance_ez
    :alt: Travis-CI build status

.. image:: https://www.codefactor.io/repository/github/ranaroussi/yfinance_ez/badge
    :target: https://www.codefactor.io/repository/github/ranaroussi/yfinance_ez
    :alt: CodeFactor

.. image:: https://img.shields.io/github/stars/ranaroussi/yfinance_ez.svg?style=social&label=Star&maxAge=60
    :target: https://github.com/ranaroussi/yfinance_ez
    :alt: Star this repo

.. image:: https://img.shields.io/twitter/follow/aroussi.svg?style=social&label=Follow&maxAge=60
    :target: https://twitter.com/aroussi
    :alt: Follow me on twitter

\

Ever since `Yahoo! finance <https://finance.yahoo.com>`_ decommissioned
their historical data API, many programs that relied on it to stop working.

**yfinance_ez** aimes to solve this problem by offering a reliable, threaded,
and Pythonic way to download historical market data from Yahoo! finance.


NOTE
~~~~

Note from Ezra:

This library was originally created by Ran Aroussi and named ``yfinance``. I encountered
some bugs using it and wasn't able to reach him about updating his package, so I've
renamed it for now to yfinance-ez so I can work on it. I've done some restructuring
and added improved documentation, but the credit for most of the code is NOT mine.

-----

Quick Start
===========

The Ticker module
~~~~~~~~~~~~~~~~~

The ``Ticker`` module, which allows you to access
ticker data in amore Pythonic way:

.. code:: python

    import yfinance_ez as yf

    msft = yf.Ticker("MSFT")

    # get stock info
    msft.info

    # get historical market data for the last quarter
    # This method also accepts start and end dates and/or time intervals
    # so you can customize what you're looking for.
    hist = msft.get_history(period=yf.TimePeriods.Quarter)

    # show actions (dividends, splits) for the last retrieved historical period
    msft.actions

    # show dividends for the last retrieved historical period
    msft.dividends

    # show splits for the last retrieved historical period
    msft.splits

    # show financials 
    msft.financials
    msft.quarterly_financials

    # show major holders
    msft.major_holders

    # show institutional holders
    msft.institutional_holders

    # show balance heet
    msft.balance_sheet
    msft.quarterly_balance_sheet

    # show cashflow
    msft.cashflow
    msft.quarterly_cashflow

    # show earnings
    msft.earnings
    msft.quarterly_earnings

    # show sustainability
    msft.sustainability

    # show analysts recommendations
    msft.recommendations

    # show next event (earnings, etc)
    msft.calendar

    # get option chain for specific expiration
    opt = msft.option_chain('YYYY-MM-DD')
    # data available via: opt.calls, opt.puts

If you want to use a proxy server for downloading data, use:

.. code:: python

    import yfinance_ez as yf

    msft = yf.Ticker("MSFT", proxy="PROXY_SERVER")
    ...

Installation
------------

Install ``yfinance_ez`` using ``pip``:

.. code:: bash

    $ pip install yfinance_ez


Requirements
------------

* `Python <https://www.python.org>`_ >= 3.5+
* `Pandas <https://github.com/pydata/pandas>`_ (tested to work with >=0.23.1)
* `Numpy <http://www.numpy.org>`_ >= 1.11.1
* `requests <http://docs.python-requests.org/en/master/>`_ >= 2.14.2

Legal Stuff
------------

**yfinance_ez** is distributed under the **Apache Software License**. See the `LICENSE.txt <./LICENSE.txt>`_ file in the release for details.


P.S.
------------

Please drop me an note with any feedback you have.

**Ezra Schiff**
