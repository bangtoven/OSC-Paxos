from majority import MajorityCheck

class Record:
    def __init__(self, roundNumber, value):
        self.roundNumber = roundNumber
        self.value = value
        self.majorityCheck = MajorityCheck()
        self.learned = False
        self.count = 0

    def toString(self):
        "{} {}".format(self.roundNumber, self.value)
