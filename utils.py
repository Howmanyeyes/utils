"""Python file with different utilities helpfull for all projects."""
import logging
import os
import sys
import queue
from logging.handlers import QueueHandler, QueueListener
import hashlib
import httpx
import websocket 
from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from logging import LogRecord
import json

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
            data = json.dumps(self.format(record), ensure_ascii= False, indent= 0)
            self.socket.send(data)

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
            self.client.post(self.url, json=self.format(record)).status_code
        except Exception:
            self.handleError(record)

class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Start with the basic log format
        base_message = super().format(record)
        # Check if "kwargs" attribute exists in the log `record`. If yes, format and append them
        if isinstance(record.args, Mapping):
            formatted_kwargs = " || " + ", ".join(f"{key}: {value}" for key, value in record.args.items())
            return base_message + formatted_kwargs
        else:
            return base_message
        
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> dict:
        data = dict(level = record.levelno,
                    message = record.message, 
                    levelname = record.levelname,
                    timestamp = self.formatTime(record, self.datefmt),
                    funcName = record.funcName)
        if record.exc_info:
            data['error'] = self.formatException(record.exc_info)
        if record.args:
            if isinstance(record.args, Mapping):
                data.update(record.args)
            elif isinstance(record.args, Iterable):
                data.update({f'arg{i}':v for i, v in enumerate(record.args)})
        return data


def setup_logger(name: str = 'default',
                encoding: str = 'utf-8',
                stdout: bool = True,
                filepath: str | None = None,
                logserver_url: str | None = None,
                text_format: str = '%(asctime)s | %(funcName)s | %(levelname)s | %(message)s',
                datefmt: str = '%Y-%m-%dT%H:%M:%S%z',
                level: int | str = 20,
                **kwargs
                 ):
    main_logger = logging.getLogger(name)
    main_logger.setLevel(level=level)
    if main_logger.hasHandlers():
        main_logger.handlers.clear()

    log_queue = queue.Queue(-1)
    queue_handler = QueueHandler(log_queue)
    main_logger.addHandler(queue_handler)

    if filepath or stdout:
        txtformatter = TextFormatter(fmt= text_format, datefmt=datefmt)

    handlers = []
    if filepath:
        dir = os.path.dirname(filepath)
        os.makedirs(dir, exist_ok=True)
        fileh = logging.FileHandler(filepath, encoding= encoding)
        fileh.setFormatter(txtformatter)
        handlers.append(fileh)
    
    if stdout:
        stdouth = logging.StreamHandler(sys.stdout)
        stdouth.setFormatter(txtformatter)
        handlers.append(stdouth)

    if logserver_url:
        handler_type = WSLogHandler if logserver_url.startswith('ws') else HttpHandler
        username = kwargs.get('username', None)
        password = kwargs.get('password', None)
        logserverh = handler_type(url= logserver_url, username=username, password=password)
        jsfmt = JsonFormatter(datefmt=datefmt)
        logserverh.setFormatter(jsfmt)
        handlers.append(logserverh)

    listener = QueueListener(log_queue, *handlers)
    listener.start()
    main_logger.listener = listener
    return main_logger
    
    

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
                datefmt: str = '%Y-%m-%dT%H:%M:%S%z',
                level: str = 'INFO',
                **kwargs
                ) -> logging.Logger:
    """
    Deprecated!
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
    logger = setup_logger("testlogger",
                          filepath="./log.txt",
                          logserver_url='http://localhost:8000/logs/log',
                          username = 'test',
                          password = "testtest")
    
    for i in range(10):
        logger.warning('i fucked a cow', dict(counter = i))
    
    import time
    time.sleep(1)