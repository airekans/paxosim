class ClientProcess(object):
    def __init__(self, proc_id, server_id, output, expected_input):
        self._id = proc_id
        self._server_id = server_id
        self._output = output
        self._expected_input = expected_input

    def process(self, _input, time):
        if time in self._expected_input:
            assert self._expected_input[time] == _input, \
                'expected: %s actual: %s' % (str(self._expected_input[time]),
                    str(_input))

        if time in self._output:
            return {self._server_id: self._output[time]}
        else:
            return None

    def get_id(self):
        return self._id


class ServerProcess(object):
    def __init__(self, proc_id):
        self._id = proc_id
        self._value = None

    def process(self, _input, time):
        print 'ServerProcess_%d[%d] recv: %s' % (self._id, time, _input)
        output = {}
        for src_id, msgs in _input.iteritems():
            for m in msgs:
                if m[0] == 'set':
                    if self._value is None:
                        self._value = m[1]
                        output[src_id] = 'set success'
                    else:
                        output[src_id] = 'set failed'
                elif m[0] == 'get':
                    if self._value is not None:
                        output[src_id] = self._value
                    else:
                        output[src_id] = 'get failed'
        return output

    def get_id(self):
        return self._id


processes = [ClientProcess(0, 1, {0: ('set', 1), 4: ('get',)},
                           {2: {1: ['set success']}, 6: {1: [1]}}),
             ServerProcess(1)]
links = {(0, 1): 1}
commands = ['next 3', 'status', 'next 3', 'status']
