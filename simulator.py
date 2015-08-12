import sys
import importlib

class Process(object):
    def __init__(self):
        pass
    
    def process(self, input):
        pass
    
    def get_id(self):
        return self._id


class Simulator(object):
    def __init__(self, processes, links):
        self._processes = processes
        self._links = links
        self._input_queues = [[] for p in processes]
    
    def run(self):
        while True:
            for process in self._processes:
                proc_id = process.get_id()
                proc_input = self.get_input(proc_id)
                if proc_input is None:
                    continue
                
                output = process.process(proc_input)
                self.sent_output(proc_id, output)

            next_round = raw_input('next_round[default:1]: ').strip()
            if next_round == 'exit':
                break
            elif len(next_round) == 0:
                next_round = 1
            else:
                next_round = int(next_round)
            goto_next_round(next_round)
    
    def get_input(self, proc_id):
        if len(self._input_queues[proc_id]) > 0:
            return self._input_queues[proc_id][0]
        else:
            return None

    def sent_output(self, process_id, output):
        for target_process, msg in output.iteritems():
            distance = self._links[(process_id, target_process)]
            queue_size = len(self._input_queues[target_process])
            if queue_size < distance:
                for _ in range(queue_size, distance):
                    self._input_queues[target_process].append([])
            self._input_queues[target_process][distance - 1].append(msg)

    def goto_next_round(next_round):
        for proc in self._processes:
            proc_id = proc.get_id()
            self._input_queues[proc_id] = self._input_queues[proc_id][next_round:]

def main():
    if len(sys.argv) < 2:
        print 'Usage:', argv[0], 'proc_module'
        sys.exit(1)
    
    proc_mod = importlib.import_module(sys.argv[1])
    sim = Simulator(proc_mod.processes, proc_mod.links)
    sim.run()

if __name__ == '__main__':
    main()

