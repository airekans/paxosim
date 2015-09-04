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
                assert expected_msg == msgs[0], \
                    'expected: %s actual: %s' % (expected_msg, msgs[0])
                del self._expected_recv_msgs[src_id]

        for target in self._expected_recv_msgs.keys():
            deadline, _ = self._expected_recv_msgs[target]
            if time > deadline:
                print 'not recv msg from %d, timeout' % target
                del self._expected_recv_msgs[target]
                assert False, 'timeout'

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
        self._commited_value = None
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
                    output[src_id] = self.process_accept(msg[1], msg[2])
                elif msg[0] == 'commit':
                    self.process_commit(msg[1], msg[2])  # commit is async
                elif msg[0] in ('promise', 'accepted', 'reject'):
                    if self._set_routine is None:
                        print 'unexpected promise from', src_id
                    else:
                        try:
                            is_set_routine_called = True
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
                            is_get_routine_called = True
                            self._get_routine.send((src_id, msg, output))
                        except StopIteration:
                            self._get_routine = None
            else:
                if msg[0] == 'set':
                    if self._commited_value is not None:
                        output[src_id] = 'set already %d' % self._commited_value
                    elif self._set_routine is not None:
                        output[src_id] = 'set in progress'
                    else:
                        set_generator = self.set_value(msg[1], time, output, src_id)
                        self._set_routine = set_generator
                        set_generator.next()
                        is_set_routine_called = True
                elif msg[0] == 'get':
                    if self._commited_value is not None:
                        output[src_id] = self._commited_value
                    elif self._get_routine is not None:
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
        ret_seq = -1
        if seq > self._promised_seq:
            ret_seq = seq if self._value is None else self._promised_seq
            self._promised_seq = seq
        else:
            ret_seq = self._promised_seq

        return 'promise', seq, ret_seq, self._value

    def process_accept(self, seq, value):
        if seq == self._promised_seq:
            self._value = value
            return 'accepted', seq
        else:
            print 'reject seq', seq
            return 'reject', seq

    def process_commit(self, _seq, value):
        self._commited_value = value

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
        cur_time = time
        largest_seq = self._promised_seq
        majority_num = (len(self._member_ids) + 1) / 2 + 1

        while True:
            value_seq = self._promised_seq if self._value is not None else -1
            set_value = None if self._value is None else self._value

            # propose to set the value
            if self._seq <= largest_seq:
                member_num = len(self._member_ids) + 1
                self._seq = ((largest_seq - self._seq) / member_num + 1) \
                    * member_num

            for proc_id in self._member_ids:
                # the second seq is used as round number
                output[proc_id] = ('propose', self._seq)

            # I will accept the promise myself.
            self._promised_seq = self._seq
            largest_seq = self._seq

            expected_seq = self._seq
            self._seq += len(self._member_ids) + 1
            output = None

            msg_records = dict((i, None) for i in self._member_ids)
            success_count = 1  # 1 because I've promised to my proposal myself first
            failure_count = 0

            should_retry = False
            propose_time = cur_time
            while success_count < majority_num:
                src_id, msg, output = yield
                cur_time += 1

                # check whether I have changed my mind to accept other guy's proposal
                if self._promised_seq > expected_seq:
                    # if yes, then I will abort the current proposal and retry
                    if self._promised_seq > largest_seq:
                        largest_seq = self._promised_seq
                    should_retry = True
                    break

                if src_id is None:
                    if cur_time > propose_time + self._timeout:
                        failure_count += msg_records.values().count(None)
                        if failure_count >= majority_num:
                            output[client_id] = 'set failed'
                            return
                elif msg_records[src_id] is not None:
                    continue
                else:
                    msg_type = msg[0]
                    if msg_type == 'promise':
                        msg_seq, promised_seq, accepted_value = msg[1:]
                        if msg_seq != expected_seq:
                            print 'ignore previous round promise', msg_seq
                        elif promised_seq == expected_seq:
                            assert accepted_value is None
                            success_count += 1
                            msg_records[src_id] = True
                        elif promised_seq < expected_seq:
                            if promised_seq > value_seq:
                                set_value = accepted_value
                            success_count += 1
                            msg_records[src_id] = True
                        elif msg[1] > expected_seq:
                            # I've found someone having higher priority, so retry
                            should_retry = True
                            if msg[1] > largest_seq:
                                largest_seq = msg[1]
                            break
                        else:
                            print 'ignore unexpected msg', msg
                    else:
                        print 'ignore unexpected msg', msg

            if should_retry:
                continue

            if set_value is None:
                set_value = value

            # the majority, including me, has promised to accept the value
            # And I will accept my own proposal first
            assert self._promised_seq == expected_seq
            accepted_count = 1
            reject_count = 0
            self._value = set_value

            for proc_id in self._member_ids:
                output[proc_id] = ('accept', expected_seq, set_value)

            msg_records = dict((i, None) for i in self._member_ids)
            accept_start_time = cur_time
            while accepted_count < majority_num:
                src_id, msg, output = yield
                cur_time += 1

                if src_id is None:
                    if cur_time > accept_start_time + self._timeout:
                        reject_count += msg_records.values().count(None)
                        if reject_count >= majority_num:
                            print 'accept timeout'
                            output[client_id] = 'set failed'
                            return
                elif msg_records[src_id] is not None:
                    continue
                else:
                    msg_type = msg[0]
                    if msg_type == 'accepted':
                        msg_seq = msg[1]
                        if msg_seq == expected_seq:
                            accepted_count += 1
                            msg_records[src_id] = True
                        else:
                            print 'ignore previous round accepted:', msg[1]
                    elif msg_type == 'reject':  # the accept msg has been rejected
                        reject_count += 1
                        msg_records[src_id] = False
                        if reject_count >= majority_num:
                            output[client_id] = 'set failed'
                            return

            # the majority have accepted, so tell the learners about the new value
            # and return
            # no need to wait for the replies from members
            assert self._commited_value in (None, set_value)
            self._commited_value = set_value  # commit myself
            print 'set_value', set_value
            output[client_id] = 'set success' if set_value == value else 'set failed'
            for proc_id in self._member_ids:
                output[proc_id] = ('commit', self._seq, set_value)
            return

    def print_status(self):
        print '%s(id=%d,seq=%d,promised_seq=%d,v=%s,cv=%s)' % (
            self.__class__.__name__, self._id, self._seq, self._promised_seq,
            self._value, self._commited_value)


processes = [ClientProcess(0, {0: [(1, ('set', 1), 'set success', 6)],
                               7: [(1, ('get',), 1, 4)]})] + \
            [ServerProcess(i, range(1, 6), 3, i) for i in xrange(1, 6)]
links = dict(((i, j), 1) for i in xrange(6) for j in xrange(i + 1, 6))
commands = ['next 7', 'status', 'next 5']
