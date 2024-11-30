"""Python file with different utilities helpfull for all projects."""
import logging
import os
import sys
import queue
from logging.handlers import QueueHandler, QueueListener
import hashlib
import httpx
import websocket 

class WSLogHandler(logging.Handler):
    """
    Dummy logging handler that sends log records to a specified HTTP URL.
    """
    def __init__(self, url, username=None, password=''):
        super().__init__()
        self.url = url
        self.headers = None
        if username:
            self.headers =\
            [f"Authorization: {hashlib.md5(f'{username}:{password}'.encode('utf-8')).hexdigest()}"]
        self.socket: websocket.WebSocket = None
        self._reconnect()
    
    def _reconnect(self):
        
        if self.socket is None or self.socket.connected == False:
            self.socket = websocket.create_connection(self.url, header = self.headers)

    def emit(self, record):
        try:
            self._reconnect()
            message = '{"level":' + str(record.levelno) + ', "msg":"' + self.format(record) + '"}\n'
            self.socket.send(message)

        except Exception:
            self.handleError(record)

        
class HttpHandler(logging.Handler):
    """
    Dummy logging handler that sends log records to a specified HTTP URL.
    """
    def __init__(self, url, username=None, password=''):
        super().__init__()
        self.url = url
        self.client = httpx.Client()
        if username:
            self.client.headers = {"Authorization": hashlib.md5(f'{username}:{password}'.encode('utf-8')).hexdigest()}
    def emit(self, record):
        try:
            self.client.post(self.url, json=dict(level = record.levelno, msg = self.format(record))).status_code
        except Exception:
            self.handleError(record)

    

def make_logger(name: str,
                encoding: str = 'utf-8',
                write_to_console: bool = True,
                write_to_file: bool = False,
                write_to_url: bool = False,
                path_to_file: list = None,
                url: str = None,
                method: str = None,
                async_logging: bool = False,
                format: str = '%(asctime)s | %(funcName)s | %(levelname)s | %(message)s',
                datefmt: str = '%d-%m-%Y %H:%M:%S',
                level: str = 'INFO',
                **kwargs
                ) -> logging.Logger:
    """
    Function to make your perfect logger!\n
    - `name`, `write_to_console` and `encoding` are self-explanatory\n
    - `path_to_file` must be a list that contains directions to your desired folder starting from 
    palcement of this module\n
    - `write_to_url` allows you to write asyncly or not to urls, to use it `url` must be specified
    , but API or auth credentials are not nessesary
    - Right now `write_to_url` is not working, this is because it is impossible to make correct
    format for every web app that exists (some require signatures abtanable through API, others
    make you include username and password within body of responce). So that's why in addition to
    supplying link you must also provide name of the logging handler and all nessesary `**kwargs`
    for that handler to function.
    """

    url_handlers = {
        "WSLogHandler": WSLogHandler,
        "HttpHandler": HttpHandler

    }
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    logger = logging.getLogger(name=name)
    logger.setLevel(levels.get(level.upper(), logging.INFO))
    if logger.hasHandlers():
        logger.handlers.clear()
    
    formatter = logging.Formatter(fmt=format, datefmt=datefmt)

    if not write_to_console and not write_to_file and not write_to_url:
        raise ValueError("At least one of write_to_console, write_to_file, or write_to_url must be True.")

    if async_logging:
        log_queue = queue.Queue(-1)
        queue_handler = QueueHandler(log_queue)
        logger.addHandler(queue_handler)
        
        handlers = []
        if write_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            handlers.append(console_handler)
        
        if write_to_file:
            if path_to_file is not None:
                file_path = os.path.join(os.getcwd(), *path_to_file)
                os.makedirs(file_path, exist_ok=True)
                log_file = os.path.join(file_path, f'{name}.log')
                file_handler = logging.FileHandler(filename=log_file, encoding=encoding)
            else:
                file_path = os.getcwd()
                log_file = os.path.join(file_path, f'{name}.log')
                file_handler = logging.FileHandler(filename=log_file, encoding=encoding)
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        
        if write_to_url:
            if url is None or url_handlers.get(method, None) is None:
                raise ValueError("url and method must be specified when write_to_url is True.")
            else:
                kwargs['url'] = url
                url_handler = url_handlers[method](**kwargs)
                url_handler.setFormatter(formatter)
                handlers.append(url_handler)

        listener = QueueListener(log_queue, *handlers)
        listener.start()

        logger.listener = listener

    else:
        if write_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        if write_to_file:
            if path_to_file is not None:
                file_path = os.path.join(os.getcwd(), *path_to_file)
                os.makedirs(file_path, exist_ok=True)
                log_file = os.path.join(file_path, f'{name}.log')
                file_handler = logging.FileHandler(filename=log_file, encoding=encoding)
            else:
                file_path = os.getcwd()
                log_file = os.path.join(file_path, f'{name}.log')
                file_handler = logging.FileHandler(filename=log_file, encoding=encoding)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        if write_to_url:
            if url is None or url_handlers.get(method, None) is None:
                raise ValueError("url and method must be specified when write_to_url is True.")
            else:
                kwargs['url'] = url
                url_handler = url_handlers[method](**kwargs)
                url_handler.setFormatter(formatter)
                logger.addHandler(url_handler)

    return logger

def logmsg(message, **kwargs):
    if kwargs:
        return f'{message} || ' + '; '.join(f'{k}: {v}' for k,v in kwargs.items() if v is not None)
    return str(message)

if __name__ == '__main__':
    logger = make_logger(name='suka', async_logging=True, write_to_url=True,
                         url = "http://localhost:8888/sendlog", method="HttpHandler", username="test",
                         password="test")
    logger.error(logmsg(message = "sss", fuck = "sssssasdfgadsfgsadgfr", six = 6))
    import time
    t0 = time.time_ns()
    for i in range(100):
        logger.info(logmsg('test', counter = i))
    print((time.time_ns()-t0)/100)