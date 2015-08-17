# this case will fail because ServerProcess cannot make progress
# if the other replica does not respond.
# If we want to resolve this, we should add one replica and
# if the majority of the replicas agree to set the value,
# then we progress.

from simple.two import ClientProcess, ServerProcess

processes = [ClientProcess(0, [1, 2], 5),
             ServerProcess(1, [1, 2], 3), ServerProcess(2, [1, 2], 3),
             ClientProcess(3, [2, 1], 5)]
links = {(0, 1): 1, (0, 2): 1, (1, 2): 1, (3, 1): 1, (3, 2): 1}
commands = ['rmlink 1 2', 'next 5', 'status']
