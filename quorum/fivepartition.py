# This cases shows that even though quorum can help set value
# But in the case of network partition, only quorum is not enough
# to ensure the safety property.
# Safety property says that no one in the cluster contains the wrong value,
# while in this case, server 4 contains the wrong value in the case of partition.
# We can resolve this by using paxos.

from quorum.five import ClientProcess, ServerProcess


processes = [ClientProcess(0, [1, 2, 3, 4, 5], 7, 1),
             ServerProcess(1, [1, 2, 3, 4, 5], 3), ServerProcess(2, [1, 2, 3, 4, 5], 3),
             ServerProcess(3, [1, 2, 3, 4, 5], 3), ServerProcess(4, [1, 2, 3, 4, 5], 3),
             ServerProcess(5, [1, 2, 3, 4, 5], 3),
             ClientProcess(6, [5, 1, 2, 3, 4], 7, 2)]
links = dict(((i, j), 1) for i in xrange(7) for j in xrange(i + 1, 7))
commands = ['rmlink 1 5', 'rmlink 2 5', 'rmlink 3 5', 'rmlink 1 4',
            'next 3', 'status', 'next 4']