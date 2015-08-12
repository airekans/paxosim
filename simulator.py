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
            for process in processes:
                proc_id = process.get_id()
                proc_input = self.get_input(proc_id)
                output = process.process(proc_input)
                self.sent_output(proc_id, output, processes)

            next_round = raw_input('next_round[default:1]: ').strip()
            if next_round == 'exit':
                break
            goto_next_round(next_round)
    
    def get_input(self, proc_id):
        input = self._input_queues[proc_id][0]
        self._input_queues[proc_id] = self._input_queues[proc_id][1:]

    def sent_output(self, process_id, output):
        for target_process, msg in output.iteritems():
            distance = self._links[(process_id, target_process)]
            self._input_queues[target_process][distance].append(msg)

    def goto_next_round(next_round):
        pass

def main():
    processes = []
    
    sim = Simulator(processes, [])
    sim.run()

if __name__ == '__main__':
    main()

