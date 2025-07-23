class FileLogger:
    def __init__(self, log_file='filelogger.log'):
        self.log_file = log_file

    def log(self, message: str):
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
