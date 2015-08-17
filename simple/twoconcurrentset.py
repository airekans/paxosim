# this case will fail because in concurrent set the replica cannot
# get agreement from other.
# In this case we cannot make any progress.
# To resolve this, we have to add one more server and make progress
# if the majority of the replicas agree on the value.

from simple.two import ClientProcess, ServerProcess

processes = [ClientProcess(0, [1, 2], 5),
             ServerProcess(1, [1, 2], 3), ServerProcess(2, [1, 2], 3),
             ClientProcess(3, [2, 1], 5)]
links = {(0, 1): 1, (0, 2): 1, (1, 2): 1, (3, 1): 1, (3, 2): 1}
commands = ['next 4', 'status']
