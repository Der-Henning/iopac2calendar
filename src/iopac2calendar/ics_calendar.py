import warnings
from datetime import date, datetime, time, timedelta

import ics


class Calendar:
    def __init__(self, file: str) -> None:
        self.calendar = ics.Calendar(creator="iopac2calendar")
        self.file = file

    def add_event(self, name: str, date: date, description: str = "", alerts: bool = True):
        event = ics.Event(name, date, description=description)
        event.make_all_day()
        if alerts:
            alert_date = datetime.combine(date - timedelta(days=1), time(9)).astimezone()
            event.alarms.append(ics.alarm.DisplayAlarm(alert_date, repeat=1, duration=timedelta(days=1)))
        self.calendar.events.add(event)

    def write(self):
        with open(self.file, "w") as f, warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=FutureWarning)
            f.write(self.calendar.serialize())
