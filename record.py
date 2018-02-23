from majority import MajorityCheck

class Record:
    def __init__(self, round, value):
        self.round = round
        self.value = value
        self.majorityCheck = MajorityCheck()
        self.learned = False

    def toString(self):
        "{} {}".format(self.round, self.value)