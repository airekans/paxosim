# one of the set will success and the other one will fail.
# because one of the set will succeed with majority number, while the other
# will just get only one(itself) promise to set the value.

from quorum.three import ClientProcess, ServerProcess

processes = [ClientProcess(0, [2, 3, 4], 7), ClientProcess(1, [3, 4, 2], 7)] + \
    [ServerProcess(i, [2, 3, 4], 3) for i in xrange(2, 5)]
links = dict(((i, j), 1) for i in xrange(5) for j in xrange(i + 1, 5))
commands = ['next 2', 'status', 'next 1', 'status', 'next 5']
