"""Python file with different utilities helpfull for all projects."""
import logging
import os
import sys
import asyncio
import queue
from logging.handlers import QueueHandler, QueueListener

import requests
import websockets

class HTTPLogHandler(logging.Handler):
    """
    Dummy logging handler that sends log records to a specified HTTP URL.
    """
    def __init__(self, url, api_key=None, api_secret=None, username=None, password=None):
        super().__init__()
        self.url = url
        self.api_key = api_key
        self.api_secret = api_secret
        self.username = username
        self.password = password

    def emit(self, record):
        try:
            log_entry = self.format(record)

            headers = {'Content-Type': 'application/json'}
            data = {'log': log_entry}

            # Add authentication if provided
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)
            elif self.api_key and self.api_secret:
                headers['API_KEY'] = self.api_key
                headers['API_SECRET'] = self.api_secret

            # Send the log entry to the specified URL
            response = requests.post(self.url, json=data, headers=headers, auth=auth)
            response.raise_for_status()

        except Exception:
            self.handleError(record)

class WebSocketLogHandler(logging.Handler):
    """
    Real - used websocket handler. Allows you to connect to specified socket and send logs to it.
    """
    def __init__(self, url, api_key=None, api_secret=None, username=None, password=None):
        super().__init__()
        self.url = url
        self.api_key = api_key
        self.api_secret = api_secret
        self.username = username
        self.password = password
        asyncio.run(self.setup(url))
    
    

    def emit(self, message):
        await self.ws.send(message)

    async def setup(self, url):
        async with websockets.connect(url) as websocket:
            await websocket.send("Hello, Server!")
            print("Message sent to server")

            response = await websocket.recv()
            print(f"Received: {response}")
            self.ws = websocket
        
        

    

def make_logger(name: str,
                encoding: str = 'utf-8',
                write_to_console: bool = True,
                write_to_file: bool = False,
                write_to_url: bool = False,
                path_to_file: list = None,
                url: str = None,
                method: str = None,
                async_logging: bool = False,
                format: str = '%(asctime)s / %(name)s / %(levelname)s / %(message)s',
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
        "HTTPLogHandler": HTTPLogHandler,
        "WebSocketLogHandler": WebSocketLogHandler
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

if __name__ == '__main__':
    logger = make_logger(name='suka', async_logging=True, write_to_url=True,
                         url = "ws://localhost:8765", method="WebSocketLogHandler")
    logger.error("sss")
    logger.info('ppp')

    print(1)