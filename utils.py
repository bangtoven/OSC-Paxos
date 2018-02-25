class process_state:
	def __init__(self, ip_val, port_val, pid_val):
		self.ip = ip_val
		self.port = int(port_val)
		self.pid = pid_val
		self.fault = False

def read_state(f_name):
	f_in = open(f_name, 'r')
	lines = f_in.readlines()
	process_state_list = []
	line_count = 0
	for line in lines:
		words = line.split()
		ip = words[0]
		port = words[1]
		process_state_temp = process_state(ip, port, line_count)
		process_state_list.append(process_state_temp)
		line_count+=1
	return process_state_list

def getMsg2Send(pid):
	msg = ""
	f_in = open("log_" + str(pid)+".txt",'r')
	lines = f_in.readlines()
	count = 0
	for line in lines:
		view_number, value = line.split(' ')
		if count == 0:
			msg = msg + str(view_number) + ',' + str(value)
		else:
			msg = msg + " " + str(view_number) + ',' + str(value)
	return msg
	
def getSendingMsg(view_list, value_list):
	if len(view_list)>0:
		count = 0
		for view,value in zip(view_list, value_list):
			if count ==0:
				msg = str(view) + "," + str(value)
			else:
				msg = msg + " " + str(view) + ',' + str(value)
			count +=1
	else:
		msg = "empty"
	return msg
		
