class MajorityCheck:
    total = -1

    def __init__(self):
        self.count = 0
        self.decided = False

    def addVoteAndCheck(self):
        if self.decided:
            return False

        self.count += 1
        if self.count > MajorityCheck.total / 2:
            self.decided = True
            return True # give True only once when they passed majority.
        else:
            return False
