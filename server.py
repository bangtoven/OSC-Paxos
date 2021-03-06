import argparse
import threading
import time
from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import udp_client
from utils import read_state, sendMessageWithLoss
from record import Record
from majority import MajorityCheck
from election import Election
from message import Message
from threading import Lock

class ServerProcess:
    def __init__(self, pid, server_count, client_count, skipped_slot, message_loss):
        # test simulation parameters
        self.skipped_slot = skipped_slot
        if message_loss in range (0, 100):
            self.lossRate = message_loss/100.0
        else:
            self.lossRate = 0.0

        self.mutex = Lock()
        self.leaderAlive = False

        self.pid = pid
        self.view = -1

        serverConfig = read_state("servers_config", server_count)
        self.port = serverConfig[self.pid].port
        self.sendChannels = []
        for p in serverConfig:
            s = udp_client.SimpleUDPClient(p.ip, p.port)
            self.sendChannels.append(s)

        clientConfig = read_state("clients_config", client_count)
        self.clientChannels = []
        for p in clientConfig:
            s = udp_client.SimpleUDPClient(p.ip, p.port)
            self.clientChannels.append(s)

        self.totalNumber = len(serverConfig)
        MajorityCheck.total = self.totalNumber
        self.electionStatus = None

        # multi-paxos
        self.lastRound = -1  # index for messages
        self.executedRound = -1
        self.records = []
        self.buffer = []
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
        d.map("/clientRequest", self.clientRequest_handler, self)
        d.map("/requestMissingValue", self.requestMissingValue_handler, self)
        d.map("/missingValue", self.missingValue_handler, self)

        listen = osc_server.ThreadingOSCUDPServer(("127.0.0.1", self.port), d)
        listeningThread = threading.Thread(target=listen.serve_forever)
        listeningThread.start()
        print("Process {} started.".format(self.pid))

        if self.pid == 0:
            self.shouldIBeLeader(self.view)


    def shouldIBeLeader(self, view):
        nextView = view + 1
        if (nextView % self.totalNumber) == self.pid:
            print("Sending iAmLeader, pid: ", self.pid)
            self.electionStatus = Election(nextView, self.lastRound+1, None)
            self.sendMessageToServers("/iAmLeader", self.electionStatus.toString())
        else:
            self.electionStatus = None
            print("It's not my turn to be a leader.")
            self.leaderAlive = False
            t = threading.Timer(3.0, self.checkLeader, [self.view]) 
            t.start()

    def checkLeader(self, view):
        print("inside check leader for view: ", view, ", pid: ", self.pid)
        if self.leaderAlive == False:
            self.view = view+1
            self.sendLeaderFaulty()

    # new leader => acceptor
    def iAmLeader_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        self.leaderAlive = True
        election = Election.fromString(recievedMsg)
        newView = election.view
        newLeader = newView % self.totalNumber
        newRound = election.roundNumber
        print("Process {} sent iAmLeader.".format(newLeader))

        if newView >= self.view:
            previousView = self.view
            self.view = newView

            # send back my previous state
            if self.lastRound == newRound-1: # normal case
                previousValue = None
            elif self.lastRound == newRound:
                record = self.records[newRound]
                #if record.learned == Falise: # only when it is not learned yet
                previousValue = record.message
                #else:
                #    previousValue = None
            elif self.lastRound < newRound:
                print("I am missing something")
                # TODO ask other server for the missing value
                #should send previous value as None and learn it only if it has already been learned or learn it anyways?
                #update learning based on view number and if it learned, mark it (things to learn from others)
                #use for loop to send one by one with round number
                previousValue = None
                #count = (newRound-1) - self.lastRound
                roundNumberTemp = self.lastRound +1
                while roundNumberTemp < newRound:
                    sendingMsg = "server\t{}\t{}".format(str(self.pid),str(roundNumberTemp))
                    self.sendMessageToServers("/requestMissingValue", sendingMsg)
                    roundNumberTemp +=1
            elif self.lastRound > newRound:
                # this guy is missing some records.
                self.sendLeaderFaulty()
                return

            print("Sending youAreLeader...")
            response = Election(previousView, self.lastRound, previousValue)
            leaderChannel = self.sendChannels[newLeader]
            # leaderChannel.send_message("/youAreLeader", response.toString())
            sendMessageWithLoss(leaderChannel, "/youAreLeader", response.toString(), self.lossRate)


    #acceptor => server
    def requestMissingValue_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        parsed = recievedMsg.split("\t")
        name = parsed[0]
        uid = int(parsed[1])
        roundNumber = int(parsed[2])
        if name == server:
            if self.lastRound >= roundNumber and self.records[roundNumber] != None:
                record = self.records[roundNumber]
                #if record.learned:
                responseChannel = self.sendChannels[uid]
                responseChannel.send_message("/missingValue",record.toString())

        elif self.executedRound >= roundNumber:
            record = self.records[roundNumber]
            responseChannel = self.clientChannels[uid]
            responseChannel.send_message("/missingValue",record.toString())

    def sendAccept(self, record):
        if self.lastRound < record.roundNumber:
            self.lastRound = record.roundNumber # why is the lastround jumping to round number

        self.sendMessageToServers("/accept", record.toString())

    #server => requester
    def missingValue_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        #doubt: should we check if enough records are available and add them?
        recieved = Record.fromString(recievedMsg)
        record = self.records[recieved.roundNumber]
        if record == None:
            #recieved.learned = True
            self.sendAccept(recieved)
            #self.records[recieved.roundNumber] = recieved #doubt: what happens to the lastround, how to update it?
        # elif record.learned == False:
        #     if recieved.view >= record.view:
        #         recieved.learned = True
        #         self.records[recieved.roundNumber] = recieved
        #         if self.lastRound < recieved.roundNumber:
        #             self.lastRound = recieved.roundNumber


    # acceptor => new leader
    def youAreLeader_handler(self, addr, args, recievedMsg):
        print("\n" + addr)
        if self.electionStatus is not None and self.electionStatus.decided == False:
            response = Election.fromString(recievedMsg)
            if response.view > self.electionStatus.view and (response.view % self.totalNumber) != self.pid:  # not me
                self.electionStatus.latestValue = Message.fromString(response.latestValue)

            if self.electionStatus.majorityCheck.addVoteAndCheck():
                self.electionStatus.decided = True
                print("Yeah, I become a leader, pid: ", self.pid)
                #self.leaderAlive = True

                hole = self.detectHole()
                if hole != -1:
                    filling = Record(self.view, hole, self.buffer[0])
                    self.propose(filling)

                if self.electionStatus.latestValue is not None: #doubt, why is this here?
                    latestMsg = Message(self.electionStatus.latestValue)
                    fromPrevious = Record(self.view, response.roundNumber, latestMsg)
                    self.propose(fromPrevious)

                print("Ready to process client requests.")

    # client => all processes
    def clientRequest_handler(self, addr, args, recievedMsg):
        print("\n" + addr)
        print("ClientRequest, msg: ", recievedMsg)
        message = Message.fromString(recievedMsg)
        if (self.view % self.totalNumber == self.pid): # leader's work
            self.lastRound += 1
            if self.lastRound == self.skipped_slot:
                print("simulate sequence skipping. incrementing the round, but not proposing the value.")
            else:
                record = Record(self.view, self.lastRound, message)
                self.propose(record)
        else: # other processes
            self.buffer.append(message)

    # leader => acceptor
    def propose(self, record):
        print("Propose value:", record.toString())
        self.sendMessageToServers("/valueProposal", record.toString())

    # leader => acceptor
    def valueProposal_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        record = Record.fromString(recievedMsg)

        if record.view >= self.view:
            self.view = record.view # in case you missed the leader election
            # self.appendRecord(record)
            self.sendAccept(record)
            # self.sendMessageToServers("/accept", record.toString()) # to learners

    # acceptor => learner
    def accept_handler(self, addr, args, recievedMsg):
        print("\n"+addr)
        received = Record.fromString(recievedMsg)
        roundNumber = received.roundNumber
        record = self.records[roundNumber]
        if record is None:
            print("I don't have this record, yet.")
            if len(self.records) <= roundNumber:
                print("allocate array for record")
                for _ in range(100):
                    self.records += [None]

            self.mutex.acquire()
            try:
                self.records[roundNumber] = received
            finally:
                self.mutex.release()

            record = self.records[roundNumber]

        if record.majorityCheck.addVoteAndCheck() == True:
            record.learned = True

            if record.message in self.buffer:
                self.buffer.remove(record.message)

            print("Learned:", record.toString())
            
            if self.detectHole() != -1:
                print("do something")
                self.sendLeaderFaulty()
            else:
                print("no holes. sending msg to client")
                while self.executedRound < self.lastRound:
                    with open("log_server_" + str(self.pid), 'a') as f_log:
                        f_log.write(record.toString() + "\n")
                    self.executedRound += 1
                    recordToExecute = self.records[self.executedRound]
                    self.sendMessageToClients(recordToExecute.toString())


    def sendLeaderFaulty(self):
        print("sendLeaderFaulty")
        self.sendMessageToServers("/leaderFaulty", self.view)


    def leaderFaulty_handler(self, addr, args, recievedMsg):
        if int(recievedMsg) >= self.view:
            print("Someone says my leader/ future leader is faulty.")
            self.shouldIBeLeader(int(recievedMsg))
        else:
            print("It's not my current leader. Maybe I already had dealt with this issue, pid: {} and view: {} ".format(self.pid, self.view))


    def sendMessageToServers(self, label, value, exceptMe=False):
        for i, s in enumerate(self.sendChannels):
            if i == self.pid and exceptMe:
                continue
            # s.send_message(label, value)
            sendMessageWithLoss(s, label, value, self.lossRate)


    def sendMessageToClients(self, message):
        for c in self.clientChannels:
            # c.send_message("/processResponse", message)
            sendMessageWithLoss(c, "/processResponse", message, self.lossRate)


    def detectHole(self):
        for i in range(self.lastRound):
            if self.records[i] is None:
                return i

        return -1


# --------- ServerProcess


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, default=-1, help="The id of the process")
    parser.add_argument("--server_count", type=int, default=3, help="number of servers")
    parser.add_argument("--client_count", type=int, default=2, help="number of clients")
    parser.add_argument("--skipped_slot", type=int, default=-1, help="test4: force primary to skip for sequence x")
    parser.add_argument("--message_loss", type=int, default=0, help="test5: randomly drop p%. range(0,100)")
    args = parser.parse_args()

    server = ServerProcess(args.pid, args.server_count, args.client_count, args.skipped_slot, args.message_loss)
    server.start()

