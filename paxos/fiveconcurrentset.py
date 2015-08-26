from paxos.basic import ClientProcess, ServerProcess


processes = [ClientProcess(0, {0: [(2, ('set', 1), 'set success', 4)],
                               5: [(2, ('get',), 2, 4)]}),
             ClientProcess(1, {0: [(3, ('set', 2), 'set success', 4)],
                               5: [(3, ('get',), 2, 4)]})] + \
            [ServerProcess(i, range(2, 7), 3, i) for i in xrange(2, 7)]
links = dict(((i, j), 1) for i in xrange(7) for j in xrange(i + 1, 7))
commands = ['next 7', 'status', 'next 5']
