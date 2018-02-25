from majority import MajorityCheck

class Record:
    def __init__(self, view, roundNumber, cid, value):
        self.roundNumber = int(roundNumber)
        self.view = int(view)  # when it is generated.
        self.cid = int(cid) # who sent it
        self.value = value
        self.majorityCheck = MajorityCheck()
        self.learned = False

    @classmethod
    def fromString(cls, string):
        parsed = string.split("\t")
        view = int(parsed[0])
        roundNumber = int(parsed[1])
        cid = int(parsed[2])
        message = parsed[3]
        return cls(view, roundNumber, cid, message)

    def toString(self):
        return "{}\t{}\t{}\t{}".format(self.view, self.roundNumber, self.cid, self.value)
