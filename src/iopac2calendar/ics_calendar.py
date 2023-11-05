import ics


class Calendar:
    def __init__(self, file: str) -> None:
        self.calendar = ics.Calendar()
        self.file = file

    def add_event(self, name: str, begin: str):
        event = ics.Event(name, begin)
        self.calendar.events.add(event)

    def write(self):
        with open(self.file, "w") as f:
            f.writelines(self.calendar.serialize_iter())
