# one of the set will succeed and the other one will fail.
# but the fail one will not set value because it cannot get
# agreement from majority.
# But look at the five partition case, which will set one inconsistent value

import quorum.threeconcurrentset

processes = quorum.threeconcurrentset.processes
links = quorum.threeconcurrentset.links
commands = ['rmlink 2 3', 'rmlink 3 4', 'next 7']
