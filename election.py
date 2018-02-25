from majority import MajorityCheck

class Election:
    def __init__(self, view, roundNumber, latestValue):
        self.view = view  # when it is generated.
        self.roundNumber = roundNumber
        self.majorityCheck = MajorityCheck()
        self.latestView = -1
        self.latestValue = latestValue
        self.decided = False

    @classmethod
    def fromString(cls, string):
        parsed = string.split("\t")
        view = int(parsed[0])
        roundNumber = int(parsed[1])
        latestValue = parsed[2]
        return cls(view, roundNumber, latestValue)

    def toString(self):
        return "{}\t{}\t{}".format(self.view, self.roundNumber, self.latestValue)
