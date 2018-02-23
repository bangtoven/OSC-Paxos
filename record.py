class Record:
    round = -1  # index of the message in the system
    value = ""

    def __init__(self, round, value):
        self.round = round
        self.value = value

    def toString(self):
        "{} {}".format(self.round, self.value)