# this case will succeed because quorum of 3 can stand 1 failure

import quorum.three

processes = [quorum.three.ClientProcess(0, [1, 2, 3], 7)] + quorum.three.processes[1:]
links = quorum.three.links
commands = ['next 1', 'kill 3', 'status', 'next 10']
