class ClientProcess(object):
    def __init__(self, proc_id, commands):
        self._id = proc_id
        self._commands = commands
        self._expected_recv_msgs = {}

    def process(self, _input, time):
        for src_id, msgs in _input.iteritems():
            if src_id not in self._expected_recv_msgs:
                print 'recv unexpected msg from', src_id, msgs
                continue

            deadline, expected_msg = self._expected_recv_msgs[src_id]
            if time <= deadline:
                print 'recv msg', msgs[0]
                assert expected_msg == msgs[0]
                del self._expected_recv_msgs[src_id]

        for target in self._expected_recv_msgs.keys():
            deadline, _ = self._expected_recv_msgs[target]
            if time > deadline:
                print 'not recv msg from %d, timeout' % target
                del self._expected_recv_msgs[target]

        output = {}
        if time in self._commands:
            for command in self._commands[time]:
                target, send_msg, recv_msg, timeout = command
                assert target not in self._expected_recv_msgs
                output[target] = send_msg
                self._expected_recv_msgs[target] = (time + timeout, recv_msg)

            del self._commands[time]

        return output

    def get_id(self):
        return self._id


class ServerProcess(object):
    """ This server store only one value and once it's set,
    it will never be changed again.
    """

    def __init__(self, proc_id, member_ids, timeout, initial_seq):
        self._id = proc_id
        self._member_ids = member_ids
        self._member_ids.remove(proc_id)
        self._timeout = timeout
        self._value = None
        self._seq = initial_seq
        self._promised_seq = -1
        self._set_routine = None
        self._get_routine = None

    def get_id(self):
        return self._id

    def process(self, _input, time):
        output = {}
        is_set_routine_called = False
        is_get_routine_called = False
        for src_id, msgs in _input.iteritems():
            msg = msgs[0]
            if src_id in self._member_ids:
                if msg[0] == 'propose':
                    output[src_id] = self.process_propose(msg[1])
                elif msg[0] == 'accept':
                    self.process_accept(msg[1], msg[2])
                elif msg[0] == 'promise':
                    if self._set_routine is None:
                        print 'unexpected promise from', src_id
                    else:
                        try:
                            self._set_routine.send((src_id, msg, output))
                        except StopIteration:
                            self._set_routine = None
                elif msg[0] == 'getreplica':
                    output[src_id] = self.process_getreplica()
                elif isinstance(msg[0], int):
                    if self._get_routine is None:
                        print 'unexpected get result', src_id
                    else:
                        try:
                            self._get_routine.send((src_id, msg, output))
                        except StopIteration:
                            self._get_routine = None
            else:
                if msg[0] == 'set':
                    if self._value is not None:
                        output[src_id] = 'set already %d' % self._value
                    elif self._set_routine is not None:
                        output[src_id] = 'set in progress'
                    else:
                        set_generator = self.set_value(msg[1], time, output, src_id)
                        self._set_routine = set_generator
                        set_generator.next()
                        is_set_routine_called = True
                elif msg[0] == 'get':
                    if self._get_routine is not None:
                        output[src_id] = 'get in progress'
                    else:
                        get_generator = self.get_value(time, output, src_id)
                        self._get_routine = get_generator
                        get_generator.next()
                        is_get_routine_called = True

        if not is_set_routine_called and self._set_routine is not None:
            try:
                self._set_routine.send((None, None, output))
            except StopIteration:
                self._set_routine = None

        if not is_get_routine_called and self._get_routine is not None:
            try:
                self._get_routine.send((None, None, output))
            except StopIteration:
                self._get_routine = None

        return output

    def process_propose(self, seq):
        if seq > self._promised_seq:
            self._promised_seq = seq

        return 'promise', self._promised_seq, self._value

    def process_accept(self, seq, value):
        if seq == self._promised_seq:
            self._value = value
        else:
            print 'reject seq', seq

    def process_getreplica(self):
        return self._promised_seq, self._value

    def get_value(self, time, output, client_id):
        for proc_id in self._member_ids:
            output[proc_id] = ('getreplica',)

        msg_records = dict((i, None) for i in self._member_ids)
        got_values = {(self._promised_seq, self._value): 1}
        success_count = 1
        failure_count = 0
        majority_num = (len(self._member_ids) + 1) / 2 + 1
        cur_time = time

        while success_count + failure_count < len(self._member_ids) + 1:
            src_id, msg, output = yield
            cur_time += 1
            if src_id is None:
                if cur_time >= time + self._timeout:
                    failure_count += msg_records.values().count(None)
                    if failure_count >= majority_num:
                        output[client_id] = 'get failed'
                        return
            elif msg_records[src_id] is not None:
                continue
            else:
                seq, value = msg
                if (seq, value) not in got_values:
                    got_values[(seq, value)] = 0
                got_values[(seq, value)] += 1
                success_count += 1

                for (seq, value), count in got_values.iteritems():
                    if count >= majority_num:
                        output[client_id] = value
                        return

        for (seq, value), count in got_values.iteritems():
            if count >= majority_num:
                output[client_id] = value
                return

        output[client_id] = 'get failed'
        return

    def set_value(self, value, time, output, client_id):
        # propose to set the value
        if self._seq <= self._promised_seq:
            member_num = len(self._member_ids) + 1
            self._seq = ((self._promised_seq - self._seq) / member_num + 1) \
                * member_num

        for proc_id in self._member_ids:
            output[proc_id] = ('propose', self._seq)

        # I will accept the promise myself.
        self._promised_seq = self._seq

        expected_seq = self._seq
        self._seq += len(self._member_ids) + 1
        output = None

        msg_records = dict((i, None) for i in self._member_ids)
        success_count = 1
        failure_count = 0
        majority_num = (len(self._member_ids) + 1) / 2 + 1

        is_check_myself = False
        set_value = value
        cur_time = time
        while success_count < majority_num:
            src_id, msg, output = yield
            cur_time += 1

            # check whether I have changed my mind to accept other guy's proposal
            if not is_check_myself and self._promised_seq != expected_seq:
                success_count -= 1
                failure_count += 1
                is_check_myself = True

            if src_id is None:
                if cur_time > time + self._timeout:
                    failure_count += msg_records.values().count(None)
                    if failure_count >= majority_num:
                        output[client_id] = 'set failed'
                        return
            elif msg_records[src_id] is not None:
                continue
            elif msg[0] == 'promise' and msg[1] == expected_seq:
                if msg[2] is not None:
                    set_value = msg[2]
                success_count += 1
                msg_records[src_id] = True
            else:
                failure_count += 1
                msg_records[src_id] = False
                if failure_count >= majority_num:
                    output[client_id] = 'set failed'
                    return

        # the majority has promised to accept the value
        # but I have to check whether I should accept it too
        if self._promised_seq == expected_seq:
            self._value = set_value

        for proc_id in self._member_ids:
            output[proc_id] = ('accept', expected_seq, set_value)

        # no need to wait for the replies from members
        if set_value == value:
            output[client_id] = 'set success'
        else:
            output[client_id] = 'set failed'

        return

    def print_status(self):
        print '%s(id=%d,seq=%d,promised_seq=%d,v=%s)' % (
            self.__class__.__name__, self._id, self._seq, self._promised_seq,
            self._value)


processes = [ClientProcess(0, {0: [(1, ('set', 1), 'set success', 4)],
                               5: [(1, ('get',), 1, 4)]})] + \
            [ServerProcess(i, range(1, 6), 3, i) for i in xrange(1, 6)]
links = dict(((i, j), 1) for i in xrange(6) for j in xrange(i + 1, 6))
commands = ['next 7', 'status', 'next 5']
