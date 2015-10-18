""" This raft implementation use 20 - 30 as timeout.
"""

import random


class ClientProcess(object):
    def __init__(self, proc_id, commands):
        self._id = proc_id
        self._commands = commands
        self._expected_recv_msgs = {}
        self._leader = None

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

    def print_status(self):
        print '%s(id=%d,seq=%d,promised_seq=%d,v=%s,cv=%s)' % (
            self.__class__.__name__, self._id, self._seq, self._promised_seq,
            self._value, self._commited_value)


class ServerProcess(object):
    ST_FOLLOWER = 1
    ST_CANDIDATE = 2
    ST_LEADER = 3

    class Follower(object):
        def __init__(self, logs, cur_term, leader, member_ids):
            self._logs = logs
            self._current_term = cur_term
            self._leader = leader
            self._last_leader_time = 0
            self._election_timeout = random.randrange(20, 30)
            self._member_ids = member_ids

        def get_status(self):
            return 'Follower(t=%d,l=%s,last=%d,e=%d)' % (
                self._current_term, str(self._leader), self._last_leader_time,
                self._election_timeout
            )

        def process(self, _input, time):
            if self._last_leader_time == 0:
                self._last_leader_time = time

            output = {}
            for src_id, msgs in _input.iteritems():
                msg = msgs[0]
                recv_term, msg_type = msg[0], msg[1]
                if msg_type == 'request_vote':
                    if recv_term < self._current_term:
                        output[src_id] = (self._current_term, 'reject_vote', self._leader)
                    elif self._leader is None or recv_term > self._current_term:
                        self._leader = src_id
                        self._current_term = recv_term
                        self._last_leader_time = time
                        output[src_id] = (self._current_term, 'accept_vote')
                    else:
                        output[src_id] = (self._current_term, 'reject_vote', self._leader)
                elif msg_type == 'append_entries':
                    if recv_term < self._current_term:
                        output[src_id] = (self._current_term, 'no_append')
                    elif self._leader is None:
                        print 'recv append_entries from', src_id, 'without leader'
                        # TODO
                    elif src_id == self._leader:
                        self._current_term = recv_term
                        self._last_leader_time = time
                        output[src_id] = self.process_append_entries(msg)
                    else:
                        # TODO
                        print 'recv append_entries from non-leader', src_id
                else:
                    print 'unrecognized msg from', src_id, msg

            if self._last_leader_time + self._election_timeout < time:
                self._leader = None
                candidate = ServerProcess.Candidate(
                    self._logs, self._current_term + 1, self._member_ids)
                return candidate.process(_input, time)

            return self, output

        def process_append_entries(self, msgs):
            # process append_entries
            return self._current_term, 'append_success'

    class Candidate(object):
        def __init__(self, logs, cur_term, member_ids):
            self._logs = logs
            self._cur_term = cur_term
            self._member_ids = member_ids
            self._election_timeout = random.randrange(20, 30)
            self._vote_routine = None

        def get_status(self):
            return 'Candidate(t=%d,e=%d)' % (
                self._cur_term, self._election_timeout)

        def process(self, _input, time):
            if self._vote_routine is None:
                self._vote_routine = self.request_vote(_input, time)
                return self._vote_routine.next()
            else:
                return self._vote_routine.send((_input, time))

        # this is a generator
        def request_vote(self, _input, time):
            reqs = dict((target, (self._cur_term, 'request_vote'))
                        for target in self._member_ids)
            accept_count = 1
            majority_num = (len(self._member_ids) + 1) / 2 + 1
            _input, time = yield (self, reqs)
            while True:
                output = {}
                for src_id, msgs in _input.iteritems():
                    msg = [0]
                    term = msg[0]
                    if term == self._cur_term:
                        msg_type = msg[1]
                        if msg_type == 'accept_vote':
                            accept_count += 1
                            if accept_count >= majority_num:
                                leader = ServerProcess.Leader(self._logs, self._cur_term)
                                yield leader.process(_input, time)
                        elif msg_type == 'reject_vote':
                            print 'recv reject_vote from %d and vote %d as leader' % (
                                src_id, msg[2]
                            )
                        else:
                            print 'recv unexpected msg', src_id, msgs
                    elif term > self._cur_term:
                        follower = ServerProcess.Follower(
                            self._logs, term, None, self._member_ids)
                        yield follower.process(_input, time)

                _input, time = yield (self, output)
            return

    class Leader(object):
        def __init__(self, logs, cur_term, member_ids):
            self._logs = logs
            self._cur_term = cur_term
            self._member_ids = member_ids

        def get_status(self):
            return 'Leader(t=%d)' % self._cur_term

        def process(self, _input, time):
            return self, {}

    def __init__(self, _id, member_ids, timeout):
        self._id = _id
        self._logs = []
        self._cur_term = 0
        self._member_ids = member_ids
        self._member_ids.remove(self._id)
        self._role = ServerProcess.Follower(self._logs, self._cur_term, None, self._member_ids)

    def get_id(self):
        return self._id

    def process(self, _input, time):
        self._role, output = self._role.process(_input, time)
        return output

    def print_status(self):
        print 'RaftServer(%s)' % self._role.get_status()


processes = [ServerProcess(i, range(5), 3) for i in xrange(5)]
links = dict(((i, j), 10) for i in xrange(5) for j in xrange(i + 1, 5))
#commands = ['next 7', 'status', 'next 5']

