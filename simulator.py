import sys
import importlib


class Process(object):
    def __init__(self):
        pass
    
    def process(self, _in):
        pass
    
    def get_id(self):
        return self._id


class Simulator(object):
    def __init__(self, processes, links, commands):
        self._cur_time = 0
        self._processes = processes
        self._stopped_processes = [None for _ in xrange(len(processes))]
        self._links = {}
        for link, distance in links.iteritems():
            id1, id2 = link
            self._links[(id1, id2)] = distance
            self._links[(id2, id1)] = distance

        self._removed_links = {}
        self._input_queues = [[{}] for _ in processes]  # Initial input
        self._commands = commands

    # this is the main method to start the simulation
    def run(self):
        skip_round_num = 1
        while True:
            for process in self._processes:
                if process:
                    proc_id = process.get_id()
                    proc_input = self.get_input(proc_id)
                    output = process.process(proc_input, self._cur_time)
                    if output:
                        self.sent_output(proc_id, output)

            skip_round_num -= 1
            if skip_round_num <= 0:
                round_num = self.process_command()
                if round_num is None:
                    break
                else:
                    skip_round_num = round_num
            
            self.goto_next_round(1)
    
    def get_input(self, proc_id):
        if len(self._input_queues[proc_id]) > 0:
            return self._input_queues[proc_id][0]
        else:
            return {}

    def sent_output(self, process_id, output):
        for target_process, msg in output.iteritems():
            try:
                distance = self._links[(process_id, target_process)]
            except KeyError:
                print 'SIM_ERROR: no link from %d to %d, drop msg' % (process_id, target_process)
                continue
            
            queue_size = len(self._input_queues[target_process])
            if queue_size <= distance:
                for _ in range(queue_size, distance + 1):
                    self._input_queues[target_process].append({})
            
            queue = self._input_queues[target_process][distance]
            if process_id in queue:
                queue[process_id].append(msg)
            else:
                queue[process_id] = [msg]

    def process_command(self):
        try:
            while True:
                command = self.get_next_commands()
                if command == '':
                    return 1
                elif command == 'exit':
                    return None
                elif command.startswith('next'):
                    args = command.split(' ')
                    if len(args) > 1:
                        try:
                            skip_round = int(args[1])
                        except ValueError:
                            skip_round = 1

                        return skip_round
                elif command.startswith('kill '):
                    proc_id = Simulator.get_process_id_from_command(command)
                    if proc_id >= 0:
                        self.kill_process(proc_id)
                elif command.startswith('stop '):
                    proc_id = Simulator.get_process_id_from_command(command)
                    if proc_id >= 0:
                        self.stop_process(proc_id)
                elif command.startswith('recover '):
                    proc_id = Simulator.get_process_id_from_command(command)
                    if proc_id >= 0:
                        self.recover_process(proc_id)
                elif command.startswith('rmlink '):
                    source, target = Simulator.get_link_from_command(command)
                    if source >= 0:
                        self.remove_link(source, target)
                elif command.startswith('addlink '):
                    source, target = Simulator.get_link_from_command(command)
                    if source >= 0:
                        self.add_link(source, target)
                elif command.startswith('rmmsg '):
                    target, source = Simulator.get_msg_target_source_from_command(command)
                    if target >= 0:
                        self.remove_msg(target, source)
                elif command == 'status':
                    self.print_status()
                elif command == 'history':
                    pass
                else:
                    print 'Unknown command:', command
        except EOFError:
            return None

    @staticmethod
    def get_process_id_from_command(command):
        args = command.split(' ')
        if len(args) == 1:
            print 'Please give a process id to kill'
            return -1

        try:
            return int(args[1])
        except ValueError:
            print 'Please give a process id to kill'
            return -1

    @staticmethod
    def get_link_from_command(command):
        args = command.split(' ')
        if len(args) < 3:
            print 'Please give a link in format (from, to)'
            return -1, -1

        try:
            return int(args[1]), int(args[2])
        except ValueError:
            print 'Please give a process id to kill'
            return -1, -1

    @staticmethod
    def get_msg_target_source_from_command(command):
        args = command.split(' ')
        try:
            target = int(args[1])
        except ValueError:
            print 'Please give a target process id to delete msg'
            return -1, -1

        if len(args) < 3:
            return target, -1

        try:
            source = int(args[2])
            return target, source
        except ValueError:
            return target, -1

    def kill_process(self, proc_id):
        if proc_id >= len(self._processes):
            return False

        process = self._processes[proc_id]
        if process is not None:
            assert proc_id == process.get_id()
        self._processes[proc_id] = None
        return True

    def stop_process(self, proc_id):
        if proc_id >= len(self._processes):
            return False

        process = self._processes[proc_id]
        if process is not None:
            assert proc_id == process.get_id()
            self._processes[proc_id] = None
            self._stopped_processes[proc_id] = process
            return True
        else:
            return False

    def recover_process(self, proc_id):
        if proc_id >= len(self._processes):
            return False

        process = self._stopped_processes[proc_id]
        if process is not None:
            assert proc_id == process.get_id()
            self._stopped_processes[proc_id] = None
            self._processes[proc_id] = process
            return True
        else:
            return False

    def remove_link(self, source, target):
        if source < 0 or target < 0:
            print 'Please give a link in format (from, to)'
            return False

        try:
            distance = self._links[(source, target)]
            del self._links[(source, target)]
            del self._links[(target, source)]
            self._removed_links[(source, target)] = distance
            self._removed_links[(target, source)] = distance
            return True
        except KeyError:
            return False

    def add_link(self, source, target):
        if source < 0 or target < 0:
            print 'Please give a link in format (from, to)'
            return False

        try:
            distance = self._removed_links[(source, target)]
            del self._removed_links[(source, target)]
            del self._removed_links[(target, source)]
            self._links[(source, target)] = distance
            self._links[(target, source)] = distance
            return True
        except KeyError:
            return False

    def remove_msg(self, target, source):
        if source < 0:
            self._input_queues[target] = [{}]
        else:
            target_queue = self._input_queues[target]
            for msg_queue in target_queue:
                if source in msg_queue:
                    del msg_queue[source]

    def print_status(self):
        print 'time: %d' % self._cur_time
        print 'processes:'
        for p in self._processes:
            if p:
                print '  %s(%d)' % (p.__class__.__name__, p.get_id())

        print 'stopped_processes:'
        for p in self._stopped_processes:
            if p:
                print '  %s(%d)' % (p.__class__.__name__, p.get_id())

        print 'links:', self._links
        print 'input_queues:'
        for proc_id, queue in enumerate(self._input_queues):
            print '  (%d)' % proc_id, queue

    def goto_next_round(self, next_round):
        self._cur_time += next_round
        for i, proc in enumerate(self._processes):
            proc_id = i if proc is None else proc.get_id()
            self._input_queues[proc_id] = self._input_queues[proc_id][next_round:]

    def get_next_commands(self):
        if self._commands is None:
            return raw_input('command[default: next 1]: ').strip()
        else:
            if len(self._commands) == 0:
                return 'exit'

            command = self._commands[0]
            self._commands = self._commands[1:]
            return command


def main():
    if len(sys.argv) < 2:
        print 'Usage:', sys.argv[0], 'proc_module'
        sys.exit(1)
    
    proc_mod = importlib.import_module(sys.argv[1])
    commands = None
    if hasattr(proc_mod, 'commands'):
        commands = proc_mod.commands
    sim = Simulator(proc_mod.processes, proc_mod.links, commands)
    sim.run()

if __name__ == '__main__':
    main()
