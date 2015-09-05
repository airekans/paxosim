""" This case shows that even though network partitino will
let the agents in the partition not aware of the changes in the other partition,
once the network recover, they can learn the changes from the latest agents.
So there will not be inconsistency when network partition happens.
"""

from paxos.basic import ClientProcess, ServerProcess


processes = [ClientProcess(0, {0: [(2, ('set', 1), 'set failed', 7)],
                               7: [(2, ('get',), 'get failed', 6)],
                               14: [(2, ('set', 1), 'set failed', 7)],
                               22: [(3, ('get',), 2, 6)]}),
             ClientProcess(1, {2: [(4, ('set', 2), 'set success', 8)],
                               9: [(4, ('get',), 2, 4)]})] + \
            [ServerProcess(i, range(2, 7), 3, i) for i in xrange(2, 7)]
links = dict(((i, j), 1) for i in xrange(7) for j in xrange(i + 1, 7))
commands = ['next 2', 'status'] + [('rmlink 2 %d' % i) for i in xrange(4, 7)] + \
           [('rmlink 3 %d' % i) for i in xrange(4, 7)] + \
           ['next 12', 'status'] + \
           [('addlink 2 %d' % i) for i in xrange(4, 7)] + \
           [('addlink 3 %d' % i) for i in xrange(4, 7)] + \
           ['next 10', 'status', 'next 7', 'status', 'next 10']
