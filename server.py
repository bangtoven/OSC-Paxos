import argparse
import math
import threading
import time
from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import osc_message_builder
from pythonosc import udp_client
from utils import process_state, read_state


class ServerProcess:
	pid = -1
	processStates = []
	sendChannels = []
	learnerChannels = []

	totalNumber = 0
	leader = -1
	view = -1
	value = None

	electionCount = -1
	electionLatestView = -1
	electionLatestValue = None
	electionDecided = True
	
	def __init__(self, pid):
		self.pid = pid
		
		self.processStates = read_state("config")
		self.totalNumber = len(self.processStates)
		
		for p in self.processStates:
			s = udp_client.SimpleUDPClient(p.ip, p.port)
			self.sendChannels.append(s)
			self.learnerChannels.append(s)


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


	def sendIAmLeader(self):
		print("Sending iAmLeader.")
		self.electionCount = 0
		self.electionLatestView = -1
		self.electionLatestValue = None
		self.electionDecided = False
		self.sendMessageToEveryone("/iAmLeader", 0, False)
		#why is 0 being sent here? we should send leader number, what is leader number?

	def sendMessageToEveryone(self, label, value, exceptMe=True):
		# for s in sendChannels:
		# 	s.send_message(label, value)
		for i, s in enumerate(self.sendChannels):
			if i==self.pid and exceptMe:
				continue
			s.send_message(label, value)
			time.sleep(0.5)

	def sendMessageToLearners(self, label, value):
		for s in self.learnerChannels:
			s.send_message(label, value)
			time.sleep(0.5)

	def iAmLeader_handler(self, addr, args, newView):
		print()
		print(addr)
		newLeader = newView % self.totalNumber
		print("Process {} sent iAmLeader.".format(newLeader))
		if newView > self.view:
			# update my state
			previousView = self.view
			self.view = newView
			self.leader = newLeader
			# send back my previous state
			leaderChannel = self.sendChannels[newLeader]
			print("Sending youAreLeader...")
			leaderChannel.send_message("/youAreLeader", "{} {}".format(previousView, self.value))


	def youAreLeader_handler(self, addr, args, response):
		print()
		print(addr)
		if self.electionDecided:
			print("I already got majority vote to be a leader.")
		else:
			parsed = response.split()
			responseView = int(parsed[0])
			responseValue = parsed[1]

			if responseView > self.electionLatestView:
				self.electionLatestValue = responseValue
			
			self.electionCount += 1
			print("# of votes I got:", self.electionCount)

			if self.electionCount > self.totalNumber/2:
				self.electionDecided = True
				print("Yeah I become a leader!")
				if self.electionLatestValue == None:
					print("I can propose whatever value I want.")
					valueToPropose = 19
				else:
					print("I have to propose value:", self.electionLatestValue)
					valueToPropose = self.electionLatestValue
				self.propose(valueToPropose)


	def propose(self, valueToPropose):
		print("Propsing value: ", valueToPropose)
		self.sendMessageToEveryone("/valueProposal", "{} {} {}".format(self.pid, self.view, valueToPropose), False)


	def valueProposal_handler(self, addr, args, viewAndValue):
		print()
		print(addr)
		parsed = viewAndValue.split()
		proposerPid = int(parsed[0])
		proposerView = int(parsed[1])
		proposedValue = parsed[2]
		
		if proposerView >= self.view:
			print("accepted value")
			self.sendMessageToLearners("/accept", "{} {}".format(proposerView, proposedValue))


	def accept_handler(self, addr, args, viewAndValue):
		print()
		print(addr)
		parsed = viewAndValue.split()
		view = parsed[0]
		value = parsed[1]
		print("view", view)
		print("value accepted: ", value)
# --------- ServerProcess


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--pid", type=int, default=-1, help="The id of the process")
	args = parser.parse_args()

	server = ServerProcess(args.pid)
	server.start()
	
