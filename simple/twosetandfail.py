# this case shows that this replicated setting can tolerate one server fail

import simple.two

processes = simple.two.processes
links = simple.two.links
commands = ['next 4', 'status', 'kill 1', 'next 8', 'status']
