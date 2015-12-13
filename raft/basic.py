""" This raft implementation use 20 - 30 as timeout.
"""

import random


class ClientProcess(object):
    def __init__(self, proc_id, commands, cluster_member_ids):
        self._id = proc_id
        self._commands = commands
        self._seq = 0
        self._expected_recv_msgs = {}
        self._cluster_member_ids = cluster_member_ids
        self._leader = None

    def process(self, _input, time):
        output = {}
        for src_id, msgs in _input.iteritems():
            msg = msgs[0]
            seq = msg[0]
            msg = msg[1]
            msg_type = msg[0]
            if seq not in self._expected_recv_msgs:
                print self._id, 'recv unexpected msg from', src_id, msgs
                continue

            deadline, sent_msg, expected_msg = self._expected_recv_msgs[seq]
            if msg_type == 'redirect':
                leader = msg[1]
                if leader is not None:
                    self._leader = msg[1]

                if self._leader is not None:
                    leader = self._leader
                else:
                    leader = random.choice(self._cluster_member_ids)

                output[leader] = (seq, sent_msg)
            elif time <= deadline:
                print self._id, 'recv msg', msg
                assert expected_msg == msg, \
                    'expected: %s actual: %s' % (expected_msg, msg)
                del self._expected_recv_msgs[seq]

        for seq, item in self._expected_recv_msgs.iteritems():
            deadline = item[0]
            if time > deadline:
                print self._id, 'not recv msg for seq %d, timeout' % seq
                del self._expected_recv_msgs[seq]
                assert False, 'timeout'

        if time in self._commands:
            for command in self._commands[time]:
                send_msg, recv_msg, timeout = command
                if self._leader is None:
                    target = random.choice(self._cluster_member_ids)
                else:
                    target = self._leader
                output[target] = (self._seq, send_msg)
                self._expected_recv_msgs[self._seq] = (time + timeout, send_msg, recv_msg)
                self._seq += 1

            del self._commands[time]

        return output

    def get_id(self):
        return self._id

    def print_status(self):
        print '%s(id=%d,seq=%d,l=%s)' % (
            self.__class__.__name__, self._id, self._seq, str(self._leader))


class NativeRandomNumber(object):
    def __init__(self, _min, _max):
        self._min = _min
        self._max = _max

    def next(self):
        return random.randrange(self._min, self._max)


class SeqRandomNumber(object):
    """ This is used for testing.
    """

    def __init__(self, numbers):
        self._numbers = numbers
        self._next_i = 0

    def next(self):
        number = self._numbers[self._next_i]
        self._next_i += 1
        if self._next_i >= len(self._numbers):
            self._next_i = 0
        return number


