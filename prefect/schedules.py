import itertools
from datetime import datetime, timedelta
from typing import Iterable, List

import croniter

from prefect.utilities.json import Serializable


class Schedule(Serializable):
    """
    Base class for Schedules
    """

    def next(self, n: int, on_or_after: datetime = None) -> List[datetime]:
        raise NotImplementedError("Must be implemented on Schedule subclasses")


class NoSchedule(Schedule):
    """
    No schedule; this Flow will only run on demand.
    """

    def next(self, n: int, on_or_after: datetime = None) -> List[datetime]:
        return []


class IntervalSchedule(Schedule):
    """
    A schedule formed by adding `timedelta` increments to a start_date.
    """

    def __init__(self, start_date: datetime, interval: timedelta) -> None:
        if interval.total_seconds() <= 0:
            raise ValueError("Interval must be positive")
        self.start_date = start_date
        self.interval = interval

    def next(self, n: int, on_or_after: datetime = None) -> List[datetime]:
        if on_or_after is None:
            on_or_after = datetime.utcnow()

        # infinite generator of all dates in the series
        all_dates = (self.start_date + i * self.interval for i in itertools.count(0, 1))
        # filter generator for only dates on or after the requested date
        upcoming_dates = filter(lambda d: d >= on_or_after, all_dates)
        # get the next n items from the generator
        return list(itertools.islice(upcoming_dates, n))


class CronSchedule(Schedule):
    def __init__(self, cron: str) -> None:
        # build cron object to check the cron string - will raise an error if it's invalid
        croniter.croniter(cron)
        self.cron = cron

    def next(self, n: int, on_or_after: datetime = None) -> List[datetime]:
        if on_or_after is None:
            on_or_after = datetime.utcnow()

        # croniter only supports >, not >=, so we subtract a microsecond
        on_or_after -= timedelta(seconds=1)

        cron = croniter.croniter(self.cron, on_or_after)
        return list(itertools.islice(cron.all_next(datetime), n))


class DateSchedule(Schedule):
    def __init__(self, dates: Iterable[datetime]) -> None:
        self.dates = dates

    def next(self, n: int, on_or_after: datetime = None) -> List[datetime]:
        if on_or_after is None:
            on_or_after = datetime.utcnow()
        dates = sorted([d for d in self.dates if d >= on_or_after])
        return dates[:n]
