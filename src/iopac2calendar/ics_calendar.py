import ics


class Calendar:
    def __init__(self, file: str) -> None:
        self.calendar = ics.Calendar()
        self.file = file

    def add_event(self, name: str, date: str, description: str = ""):
        event = ics.Event(name, date, description=description)
        event.make_all_day()
        self.calendar.events.add(event)

    def write(self):
        with open(self.file, "w") as f:
            f.writelines(self.calendar.serialize_iter())
