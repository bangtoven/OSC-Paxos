import argparse
import threading
import time
from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import udp_client
from utils import read_state
from record import Record
from majority import MajorityCheck

from threading import Lock

class ServerProcess:
    def __init__(self, pid):
        self.mutex = Lock()

        self.pid = pid
        self.leader = -1
        self.view = -1

        self.processStates = read_state("config")
        self.sendChannels = []
        for p in self.processStates:
            s = udp_client.SimpleUDPClient(p.ip, p.port)
            self.sendChannels.append(s)
            # self.learnerChannels.append(s)

        self.totalNumber = len(self.processStates)
        MajorityCheck.total = self.totalNumber

        self.records = []  # multi-paxos
        self.round = -1  # index for messages
        self.majorityCheck = []

        self.electionCount = -1
        self.electionLatestView = -1
        self.electionLatestValue = None
        self.electionDecided = True


    def start(self):
        # initialze listening channels
        d = dispatcher.Dispatcher()
        d.map("/iAmLeader", self.iAmLeader_handler, self)
        d.map("/youAreLeader", self.youAreLeader_handler, self)
        d.map("/valueProposal", self.valueProposal_handler, self)
        d.map("/accept", self.accept_handler, self)

        port = self.processStates[self.pid].port
        listen = osc_server.ThreadingOSCUDPServer(("127.0.0.1", port), d)
        listeningThread = threading.Thread(target=listen.serve_forever)
        listeningThread.start()

        print("Process {} started.".format(self.pid))

        if self.pid == 0:
            self.sendIAmLeader()


    def sendMessageToEveryone(self, label, value, exceptMe=False):
        # for s in sendChannels:
        # 	s.send_message(label, value)
        for i, s in enumerate(self.sendChannels):
            if i == self.pid and exceptMe:
                continue
            s.send_message(label, value)
            time.sleep(0.5)


    def sendMessageToLearners(self, label, value):
        self.sendMessageToEveryone(label, value)
        # for s in self.learnerChannels:
        #     s.send_message(label, value)
        #     time.sleep(0.5)


    def sendIAmLeader(self):
        nextView = self.view+1
        nextRound = self.round+1
        if (nextView % self.totalNumber) == self.pid:
            print("Sending iAmLeader.")
            self.electionCount = 0
            self.electionLatestView = -1
            self.electionLatestValue = None
            self.electionDecided = False
            message = "{} {}".format(nextView, nextRound)
            self.sendMessageToEveryone("/iAmLeader", message)
        else:
            print("It's not my turn to be a leader.")


    def iAmLeader_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        parsed = recievedMsg.split()
        newView = int(parsed[0])
        newRound = int(parsed[1])
        newLeader = newView % self.totalNumber
        print("Process {} sent iAmLeader.".format(newLeader))

        if newView >= self.view:
            # update my state
            previousView = self.view
            self.view = newView
            self.leader = newLeader

            # send back my previous state
            previousValue = None
            if len(self.records) > newRound: # I need better understanding on multi-paxos for this.
                previousRecord = self.records[newRound]
                previousValue = previousRecord.value

            print("Sending youAreLeader...")
            leaderChannel = self.sendChannels[newLeader]
            sendingMsg = "{} {}".format(previousView, previousValue)
            leaderChannel.send_message("/youAreLeader", sendingMsg)
        else:
            print("Invalid leader id.")


    def youAreLeader_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        if self.electionDecided == False:
            parsed = recievedMsg.split()
            responseView = int(parsed[0])
            responseValue = parsed[1]

            if responseView > self.electionLatestView:
                self.electionLatestValue = responseValue

            self.electionCount += 1
            # print("# of votes I got:", self.electionCount)

            if self.electionCount > self.totalNumber / 2:
                self.electionDecided = True
                print("Yeah I become a leader!")
                if self.electionLatestValue == None:
                    print("I can propose whatever value I want.")
                    valueToPropose = input("Enter something: ") # get input from console
                else:
                    print("I have to propose value:", self.electionLatestValue)
                    valueToPropose = self.electionLatestValue
                self.propose(valueToPropose)


    def propose(self, value):
        print("Propsing value: ", value)
        self.round += 1
        self.sendMessageToEveryone("/valueProposal", "{} {} {}".format(self.view, self.round, value))


    def valueProposal_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        parsed = recievedMsg.split()
        proposerView = int(parsed[0])
        proposedRound = int(parsed[1])
        proposedValue = parsed[2]

        if proposerView >= self.view:
            # multi-paxos. sequence of data
            self.appendRecord(proposedRound, proposedValue)
            self.view = proposerView
            self.round = proposedRound
            sendingMsg = "{} {} {}".format(self.view, self.round, proposedValue)
            self.sendMessageToLearners("/accept", sendingMsg)
        else:
            print("ignore")


    def appendRecord(self, round, value):
        self.mutex.acquire()
        try:
            while len(self.records) < round:
                self.records += [None]

            if len(self.records) > round:
                print("!!!!!!!!!!! something goes wrong? how does the Paxos deal with this? !!!!!!!!!!!!")

            record = Record(round, value)
            self.records += [record]
        finally:
            self.mutex.release()


    def accept_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        parsed = recievedMsg.split()
        view = parsed[0]
        round = int(parsed[1])
        value = int(parsed[2])

        # need to check majority
        if len(self.records) < round:
            self.appendRecord(round, value) # could have been dropped or something

        record = self.records[round]
        if record.majorityCheck.addVoteAndCheck() == True:
            print("Majority accepted it.")

            print("view: ", view)
            print("round: ", round)
            print("value accepted so far")
            for r in self.records:
                print(r.value)
            print("----")

            # for testing
            if (self.view % self.totalNumber) == self.pid:
                valueToPropose = input("Propose more: ")  # get input from console
                self.propose(valueToPropose)


# --------- ServerProcess


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, default=-1, help="The id of the process")
    args = parser.parse_args()

    server = ServerProcess(args.pid)
    server.start()

