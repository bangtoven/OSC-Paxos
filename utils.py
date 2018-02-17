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

