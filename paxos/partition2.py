""" This case shows that even though there're 2 agents being partitioned,
paxos instance can still proceed because the majority(3 here) is still
functional.
You may ask what happen if the network repairs after that.
To check this, you can see partitionandrecover.
"""

from paxos.basic import ClientProcess, ServerProcess


processes = [ClientProcess(0, {0: [(2, ('set', 1), 'set failed', 7)],
                               7: [(2, ('get',), 'get failed', 6)]}),
             ClientProcess(1, {2: [(4, ('set', 2), 'set success', 8)],
                               9: [(4, ('get',), 2, 4)]})] + \
            [ServerProcess(i, range(2, 7), 3, i) for i in xrange(2, 7)]
links = dict(((i, j), 1) for i in xrange(7) for j in xrange(i + 1, 7))
commands = ['next 2', 'status'] + [('rmlink 2 %d' % i) for i in xrange(4, 7)] + \
           [('rmlink 3 %d' % i) for i in xrange(4, 7)] + \
           ['next 1', 'status', 'next 7', 'status', 'next 7', 'status', 'next 10']