from majority import MajorityCheck

class Record:
    def __init__(self, view, roundNumber, cid, message):
        self.roundNumber = roundNumber
        self.view = view # when it is generated.
        self.cid = cid # who sent it
        self.message = message 
        self.majorityCheck = MajorityCheck()
        self.learned = False
        self.count = 0

    def toString(self):
        "{}\t{}\t{}\t{}".format(self.view, self.roundNumber, self.value, self.cid)
