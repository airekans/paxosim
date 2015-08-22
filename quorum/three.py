from simple.two import ClientProcess


class ServerProcess(object):
    def __init__(self, proc_id, replica_ids, timeout):
        self._id = proc_id
        self._replica_ids = replica_ids
        self._replica_ids.remove(proc_id)
        self._timeout = timeout
        self._value = None
        self._replica_write_routine = None
        self._write_src_id = None
        self._replica_read_routine = None
        self._read_src_id = None

    def process(self, _input, time):
        print 'ServerProcess_%d[%d] recv: %s' % (self._id, time, _input)
        output = {}
        is_write_routine_called = False
        is_read_routine_called = False
        for src_id, msgs in _input.iteritems():
            if src_id in self._replica_ids:  # request from other replica
                if 'setreplica success' in msgs or 'setreplica failed' in msgs:
                    if self._replica_write_routine is not None:
                        is_write_routine_called = True
                        try:
                            self._replica_write_routine.send((src_id, msgs[0]))
                        except StopIteration:
                            self._replica_write_routine = None
                            if self._value is not None:
                                output[self._write_src_id] = 'set success'
                            else:
                                output[self._write_src_id] = 'set failed'
                            self._write_src_id = None

                    continue
                elif 'getreplica failed' in msgs or isinstance(msgs[0], int):
                    if self._replica_read_routine is not None:
                        is_read_routine_called = True
                        try:
                            self._replica_read_routine.send(((src_id, msgs[0]), output))
                        except StopIteration:
                            self._replica_read_routine = None
                            self._read_src_id = None

                    continue
                else:
                    for m in msgs:
                        if m[0] == 'setreplica':
                            if self._value is None and self._replica_write_routine is None:
                                self._value = m[1]
                                output[src_id] = 'setreplica success'
                            else:
                                output[src_id] = 'setreplica failed'
                        elif m[0] == 'getreplica':
                            if self._value is not None:
                                output[src_id] = self._value
                            else:
                                output[src_id] = 'getreplica failed'
            else:  # request from client
                for m in msgs:
                    if m[0] == 'set':
                        if self._value is None:
                            if self._replica_write_routine is not None:
                                output[src_id] = 'set failed'
                            else:
                                assert self._replica_write_routine is None
                                assert self._write_src_id is None
                                self._write_src_id = src_id
                                self._replica_write_routine = self.set_value(m[1], time)
                                msg = self._replica_write_routine.next()
                                for replica_id in self._replica_ids:
                                    output[replica_id] = msg
                        else:
                            output[src_id] = 'set failed'
                    elif m[0] == 'get':
                        if self._value is not None:
                            if self._replica_read_routine is not None:
                                output[src_id] = 'get failed'
                            else:
                                assert self._read_src_id is None
                                self._read_src_id = src_id
                                self._replica_read_routine = self.get_value(time)
                                msg = self._replica_read_routine.next()
                                for replica_id in self._replica_ids:
                                    output[replica_id] = msg
                        else:
                            output[src_id] = 'get failed'

        if not is_write_routine_called and self._replica_write_routine:
            try:
                self._replica_write_routine.send(None)
            except StopIteration:
                self._replica_write_routine = None
                if self._value is not None:
                    output[self._write_src_id] = 'set success'
                else:
                    output[self._write_src_id] = 'set failed'
                self._write_src_id = None

        if not is_read_routine_called and self._replica_read_routine:
            try:
                self._replica_read_routine.send((None, output))
            except StopIteration:
                self._replica_read_routine = None
                self._read_src_id = None

        return output

    # this is a generator
    def set_value(self, value, start_time):
        success_count = 1
        failure_count = 0
        replica_set_states = dict((replica_id, None) for replica_id in self._replica_ids)
        majority_num = (len(self._replica_ids) + 1) / 2 + 1
        result = yield ('setreplica', value)
        cur_time = start_time + 1
        while True:
            if result is None:
                if cur_time - start_time >= self._timeout:
                    if success_count >= majority_num:
                        break
                    else:
                        return
            else:
                replica_id, msg = result
                assert replica_set_states[replica_id] is None
                if msg == 'setreplica success':
                    replica_set_states[replica_id] = True
                    success_count += 1
                else:
                    failure_count += 1
                    if failure_count >= majority_num:
                        return

                if success_count + failure_count == len(self._replica_ids) + 1:
                    break

            result = yield
            cur_time += 1

        self._value = value
        return

    # generator
    def get_value(self, start_time):
        success_count = 1
        failure_count = 0
        replica_set_states = dict((replica_id, None) for replica_id in self._replica_ids)
        got_values = {self._value: 1}
        majority_num = (len(self._replica_ids) + 1) / 2 + 1
        result, output = yield ('getreplica',)
        cur_time = start_time + 1
        while True:
            if result is None:
                if cur_time - start_time >= self._timeout:
                    if success_count >= majority_num:
                        for value, count in got_values.iteritems():
                            if count >= majority_num:
                                output[self._read_src_id] = value
                                return

                    output[self._read_src_id] = 'get failed'
                    return
            else:
                replica_id, msg = result
                assert replica_set_states[replica_id] is None
                replica_set_states[replica_id] = True
                if isinstance(msg, int):
                    success_count += 1
                    if msg not in got_values:
                        got_values[msg] = 0
                    got_values[msg] += 1
                else:
                    failure_count += 1

                if success_count + failure_count == len(self._replica_ids) + 1:
                    break

            result, output = yield
            cur_time += 1

        for value, count in got_values.iteritems():
            if count >= majority_num:
                output[self._read_src_id] = value
                return

        output[self._read_src_id] = 'get failed'
        return

    def get_id(self):
        return self._id

    def print_status(self):
        print '%s(%d, %s)' % (self.__class__.__name__, self._id, str(self._value))


processes = [ClientProcess(0, [1, 2, 3], 5),
             ServerProcess(1, [1, 2, 3], 3), ServerProcess(2, [1, 2, 3], 3),
             ServerProcess(3, [1, 2, 3], 3)]
links = {(0, 1): 1, (0, 2): 1, (0, 3): 1, (1, 2): 1, (1, 3): 1, (2, 3): 1}
commands = ['next 5', 'status', 'next 5', 'status']
