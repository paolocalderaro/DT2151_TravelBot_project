import subprocess
from threading import Thread
import threading
import time
import json
import os
import sys
import requests
import logging
from datetime import datetime
import glob
import os.path
import re


logger = logging.getLogger(__name__)
SIMPLE_LOG_FORMAT = '[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s - %(processName)s %(threadName)s'
logger.setLevel(logging.INFO)
formatter = logging.Formatter(SIMPLE_LOG_FORMAT)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.info("Message before redirecting stdout and stderr")
# Checking what logger is writing to
logger.info('Before Redirection. logger writing to {} '.format(logger.handlers[0].stream))

cur_date = str(datetime.now()).replace(" ", "_").replace(":", "-")
idx_dot = cur_date.find(".")
cur_date = cur_date[:idx_dot] if idx_dot != -1 else cur_date
ngrok_lock = threading.Lock()
ngrok_lock.acquire()
if not os.path.exists("config.yml"):
    os.chdir("..")

try:
    os.makedirs(".\\logs\\text_based\\")
except:
    pass


def escape_ansi(line):
    ansi_escape =re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
    return ansi_escape.sub('', line)


class RasaX(Thread):
    def __init__(self, port=5002):
        Thread.__init__(self)
        self.port = port
        self.log_file = f".\\logs\\text_based\\{cur_date}_rasa_x_server.log"
        self.last_model_name = ".\\models"

    def _get_last_model(self):
        latest_model = "models"
        try:
            folder_path = r'.\models'
            file_type = '\*gz'
            files = glob.glob(folder_path + file_type)
            latest_model = max(files, key=os.path.getctime)
        except:
            pass
        return str(latest_model)

    def run(self):
        self.last_model_name = self._get_last_model()
        logger.debug(f"Latest found model: {self.last_model_name}")
        try:
            with open(self.log_file, "w") as fp:
                # run rasa x server on localhost
                p = subprocess.Popen(['rasa', 'x', '--debug', '--rasa-x-port', str(self.port), "--model", self.last_model_name],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                for line in p.stdout:
                    try:
                        sys.stdout.write(line)
                        fp.write(escape_ansi(line))
                    except Exception as e:
                        sys.stdout.write(f"EXCEPTION DURING HANDLING OUTPUT: {e}")
        except Exception as e:
            sys.stdout.write(f"EXCEPTION IN THREAD {self.name}, funcion run")


class RasaActions(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.log_file = f".\\logs\\text_based\\{cur_date}_rasa_actions.log"

    def run(self):
        with open(self.log_file, "w") as fp:
            p = subprocess.Popen(['rasa', 'run', 'actions'],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            for line in p.stdout:
                try:
                    sys.stdout.write(line)
                    fp.write(escape_ansi(line))
                    fp.flush()
                except Exception as e:
                    sys.stdout.write(f"EXCEPTION DURING HANDLING OUTPUT: {e}")


class NgrokServer(Thread):
    def __init__(self, port):
        Thread.__init__(self)
        self.port = port
        self.log_file = f".\\logs\\text_based\\{cur_date}_ngrok_server.log"
        self.ngrok_url = "localhost:4040"
        self.development_suffix = "/guest/conversations/development/3e2bf3215a3c43e38d0d5821a8348b94"
        self.MAX_RETRY = 5

    def run(self):
        subprocess.Popen(['ngrok', 'http', str(self.port)])
        cont = 0
        forwarding_address = None
        while cont < self.MAX_RETRY and forwarding_address is None:
            logger.debug(f"Extract ngrok url. Trial #{cont + 1}")
            response = requests.get('http://localhost:4040/api/tunnels')
            ngrok_json = response.json()
            if 'status_code' in ngrok_json and ngrok_json['status_code'] != 200:
                logger.error("Ngrok service not running!")
                exit(1)
            if len(ngrok_json['tunnels']) > 0:
                forwarding_address = ngrok_json['tunnels'][0]['public_url']
            cont += 1
            logger.info(f"FORWARDING ADDRESS: {forwarding_address}{self.development_suffix}")
        with open("FORWARDING_ADDRESS_RASA_X.txt", "w") as fp:
            fp.write(f"{forwarding_address}{self.development_suffix}")
        return forwarding_address


rasa_x_server = RasaX()
rasa_actions_server = RasaActions()
ngrok_server = NgrokServer(port=rasa_x_server.port)

rasa_actions_server.start()
rasa_x_server.start()
ngrok_server.start()
