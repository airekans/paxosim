""" This case is the case mentioned in figure 7 of the Raft paper.
"""

from raft.basic import ClientProcess, ServerProcess, SeqRandomNumber

leader_timeouts = [15]
second_leader_timeouts = [20]
third_leader_timeouts = [25]
follower_timeouts = [30]


client_commands = {30: [(('set', 1, 2), ('set_result', True), 60)],
                   180: [(('set', 2, 3), ('set_result', True), 1000)],
                   300: [(('set', 3, 4), ('set_result', True), 1000)],
                   400: [(('get', 2), ('get_result', 3), 1000)]}
client_commands2 = {220: [(('set', 5, 6), ('set_result', True), 1000)]}
processes = [ClientProcess(0, client_commands, range(1, 6))] + \
            [ServerProcess(1, range(1, 6), random_num=SeqRandomNumber(leader_timeouts)),
             ServerProcess(2, range(1, 6), random_num=SeqRandomNumber(second_leader_timeouts)),
             ServerProcess(3, range(1, 6), random_num=SeqRandomNumber(third_leader_timeouts))] + \
            [ServerProcess(i, range(1, 6), random_num=SeqRandomNumber(follower_timeouts))
             for i in xrange(4, 6)] + \
            [ClientProcess(6, client_commands2, range(1, 6))]
links = dict(((i, j), 5) for i in xrange(7) for j in xrange(i + 1, 7))
commands = ['next 70', 'rmlink 1 2', 'rmlink 1 3', 'rmlink 1 4', 'rmlink 1 5', 'status',
            'next 50', 'addlink 1 3', 'addlink 1 4', 'addlink 1 5', 'status',
            'rmlink 2 3', 'rmlink 2 4', 'rmlink 2 5', 'rmlink 3 4', 'rmlink 3 5', 'rmlink 1 3',
            'next 60', 'rmlink 1 2', 'rmlink 1 3', 'rmlink 1 4', 'rmlink 1 5',
            'addlink 2 3', 'addlink 2 4', 'addlink 2 5', 'addlink 3 4', 'addlink 3 5',
            'next 5', 'status', 'next 40', 'rmlink 2 3', 'rmlink 3 4', 'rmlink 3 5',
            'next 20', 'addlink 1 3', 'addlink 1 4', 'addlink 1 5',
            'rmlink 2 3', 'rmlink 2 4', 'rmlink 2 5', 'status', 'stop 3', 'stop 2',
            'next 50', 'status', 'next 10', 'stop 1', 'stop 4', 'stop 5', 'recover 3',
            'addlink 3 4', 'addlink 3 5', 'next 10', 'status', 'read']

