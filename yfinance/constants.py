from enum import Enum


YEARLY = 'yearly'
QUARTERLY = 'quarterly'

class TimePeriods(Enum):
    Day='1d'
    Week = '5d'
    Month = '1mo'
    Quarter = '3mo'
    HalfYear = '6mo'
    Year = '1y'
    TwoYears = '2y'
    FiveYears = '5y'
    TenYears = '10y'
    YTD = 'ytd'
    Max = 'max'

class TimeIntervals(Enum):
    Minute = '1m'
    TwoMinutes = '2m'
    FiveMinutes = '5m'
    FifteenMinutes = '15m'
    HalfHour = '30m'
    Hourly = '60m'
    HourAndAHalf = '90m'
    Daily = '1d'
    FiveDays = '5d'
    Weekly = '1wk'
    Monthly = '1mo'
    Quarterly = '3mo'
