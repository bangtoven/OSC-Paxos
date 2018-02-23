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

        self.electionCount = -1
        self.electionLatestView = -1
        self.electionLatestValue = None
        self.electionDecided = True

        self.totalNumber = len(self.processStates)
        MajorityCheck.total = self.totalNumber

        # multi-paxos
        self.round = -1  # index for messages
        self.majorityCheck = []
        self.records = []
        for _ in range(100):
            self.records += [None]




    def start(self):
        # initialze listening channels
        d = dispatcher.Dispatcher()
        d.map("/iAmLeader", self.iAmLeader_handler, self)
        d.map("/youAreLeader", self.youAreLeader_handler, self)
        d.map("/valueProposal", self.valueProposal_handler, self)
        d.map("/accept", self.accept_handler, self)
        d.map("/leaderFaulty", self.leaderFaulty_handler, self)

        port = self.processStates[self.pid].port
        listen = osc_server.ThreadingOSCUDPServer(("127.0.0.1", port), d)
        listeningThread = threading.Thread(target=listen.serve_forever)
        listeningThread.start()

        print("Process {} started.".format(self.pid))

        if self.pid == 0:
            self.shouldIBeLeader()


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


    def shouldIBeLeader(self):
        nextView = self.view+1
        nextRound = self.round+1
        if (nextView % self.totalNumber) == self.pid:
            print("Sending iAmLeader.")
            self.electionCount = 0
            self.electionLatestView = -1
            self.electionLatestValue = None
            self.electionDecided = False
            message = "{}\t{}".format(nextView, nextRound)
            self.sendMessageToEveryone("/iAmLeader", message)
        else:
            print("It's not my turn to be a leader.")


    def iAmLeader_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        parsed = recievedMsg.split("\t")
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
            if self.round == newRound-1: # normal case
                previousValue = None
            elif self.round == newRound:
                record = self.records[newRound]
                if record.learned: # only when it is learned by learner?
                    previousValue = record.value
            elif self.round < newRound:
                # it means I miss something
                previousValue = None # first, you agree this one to be a leader
                # self.request_other_process_for_missing_rounds_values(myLastRound)
                # then other process will give you missing values
            else:
                # self.round > newRound.
                # acceptor has more information.
                # the leader is missing some records.
                # How to deal with this situation?
                # previousValue = "multiple values???"
                # => send leader faulty, and expect other process (or me), which is most up to date, becomes a leader
                self.sendLeaderFaulty()
                return
                
            sendingMsg = "{}\t{}".format(previousView, previousValue)
            print("Sending youAreLeader...")
            leaderChannel = self.sendChannels[newLeader]
            leaderChannel.send_message("/youAreLeader", sendingMsg)
        else:
            print("Invalid leader id.")


    def youAreLeader_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        if self.electionDecided == False:
            parsed = recievedMsg.split("\t")
            responseView = int(parsed[0])
            responseValue = parsed[1]

            if responseView > self.electionLatestView and (responseView % self.totalNumber) != self.pid: # not me
                self.electionLatestValue = responseValue

            self.electionCount += 1
            # print("# of votes I got:", self.electionCount)

            if self.electionCount > self.totalNumber / 2:
                self.electionDecided = True
                print("Yeah I become a leader!")
                if self.electionLatestValue is None or self.electionLatestValue == 'None':
                    print("I can propose whatever value I want.")
                    valueToPropose = input("Enter something: ") # get input from console
                else:
                    print("I have to propose value:", self.electionLatestValue)
                    valueToPropose = self.electionLatestValue
                self.propose(valueToPropose)


    def propose(self, value):
        print("Propsing value: ", value)
        self.round += 1
        self.sendMessageToEveryone("/valueProposal", "{}\t{}\t{}".format(self.view, self.round, value))


    def valueProposal_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        print(recievedMsg)
        parsed = recievedMsg.split("\t")
        proposerView = int(parsed[0])
        proposedRound = int(parsed[1])
        proposedValue = parsed[2]

        if proposerView >= self.view:
            self.view = proposerView # in case you missed the leader election
            # multi-paxos. sequence of data
            self.appendRecord(proposedRound, proposedValue)
            sendingMsg = "{}\t{}\t{}".format(self.view, self.round, proposedValue)
            self.sendMessageToLearners("/accept", sendingMsg)
        else:
            print("ignore")


    def appendRecord(self, round, value):
        if self.records[round] is not None:
            return

        if len(self.records) <= round:
            print("allocate array for record")
            for _ in range(100):
                self.records += [None]

        self.mutex.acquire()
        try:
            record = Record(round, value)
            self.records[round] = record
            self.round = round
        finally:
            self.mutex.release()


    def accept_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        parsed = recievedMsg.split("\t")
        view = parsed[0]
        round = int(parsed[1])
        value = parsed[2]

        record = self.records[round]
        if record is None:
            print("I don't have this record, yet!")
            self.appendRecord(round, value)
            record = self.records[round]

        if record.majorityCheck.addVoteAndCheck() == True:
            print("Majority accepted it.")
            record.learned = True

            print("view: ", view)
            print("round: ", round)
            print("value accepted so far")
            for r in self.records:
                if r is not None:
                    print(r.value)
            print("----")

            # for testing
            if (self.view % self.totalNumber) == self.pid:
                valueToPropose = input("Propose more::::::: ")  # get input from console
                if valueToPropose == "change":
                    self.sendLeaderFaulty()
                else:
                    self.propose(valueToPropose)


    def sendLeaderFaulty(self):
        print("sendLeaderFaulty")
        self.sendMessageToEveryone("/leaderFaulty", self.view)


    def leaderFaulty_handler(self, addr, args, recievedMsg):
        if int(recievedMsg) == self.view:
            print("Someone says my leader is faulty.")
            self.shouldIBeLeader()
        else:
            print("It's not my current leader. Maybe I already had dealt with this issue.")



# --------- ServerProcess


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, default=-1, help="The id of the process")
    args = parser.parse_args()

    server = ServerProcess(args.pid)
    server.start()

