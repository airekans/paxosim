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
        self._links = {}
        for k, v in links.iteritems():
            id1, id2 = k
            self._links[(id1, id2)] = v
            self._links[(id2, id1)] = v
        
        self._input_queues = [[{}] for p in processes]  # Initial input
        self._cur_time = 0
    
    def run(self):
        skip_round_num = 1
        while True:
            for process in self._processes:
                proc_id = process.get_id()
                proc_input = self.get_input(proc_id)
                if proc_input is None:
                    continue
                
                output = process.process(proc_input, self._cur_time)
                if output:
                    self.sent_output(proc_id, output)

            skip_round_num -= 1
            if skip_round_num <= 0:
                try:
                    next_round = raw_input('next_round[default:1]: ').strip()
                    if next_round == 'exit':
                        break
                    elif len(next_round) == 0:
                        next_round = 1
                    else:
                        next_round = int(next_round)

                    skip_round_num = next_round if next_round > 0 else 1
                except EOFError:
                    break
            
            self.goto_next_round(1)
    
    def get_input(self, proc_id):
        if len(self._input_queues[proc_id]) > 0:
            return self._input_queues[proc_id][0]
        else:
            return None

    def sent_output(self, process_id, output):
        distance = 0
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

    def goto_next_round(self, next_round):
        self._cur_time += next_round
        for proc in self._processes:
            proc_id = proc.get_id()
            self._input_queues[proc_id] = self._input_queues[proc_id][next_round:]

def main():
    if len(sys.argv) < 2:
        print 'Usage:', sys.argv[0], 'proc_module'
        sys.exit(1)
    
    proc_mod = importlib.import_module(sys.argv[1])
    sim = Simulator(proc_mod.processes, proc_mod.links)
    sim.run()

if __name__ == '__main__':
    main()
