from majority import MajorityCheck
from message import Message

class Record:
    def __init__(self, view, roundNumber, message):
        self.roundNumber = int(roundNumber)
        self.view = int(view)  # when it is generated.
        self.message = message
        self.majorityCheck = MajorityCheck()
        self.learned = False

    @classmethod
    def fromString(cls, string):
        parsed = string.split("\t")
        view = parsed[0]
        roundNumber = parsed[1]

        cid = parsed[2]
        mid = parsed[3]
        value = parsed[4]
        message = Message(cid, mid, value)

        return cls(view, roundNumber, message)

    def toString(self):
        return "{}\t{}\t{}".format(self.view, self.roundNumber, self.message.toString())
