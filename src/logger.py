import os

class Logger:
    def __init__(self, output_dir, verbose):
        self.log_file = os.path.join(output_dir, "metadata_processing.log")
        self.verbose = verbose

    def log(self, message):
        with open(self.log_file, "a") as f:
            f.write(message + "\n")
        if "[ERROR]" in message or "[WARNING]" in message or self.verbose:
            print(message)
