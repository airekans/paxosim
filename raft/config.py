

class Configuration(object):
    STATE_STABLE = 1
    STATE_TRANSITIONAL = 2

    def __init__(self, state):
        self._state = state
        self._staging_servers = []
        self._old_servers = []  # only valid for transitional config
        self._servers = []

    def set_staging_server(self, servers):
        assert self._state == Configuration.STATE_TRANSITIONAL
        self._staging_servers = servers

    def remove_staging_server(self, server_id):
        assert self._state == Configuration.STATE_TRANSITIONAL
        self._staging_servers.remove(server_id)

    def is_all_caught_up(self):
        return len(self._staging_servers) == 0

    def set_servers(self, servers, old_servers=None):
        self._servers = servers

        if old_servers is not None:
            assert self._state == Configuration.STATE_TRANSITIONAL
            self._old_servers = old_servers

    def get_servers(self, self_id=None):
        servers = None
        if self._state == Configuration.STATE_TRANSITIONAL:
            servers = list(set(self._old_servers) | set(self._servers))
        else:
            servers = list(self._servers)

        if self_id is not None:
            servers.remove(self_id)

        return servers

    def is_server_in_config(self, server_id):
        if self._state == Configuration.STATE_TRANSITIONAL:
            return server_id in self._old_servers or server_id in self._servers
        else:
            return server_id in self._servers

    def is_quorum(self, servers):
        server_set = set(servers)
        new_server_set = set(self._servers)
        new_majority = len(new_server_set) / 2 + 1
        if self._state == Configuration.STATE_TRANSITIONAL:
            old_server_set = set(self._old_servers)
            old_majority = len(old_server_set) / 2 + 1
            return len(server_set & old_server_set) >= old_majority and \
                len(server_set & new_server_set) >= new_majority
        else:
            return len(server_set & new_server_set) >= new_majority

    def is_equal(self, other):
        if not isinstance(other, Configuration) or self._state != other._state:
            return False

        if self._state == Configuration.STATE_TRANSITIONAL:
            return self._old_servers == other._old_servers and self._servers == other._servers
        else:
            return self._servers == other._servers


    def to_log(self):
        if self._state == Configuration.STATE_TRANSITIONAL:
            return 'config', 'transitional', list(self._old_servers), list(self._servers)
        else:
            return 'config', 'stable', list(self._servers)

    @staticmethod
    def from_log(log_entry):
        assert log_entry[0] == 'config'
        if log_entry[1] == 'stable':
            config = Configuration(Configuration.STATE_STABLE)
            config.set_servers(list(log_entry[2]))
        else:
            config = Configuration(Configuration.STATE_TRANSITIONAL)
            config.set_servers(list(log_entry[3]), list(log_entry[2]))
        return config

