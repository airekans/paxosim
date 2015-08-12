import random


class ClientProcess(object):
    def __init__(self, id):
        self._id = id
    
    def process(self, input, time):
        print 'ClientProcess_%d[%d] recv: %s' % (self._id, time, input)
        user_input = raw_input('ClientProcess_%d[%d]:' % (self._id, time)).strip()
        output = user_input.split(' ')
        output = {int(output[0]): output[1:]}
        print 'ClientProcess_%d[%d] sent: %s' % (self._id, time, output)
        return output
    
    def get_id(self):
        return self._id
        

class ClusterProcess(object):
    def __init__(self, id, member_ids):
        self._id = id
        self._member_ids = member_ids
        self._member_ids.remove(self._id)
    
    def process(self, input, time):
        print 'ClusterProcess_%d[%d] recv: %s' % (self._id, time, input)
        output = {random.choice(self._member_ids): None}
        print 'ClusterProcess_%d[%d] sent: %s' % (self._id, time, output)
        return output
    
    def get_id(self):
        return self._id


processes = [ClientProcess(0)]
processes.extend([ClusterProcess(id, range(1, 4)) for id in range(1, 4)])
links = {(0, 1): 1, (1, 2): 1, (1, 3): 1, (2, 3): 1}
