""" This case shows that even one followers disconnects from the cluster,
the cluster can still move forwards with this situation.
While the disconnected server timeouts, it will try to act as candidate with higher
term, and whether it will succeed depends on whether its log contains the latest committed
log.
No matter whether the disconnected one will become the new leader, the servers receiving
the request_vote will converts to follower state and starts an new election.
"""

from raft.basic import ClientProcess, ServerProcess, SeqRandomNumber

leader_timeouts = [15]
follower_timeouts = [30]

client_commands = {30: [(('set', 1, 2), ('set_result', True), 60)],
                   80: [(('set', 2, 3), ('set_result', True), 60)],
                   180: [(('set', 3, 4), ('set_result', True), 60)],
                   220: [(('get', 2), ('get_result', 3), 60)]}
processes = [ClientProcess(0, client_commands, range(1, 6))] + \
            [ServerProcess(1, range(1, 6), random_num=SeqRandomNumber(leader_timeouts))] + \
            [ServerProcess(i, range(1, 6), random_num=SeqRandomNumber(follower_timeouts))
             for i in xrange(2, 6)]
links = dict(((i, j), 5) for i in xrange(6) for j in xrange(i + 1, 6))
commands = ['next 30', 'status', 'rmlink 1 5', 'next 30', 'status', 'next 50', 'read']
