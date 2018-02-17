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


	def start(self):
		# initialze listening channels
		d = dispatcher.Dispatcher()
		d.map("/iAmLeader", self.iAmLeader_handler, self)
		d.map("/youAreLeader", self.youAreLeader_handler, self)

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


	def sendMessageToEveryone(self, label, value, exceptMe=True):
		# for s in sendChannels:
		# 	s.send_message(label, value)
		for i, s in enumerate(self.sendChannels):
			if i==self.pid and exceptMe:
				continue
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
			leaderChannel.send_message('/youAreLeader', "{} {}".format(previousView, self.value))


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
				else:
					print("I have to propose value:", self.electionLatestValue)

# --------- ServerProcess


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--pid", type=int, default=-1, help="The id of the process")
	args = parser.parse_args()

	server = ServerProcess(args.pid)
	server.start()
