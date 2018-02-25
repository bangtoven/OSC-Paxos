import argparse
import threading
import time
from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import udp_client
from utils import read_state, getSendingMsg
from record import Record
from majority import MajorityCheck

from threading import Lock

class ServerProcess:
    def __init__(self, pid):
        self.mutex = Lock()

        self.pid = pid
        self.leader = -1
        #self.leaderView = -1
        self.viewList = []
        self.valueList = []
        #self.viewList.append(self.view)
        #self.valueList.append(0)
        self.my_view = pid
        self.view = -1

        self.processStates = read_state("servers_config")
        self.sendChannels = []
        for p in self.processStates:
            s = udp_client.SimpleUDPClient(p.ip, p.port)
            self.sendChannels.append(s)
            # self.learnerChannels.append(s)

        self.clientStates = read_state("clients_config")
        self.clientChannels = []
        for p in self.clientStates:
            s = udp_client.SimpleUDPClient(p.ip, p.port)
            self.clientChannels.append(s)

        self.electionCount = -1
        self.electionLatestView = -1
        self.electionLatestValue = None
        self.electionDecided = True

        self.totalNumber = len(self.processStates)
        MajorityCheck.total = self.totalNumber

        # multi-paxos
        self.roundNumber = -1  # index for messages
        self.majorityCheck = []
        self.records = []
        for _ in range(100):
            self.records += [None]

        acceptorValueLog = ""
        self.iAmLeader = False
        
        self.recordDict = {}

    def start(self):
        # initialze listening channels
        d = dispatcher.Dispatcher()
        d.map("/iAmLeader", self.iAmLeader_handler, self)
        d.map("/youAreLeader", self.youAreLeader_handler, self)
        d.map("/valueProposal", self.valueProposal_handler, self)
        d.map("/accept", self.accept_handler, self)
        d.map("/leaderFaulty", self.leaderFaulty_handler, self)
        d.map("/clientRequest", self.clientRequest_handler, self)

        port = self.processStates[self.pid].port
        listen = osc_server.ThreadingOSCUDPServer(("127.0.0.1", port), d)
        listeningThread = threading.Thread(target=listen.serve_forever)
        listeningThread.start()

        print("Process {} started.".format(self.pid))

        if self.pid == 0:
            self.shouldIBeLeader(self.view)


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


    def shouldIBeLeader(self, view):
        #nextView = self.my_view
        #nextRound = self.round+1
        #self.view = view+1
        if (view+1 % self.totalNumber) == self.pid:
            print("Sending iAmLeader.")
            self.electionCount = 0
            self.electionLatestView = -1
            self.electionLatestValue = None
            self.electionDecided = False
            #message = "{}\t{}".format(nextView, nextRound)
            message = "{}".format(view+1)
            self.sendMessageToEveryone("/iAmLeader", message)
        else:
            print("It's not my turn to be a leader.")


    def iAmLeader_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        parsed = recievedMsg.split("\t")
        newView = int(parsed[0])
        #newRound = int(parsed[1])
        newLeader = newView % self.totalNumber
        print("Process {} sent iAmLeader.".format(newLeader))

        if newView >= self.view:
            # update my state
            #previousView = self.view
            #self.viewList[self.roundNumber] = self.view
            #TODO the following two lines are not accurate. Just coz you recieved a request does not mean, he is the leader
            self.view = newView
            
            #self.leader = newLeader
            """
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
            """    
            #sendingMsg = "{}\t{}".format(previousView, previousValue)
            sendingMsg = getSendingMsg(self.viewList, self.valueList)
            print("Sending youAreLeader...")
            leaderChannel = self.sendChannels[newLeader]
            leaderChannel.send_message("/youAreLeader", sendingMsg)
        else:
            print("Invalid leader id.")


    def youAreLeader_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        if self.electionDecided == False:
            """
            parsed = recievedMsg.split("\t")
            for viewNvalue in parsed:
                responseView = int(parsed[0])
                responseValue = parsed[1]

            if responseView > self.electionLatestView and (responseView % self.totalNumber) != self.pid: # not me
                self.electionLatestValue = responseValue
            """
            self.electionCount += 1
            # print("# of votes I got:", self.electionCount)

            if self.electionCount > self.totalNumber / 2:
                self.electionDecided = True
                self.iAmLeader = True
                print("Yeah I become a leader!")
                """
                if self.electionLatestValue is None or self.electionLatestValue == 'None':
                    print("I can propose whatever value I want.")
                    valueToPropose = input("Enter something: ") # get input from console
                else:
                    print("I have to propose value:", self.electionLatestValue)
                    valueToPropose = self.electionLatestValue
                self.propose(valueToPropose)
                """

    def propose(self, cid, value):
        print("Propsing value: {} for client {} ".format(value,cid))
        self.roundNumber += 1
        self.sendMessageToEveryone("/valueProposal", "{}\t{}\t{}\t{}".format(self.view, self.roundNumber, value, cid))


    def valueProposal_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        print("view, round, value, cid", recievedMsg)
        parsed = recievedMsg.split("\t")
        proposerView = int(parsed[0])
        proposedRound = int(parsed[1])
        proposedValue = parsed[2]
        cid = parsed[3]

        if proposerView >= self.view:
            self.view = proposerView # in case you missed the leader election
            # multi-paxos. sequence of data
            #self.appendRecord(proposedRound, proposedValue)
            sendingMsg = "{}\t{}\t{}\t{}".format(self.view, proposedRound, proposedValue, cid)
            self.sendMessageToLearners("/accept", sendingMsg)
        else:
            print("ignore")


    def appendRecord(self, roundNumber, value):
        if self.records[roundNumber] is not None:
            return

        if len(self.records) <= roundNumber:
            print("allocate array for record")
            for _ in range(100):
                self.records += [None]

        self.mutex.acquire()
        try:
            record = Record(roundNumber, value)
            self.records[roundNumber] = record
            self.round = round
        finally:
            self.mutex.release()


    def accept_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        parsed = recievedMsg.split("\t")
        view = parsed[0]
        roundNumber = int(parsed[1])
        value = parsed[2]
        cid = parsed[3]

        #create dict of records, count, if enough, write to log, send to client. In client just print the value
        #go back to the start and see what would happen if the second client sends a msg, accordingly change the view storage etc etc        

        recordStr = str(roundNumber) + "," + str(value)
        print("recordStr: ", recordStr)
        if recordStr not in self.recordDict:
            print("recordString not in dict")
            self.recordDict[recordStr] = Record(roundNumber, value)
            self.recordDict[recordStr].count +=1
        else:
            self.recordDict[recordStr].count +=1

        if self.recordDict[recordStr].learned == False:
            print("recordstr learned is false, count", self.recordDict[recordStr].count)
            if self.recordDict[recordStr].count > self.totalNumber / 2:
                self.recordDict[recordStr].learned = True
                with open("log_"+str(self.pid),'a') as f_log:
                    f_log.write(str(roundNumber))
                    f_log.write(" ")
                    f_log.write(value)
                    f_log.write("\n")
                print("sending msg to client")
                clientChannel = self.clientChannels[int(cid)]
                sendingMsg = "{}\t{}".format(self.pid, value)
                clientChannel.send_message("/processResponse", sendingMsg)

        """
        record = self.records[roundNumber]
        if record is None:
            print("I don't have this record, yet!")
            self.appendRecord(roundNumber, value)
            record = self.records[roundNumber]

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
        """

    def sendLeaderFaulty(self):
        print("sendLeaderFaulty")
        self.sendMessageToEveryone("/leaderFaulty", self.view)


    def leaderFaulty_handler(self, addr, args, recievedMsg):
        if int(recievedMsg) >= self.view:
            print("Someone says my leader/ future leader is faulty.")
            self.shouldIBeLeader(int(recievedMsg))
        else:
            print("It's not my current leader. Maybe I already had dealt with this issue.")


    def clientRequest_handler(self, addr, args, recievedMsg):
        print("\n" + addr)
        print("ClientRequest, msg: ", recievedMsg)
        parsed = recievedMsg.split("\t")
        cid = parsed[0]
        value = parsed[1]
        if (self.view % self.totalNumber == self.pid):
            self.propose(cid, value)

# --------- ServerProcess


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, default=-1, help="The id of the process")
    args = parser.parse_args()

    server = ServerProcess(args.pid)
    server.start()

