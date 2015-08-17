class ClientProcess(object):
    def __init__(self, proc_id, server_ids, timeout):
        self._id = proc_id
        self._server_ids = server_ids
        self._server_states = dict((svr_id, True) for svr_id in server_ids)
        self._sent_requests = {}
        self._timeout = timeout

    def process(self, _input, time):
        if time == 0:
            for svr_id in self._server_ids:
                if self._server_states[svr_id]:
                    self._sent_requests[svr_id] = (time, 'set')
                    return {svr_id: ('set', 1)}
            assert False
        
        for svr_id, msgs in _input.iteritems():
            assert svr_id in self._sent_requests
            assert time - self._sent_requests[svr_id][0] < self._timeout
            if self._sent_requests[svr_id][1] == 'set':
                assert msgs == ['set success']
                self._sent_requests[svr_id] = (time, 'get')
                return {svr_id: ('get',)}
            else:
                assert msgs == [1]
                print 'get result', msgs
                self._sent_requests = {}
                # the flow is over here
                return None
        
        output = {}
        timeout_svr = None
        for svr_id, (sent_time, cmd) in self._sent_requests.iteritems():
            if time - sent_time >= self._timeout:
                self._server_states[svr_id] = False
                timeout_svr = svr_id
                print 'server_%s has timeout' % svr_id
                for server_id in self._server_ids:
                    if self._server_states[server_id]:
                        if cmd == 'set':
                            self._sent_requests[server_id] = (time, 'set')
                            output = {server_id: ('set', 1)}
                            break
                        else:
                            self._sent_requests[server_id] = (time, 'get')
                            output = {server_id: ('get',)}
                            break
                
            if output:
                break
        
        if output:
            del self._sent_requests[timeout_svr]
        return output

    def get_id(self):
        return self._id


class ServerProcess(object):
    def __init__(self, proc_id, replica_ids):
        self._id = proc_id
        self._replica_ids = replica_ids
        self._replica_ids.remove(proc_id)
        self._value = None
        self._replica_routine = None
        self._src_id = None

    def process(self, _input, time):
        print 'ServerProcess_%d[%d] recv: %s' % (self._id, time, _input)
        output = {}
        for src_id, msgs in _input.iteritems():
            if src_id in self._replica_ids:  # request from other replica
                if msgs == ['setreplica success']:
                    assert self._replica_routine is not None
                    try:
                        self._replica_routine.send((src_id, msgs[0]))
                    except StopIteration:
                        self._replica_routine = None
                        if self._value is not None:
                            output[self._src_id] = 'set success'
                        else:
                            output[self._src_id] = 'set failed'
                        self._src_id = None
                    
                    continue
                else:
                    for m in msgs:
                        if m[0] == 'setreplica':
                            if self._value is None:
                                self._value = m[1]
                                output[src_id] = 'setreplica success'
                            else:
                                output[src_id] = 'setreplica failed'
            else:  # request from client
                for m in msgs:
                    if m[0] == 'set':
                        if self._value is None:
                            if self._replica_routine is not None:
                                output[src_id] = 'set failed'
                            else:
                                assert self._replica_routine is None
                                assert self._src_id is None
                                self._src_id = src_id
                                self._replica_routine = self.set_value(m[1])
                                msg = self._replica_routine.next()
                                for replica_id in self._replica_ids:
                                    output[replica_id] = msg
                        else:
                            output[src_id] = 'set failed'
                    elif m[0] == 'get':
                        if self._value is not None:
                            output[src_id] = self._value
                        else:
                            output[src_id] = 'get failed'
        return output
    
    # this is a generator
    def set_value(self, value):
        replica_set_states = dict((replica_id, None) for replica_id in self._replica_ids)
        replica_id, msg = yield ('setreplica', value)
        count = 0
        while True:
            assert replica_set_states[replica_id] is None
            replica_set_states[replica_id] = (msg == 'setreplica success')
            count += 1
            if count == len(replica_set_states):
                break
            else:
                replica_id, msg = yield
        
        for replica_id, is_success in replica_set_states.iteritems():
            if not is_success:
                return
        
        self._value = value
        return

    def get_id(self):
        return self._id


processes = [ClientProcess(0, [1, 2], 5),
             ServerProcess(1, [1, 2]), ServerProcess(2, [1, 2])]
links = {(0, 1): 1, (0, 2): 1, (1, 2): 1}
commands = ['next 5', 'status', 'next 3', 'status']
