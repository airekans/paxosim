from quorum.three import ClientProcess, ServerProcess


processes = [ClientProcess(0, [1, 2, 3, 4, 5], 5),
             ServerProcess(1, [1, 2, 3, 4, 5], 3), ServerProcess(2, [1, 2, 3, 4, 5], 3),
             ServerProcess(3, [1, 2, 3, 4, 5], 3), ServerProcess(4, [1, 2, 3, 4, 5], 3),
             ServerProcess(5, [1, 2, 3, 4, 5], 3)]
links = dict(((i, j), 1) for i in xrange(6) for j in xrange(i + 1, 6))
commands = ['next 5', 'status', 'next 5', 'status']