class ServerProcess(object):
    MIN_ELECTION_TIMEOUT = 10

    class Follower(object):
        def __init__(self, _id, random_num, logs, cur_term, leader, member_ids, kvs,
                     commit_index, last_apply_index):
            self._id = _id
            self._random_num = random_num
            self._logs = logs
            self._current_term = cur_term
            self._leader = leader
            self._last_leader_time = 0
            self._election_timeout = random_num.next()
            self._member_ids = member_ids
            self._commit_index = commit_index
            self._last_apply_index = last_apply_index
            self._kvs = kvs

        def get_status(self):
            return 'Follower(t=%d,l=%s,last=%d,e=%d,ci=%d,li=%d,logs=%s,kv=%s)' % (
                self._current_term, str(self._leader), self._last_leader_time,
                self._election_timeout, self._commit_index, self._last_apply_index,
                str(self._logs), str(self._kvs)
            )

        def process(self, _input, time):
            if self._last_leader_time == 0:
                self._last_leader_time = time

            output = {}
            for src_id, msgs in _input.iteritems():
                msg = msgs[0]
                if src_id not in self._member_ids:  # client requests
                    output[src_id] = (msg[0], ('redirect', self._leader))
                    continue

                msg_type, recv_term = msg[0], msg[1]
                if msg_type == 'request_vote':
                    last_index, last_term = msg[2], msg[3]
                    if recv_term < self._current_term:
                        output[src_id] = ('reject_vote', self._current_term, self._leader)
                    else:
                        if recv_term > self._current_term:
                            print self._id, 'recv higher term from', src_id, ', reset leader'
                            self._current_term = recv_term
                            self._leader = None

                        if ((self._leader is None or self._leader == src_id) and
                                self.is_candidate_log_up_to_date(last_index, last_term)):
                            self._leader = src_id
                            self._current_term = recv_term
                            self._last_leader_time = time
                            output[src_id] = ('accept_vote', self._current_term)
                        else:
                            output[src_id] = ('reject_vote', self._current_term, self._leader)
                elif msg_type == 'append_entries':
                    seq = msg[2]
                    if recv_term < self._current_term:
                        output[src_id] = ('append_result', self._current_term, seq, False)
                    elif recv_term == self._current_term:
                        if self._leader is None:
                            print self._id, 'recv append_entries from', src_id, 'without leader'
                            self._leader = src_id
                        if src_id == self._leader:
                            self._last_leader_time = time
                            output[src_id] = self.process_append_entries(msg, seq)
                        else:
                            print self._id, 'recv append_entries from non-leader', src_id
                            output[src_id] = ('append_result', self._current_term, seq, False)
                    else:
                        print self._id, 'recv append_entries from higher term leader', \
                            src_id, recv_term
                        self._leader = src_id
                        self._last_leader_time = time
                        output[src_id] = self.process_append_entries(msg, seq)
                else:
                    print self._id, 'unrecognized msg from', src_id, msg

            if self._last_leader_time + self._election_timeout < time:
                self._leader = None
                candidate = ServerProcess.Candidate(
                    self._id, self._random_num, self._logs, self._current_term + 1,
                    self._member_ids, self._kvs,
                    self._commit_index, self._last_apply_index)
                return candidate.process(_input, time)

            return self, output

        def is_candidate_log_up_to_date(self, last_index, last_term):
            if len(self._logs) == 0:
                return True

            my_last_index = len(self._logs) - 1
            my_last_term = self._logs[-1][0]
            if my_last_term < last_term:
                return True
            elif my_last_term > last_term:
                return False
            else:  # my_last_term == last_term
                return my_last_index <= last_index

        def process_append_entries(self, msg, seq):
            logs, prev_index, prev_term, last_commit_index = msg[3:]
            if prev_index >= 0:
                if prev_index < len(self._logs) and self._logs[prev_index][0] != prev_term:
                    print self._id, 'not consistent logs with leader', self._leader, msg
                    return 'append_result', self._current_term, seq, False

                # this follower's logs does not contain the leader's log
                if prev_index >= len(self._logs):
                    print self._id, 'fewer logs with leader', self._leader, msg, len(self._logs)
                    return 'append_result', self._current_term, seq, False

            for i, cmd in enumerate(logs):
                if prev_index + 1 + i >= len(self._logs):
                    break

                if self._logs[prev_index + 1 + i][0] != cmd[0]:
                    self._logs = self._logs[:prev_index + 1 + i]
                    break

            self._logs.extend(logs[len(self._logs) - prev_index - 1:])

            # check whether we should apply the logs to the state machine
            if self._commit_index < last_commit_index:
                self._commit_index = last_commit_index

            if self._last_apply_index < last_commit_index:
                for i in xrange(self._last_apply_index + 1, last_commit_index + 1):
                    _, cmd = self._logs[i]
                    print self._id, 'apply cmd to follower:', cmd
                    if cmd[0] == 'set':
                        self._kvs[cmd[1]] = cmd[2]

                self._last_apply_index = last_commit_index

            return 'append_result', self._current_term, seq, True

    class Candidate(object):
        def __init__(self, _id, random_num, logs, cur_term, member_ids, kvs,
                     commit_index, last_apply_index):
            self._id = _id
            self._random_num = random_num
            self._logs = logs
            self._cur_term = cur_term
            self._member_ids = member_ids
            self._election_timeout = random_num.next()
            self._vote_routine = None
            self._commit_index = commit_index
            self._last_apply_index = last_apply_index
            self._kvs = kvs

        def get_status(self):
            return 'Candidate(t=%d,e=%d,logs=%s)' % (
                self._cur_term, self._election_timeout, str(self._logs))

        def process(self, _input, time):
            if self._vote_routine is None:
                self._vote_routine = self.request_vote(_input, time)
                return self._vote_routine.next()
            else:
                return self._vote_routine.send((_input, time))

        # this is a generator
        def request_vote(self, _, time):
            election_start_time = time
            req_msg = ('request_vote', self._cur_term, len(self._logs) - 1,
                        self._logs[-1][0] if len(self._logs) > 0 else -1)
            reqs = dict((target, req_msg) for target in self._member_ids)
            accept_count = 1
            majority_num = (len(self._member_ids) + 1) / 2 + 1
            _input, time = yield (self, reqs)
            while True:
                output = {}
                for src_id, msgs in _input.iteritems():
                    msg = msgs[0]
                    if src_id not in self._member_ids:  # client request
                        seq = msg[0]
                        output[src_id] = (seq, ('redirect', None))
                        continue

                    msg_type, term = msg[0], msg[1]
                    if term == self._cur_term:
                        if msg_type == 'accept_vote':
                            # TODO: check duplicate accept
                            accept_count += 1
                            if accept_count >= majority_num:
                                leader = ServerProcess.Leader(
                                    self._id, self._random_num, self._logs, self._cur_term,
                                    self._member_ids,
                                    self._kvs, self._commit_index, self._last_apply_index)
                                yield leader.process(_input, time)
                        elif msg_type == 'reject_vote':
                            print self._id, 'recv reject_vote from %d and vote %s as leader' % (
                                src_id, str(msg[2])
                            )
                        elif msg_type == 'request_vote':
                            print self._id, 'recv request_vote from', src_id, ', reject it'
                            output[src_id] = ('reject_vote', self._cur_term, None)
                        elif msg_type == 'append_entries':
                            print self._id, 'new leader', src_id, 'append_entries'
                            follower = ServerProcess.Follower(
                                self._id, self._random_num, self._logs, term, src_id,
                                self._member_ids, self._kvs, self._commit_index,
                                self._last_apply_index)
                            yield follower.process(_input, time)
                        else:
                            print self._id, 'recv unexpected msg', src_id, msgs
                    elif term > self._cur_term:
                        if msg_type in ['append_entries', 'request_vote']:
                            follower = ServerProcess.Follower(
                                self._id, self._random_num, self._logs, term, None,
                                self._member_ids, self._kvs,
                                self._commit_index, self._last_apply_index)
                        else:
                            follower = ServerProcess.Follower(
                                self._id, self._random_num, self._logs, term, src_id,
                                self._member_ids, self._kvs,
                                self._commit_index, self._last_apply_index)
                        yield follower.process(_input, time)
                    else:
                        print self._id, 'recv lower term %d from %d' % (term, src_id)
                        if msg_type == 'append_entries':
                            output[src_id] = ('append_result', self._cur_term, msg[2], False)

                if election_start_time + self._election_timeout < time:
                    new_candidate = ServerProcess.Candidate(
                        self._id, self._random_num, self._logs, self._cur_term + 1,
                        self._member_ids, self._kvs,
                        self._commit_index, self._last_apply_index)
                    yield new_candidate.process(_input, time)
                else:
                    _input, time = yield (self, output)

            return

    class Leader(object):
        def __init__(self, _id, random_num, logs, cur_term, member_ids, kvs,
                     commit_index, last_apply_index):
            self._id = _id
            self._random_num = random_num
            self._logs = logs
            self._cur_term = cur_term
            self._member_ids = member_ids
            self._lead_routine = None
            self._append_timeout = ServerProcess.MIN_ELECTION_TIMEOUT - 2
            self._last_append_time = 0
            self._commit_index = commit_index
            self._last_apply_index = last_apply_index
            self._kvs = kvs  # this is the state
            self._set_procedure = None
            self._sent_req_seqs = {}
            self._req_seq = 0
            self._next_index = dict((i, len(self._logs)) for i in member_ids)
            self._match_index = dict((i, -1) for i in member_ids)

        def get_status(self):
            return 'Leader(t=%d,ci=%d,la=%d,logs=%s,st=%s)' % (
                self._cur_term, self._commit_index,
                self._last_apply_index, str(self._logs), str(self._kvs))

        def process(self, _input, time):
            if self._lead_routine is None:
                self._lead_routine = self.lead(_input, time)
                return self._lead_routine.next()
            else:
                return self._lead_routine.send((_input, time))

        def lead(self, _input, time):
            # TODO: handle input
            output = {}
            self.heartbeat(output)
            self._last_append_time = time
            _input, time = yield self, output
            while True:
                output = {}
                for src_id, msgs in _input.iteritems():
                    msg = msgs[0]
                    if src_id not in self._member_ids:  # request from client
                        seq = msg[0]
                        msg = msg[1]
                        msg_type = msg[0]
                        if msg_type == 'get':
                            self.process_get(src_id, seq, msg[1], output)
                        elif msg_type == 'set':
                            if self._set_procedure is None:
                                self._set_procedure = self.process_set(
                                    src_id, seq, msg[1], msg[2], output)
                                self._set_procedure.next()
                            else:
                                print self._id, 'set in progress'
                        else:
                            print self._id, 'recv unknown command from client:', msg, src_id
                    else:
                        msg_type = msg[0]
                        term = msg[1]
                        if term > self._cur_term:
                            print self._id, 'leader recv higher term', term, msg
                            if msg_type == 'request_vote':
                                follower = ServerProcess.Follower(
                                    self._id, self._random_num, self._logs, self._cur_term,
                                    None, self._member_ids,
                                    self._kvs, self._commit_index, self._last_apply_index)
                            elif msg_type == 'append_entries':
                                follower = ServerProcess.Follower(
                                    self._id, self._random_num, self._logs, term, src_id,
                                    self._member_ids, self._kvs,
                                    self._commit_index, self._last_apply_index)
                            else:
                                follower = ServerProcess.Follower(
                                    self._id, self._random_num, self._logs, term, None,
                                    self._member_ids, self._kvs,
                                    self._commit_index, self._last_apply_index)
                            yield follower.process(_input, time)
                        elif term == self._cur_term:
                            if msg_type == 'append_result':
                                seq = msg[2]
                                try:
                                    sent_req_type = self._sent_req_seqs[seq]
                                    del self._sent_req_seqs[seq]
                                except KeyError:
                                    print self._id, 'recv unknown seq from', src_id, seq
                                    continue

                                if sent_req_type == 'set':
                                    if self._set_procedure is not None:
                                        try:
                                            self._set_procedure.send(({src_id: msgs}, output))
                                        except StopIteration:
                                            self._set_procedure = None
                                    else:
                                        print self._id, 'recv append_result without set'
                                else:  # heartbeat response
                                    append_result = msg[3]
                                    if not append_result:
                                        self._next_index[src_id] -= 1
                                        self.send_append_entries(output, src_id, 'heartbeat')

                if self._last_append_time + self._append_timeout < time:
                    self.heartbeat(output)
                    self._last_append_time = time
                _input, time = yield (self, output)

            return

        def heartbeat(self, output):
            for target in self._member_ids:
                if target not in output:
                    self.send_append_entries(output, target, 'heartbeat')

        def process_get(self, client_id, seq, _key, output):
            try:
                output[client_id] = (seq, ('get_result', self._kvs[_key]))
            except KeyError:
                output[client_id] = (seq, ('get_result', None))

        def process_set(self, client_id, seq, _key, _value, output):
            cmd = ('set', _key, _value)
            to_commit_index = len(self._logs)
            self._logs.append((self._cur_term, cmd))

            for target in self._member_ids:
                self.send_append_entries(output, target, 'set')

            majority_num = (1 + len(self._member_ids)) / 2 + 1
            accept_count = set(['self'])
            reject_count = set()
            _input, output = yield
            while True:
                for src_id, msgs in _input.iteritems():
                    msg = msgs[0]
                    msg_type = msg[0]
                    if msg_type == 'append_result':
                        term, result = msg[1], msg[3]
                        if result:
                            accept_count.add(src_id)
                            self._next_index[src_id] = to_commit_index + 1
                            self._match_index[src_id] = to_commit_index
                        else:
                            print self._id, 'recv failed append from', src_id, '. retry.'
                            assert self._next_index[src_id] >= 0
                            self._next_index[src_id] -= 1
                            self.send_append_entries(output, src_id, 'set')

                        if len(accept_count) >= majority_num:
                            output[client_id] = (seq, ('set_result', True))
                            # the entry has been commited, apply it to the state machine
                            self.commit_log(to_commit_index)
                            return
                        elif len(reject_count) >= majority_num:  # TODO: remove this?
                            print self._id, 'majority rejected the accept'
                            # TODO
                            return
                    else:
                        print
                _input, output = yield

            return

        def send_append_entries(self, output, target, purpose):
            its_next_index = self._next_index[target]
            prev_term = self._logs[its_next_index - 1][0] if its_next_index > 0 else 0
            cmds = self._logs[its_next_index:]
            output[target] = ('append_entries', self._cur_term, self._req_seq,
                              cmds, its_next_index - 1, prev_term, self._commit_index)
            self._sent_req_seqs[self._req_seq] = purpose
            self._req_seq += 1

        def update_commit_index(self, new_commit_index):
            if new_commit_index <= self._commit_index:
                return

            majority_num = (len(self._member_ids) + 1) / 2 + 1
            commit_count = 1 if len(self._logs) - 1 == new_commit_index else 0
            commit_count += list(self._match_index.itervalues()).count(new_commit_index)
            if commit_count >= majority_num and \
               self._logs[new_commit_index][0] == self._cur_term:
                self._commit_index = new_commit_index

        def commit_log(self, commit_index):
            self.update_commit_index(commit_index)
            if commit_index > self._last_apply_index:
                for i in xrange(self._last_apply_index + 1, commit_index + 1):
                    term, log_msg = self._logs[i]
                    assert log_msg[0] == 'set', str(log_msg)
                    self._kvs[log_msg[1]] = log_msg[2]

                self._last_apply_index = commit_index

    def __init__(self, _id, member_ids, timeout=0, random_num=None):
        self._id = _id
        self._logs = []
        self._cur_term = 0
        self._member_ids = member_ids
        self._member_ids.remove(self._id)

        if random_num is None:
            random_num = NativeRandomNumber(ServerProcess.MIN_ELECTION_TIMEOUT, 30)
        self._role = ServerProcess.Follower(
            self._id, random_num, self._logs, self._cur_term,
            None, self._member_ids, {}, -1, -1)

    def get_id(self):
        return self._id

    def process(self, _input, time):
        self._role, output = self._role.process(_input, time)
        return output

    def print_status(self):
        print 'RaftServer(id=%d,%s)' % (self._id, self._role.get_status())


client_commands = {30: [(('set', 1, 2), ('set_result', True), 60)],
                   80: [(('set', 2, 3), ('set_result', True), 60)],
                   180: [(('set', 3, 4), ('set_result', True), 60)],
                   220: [(('get', 2), ('get_result', 3), 60)]}
processes = [ClientProcess(0, client_commands, range(1, 6))] + \
            [ServerProcess(i, range(1, 6), 3) for i in xrange(1, 6)]
links = dict(((i, j), 5) for i in xrange(6) for j in xrange(i + 1, 6))
#commands = ['next 20', 'status', 'next 10', 'status', 'next 10',
 #           'status', 'next 20', 'status']

