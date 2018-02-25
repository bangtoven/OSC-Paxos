class Message:
    def __init__(self, cid, mid, value):
        self.cid = int(cid) # who sent it
        self.mid = int(mid) # message id of that specific client
        self.value = value

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(self, other.__class__):
            return self.cid == other.cid and self.mid == other.mid
        return NotImplemented

    @classmethod
    def fromString(cls, string):
        parsed = string.split("\t")
        cid = int(parsed[0])
        mid= int(parsed[1])
        value = parsed[2]
        return cls(cid, mid, value)

    def toString(self):
        return "{}\t{}\t{}".format(self.cid, self.mid, self.value)
