class Process(object):
    def __init__(self):
        pass
    
    def process(self, input):
        pass

def sent_output(process_id, output, processes):
    for target_process, msg in output.iteritems():
        distance = process_link[(process_id, target_process)]
        process_input_queue[target_process][distance].append(msg)

def goto_next_round(next_round):
    pass

def main():
    processes = []
    
    while True:
        for i, process in enumerate(processes):
            input_queue = process.get_input_queue()
            output = process.process(input_queue)
            sent_output(i, output, processes)
            next_round = raw_input('next_round[default:1]: ')
            goto_next_round(next_round)
    
    return

if __name__ == '__main__':
    main()

