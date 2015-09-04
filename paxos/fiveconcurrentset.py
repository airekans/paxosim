""" This case shows that concurrent set in paxos will not result in inconsistency.
In this case, client 1 will propose successfully, but after that client 2 will
propose successfully also, with a higher sequence number.
At this moment, client 1 will find this and abort the current paxos instance,
then retry another new instance, whose propose message arrives before client 2's
accept message.
So after this, client 2 will set failed and client 1 will succeed.
"""

from paxos.basic import ClientProcess, ServerProcess


processes = [ClientProcess(0, {0: [(2, ('set', 1), 'set success', 6)],
                               7: [(2, ('get',), 1, 4)]}),
             ClientProcess(1, {2: [(3, ('set', 2), 'set failed', 6)],
                               9: [(3, ('get',), 1, 4)]})] + \
            [ServerProcess(i, range(2, 7), 3, i) for i in xrange(2, 7)]
links = dict(((i, j), 1) for i in xrange(7) for j in xrange(i + 1, 7))
commands = ['next 7', 'status', 'next 5']
