""" This case shows that if the proposer itself has been partitioned from
other agents after the agents has promised to it, then the only one to
accept its value is itself.
In this case, the consensus for this paxos instance is not finished,
because no majority of the agents have accepted it.
And in this cases, the agents in the other partitions can also reach
consensus because the majority of the agents still there.
"""

from paxos.basic import ClientProcess, ServerProcess


processes = [ClientProcess(0, {0: [(2, ('set', 1), 'set failed', 6)],
                               7: [(2, ('get',), 'get failed', 6)]}),
             ClientProcess(1, {2: [(3, ('set', 2), 'set success', 6)],
                               9: [(3, ('get',), 2, 4)]})] + \
            [ServerProcess(i, range(2, 7), 3, i) for i in xrange(2, 7)]
links = dict(((i, j), 1) for i in xrange(7) for j in xrange(i + 1, 7))
commands = ['next 2', 'status'] + [('rmlink 2 %d' % i) for i in xrange(3, 7)] + \
           ['next 1', 'status', 'next 7', 'status', 'next 7', 'status', 'next 10']

