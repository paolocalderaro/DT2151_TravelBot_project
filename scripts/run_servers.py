import subprocess
from threading import Thread
import threading
import time
import json
import os
import requests
import logging
from datetime import datetime
import sys, re


logger = logging.getLogger(__name__)
cur_date = str(datetime.now()).replace(" ", "_").replace(":", "-")
idx_dot = cur_date.find(".")
cur_date = cur_date[:idx_dot] if idx_dot != -1 else cur_date
ngrok_lock = threading.Lock()
ngrok_lock.acquire()
os.chdir("..")


try:
    os.makedirs(".\\logs\\voice_based\\")
except:
    pass


def escape_ansi(line):
    ansi_escape =re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
    return ansi_escape.sub('', line)


class RasaEndpoint(Thread):
    def __init__(self, port=5004):
        Thread.__init__(self)
        self.port = port
        self.log_file = f".\\logs\\voice_based\\{cur_date}_rasa_server.log"

    def run(self):
        with open(self.log_file, "w") as fp:
            # run rasa server on localhost, port 'self.port'
            p = subprocess.run(['rasa', 'run', '--enable-api', '-p', str(self.port)],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            for line in p.stdout:
                try:
                    sys.stdout.write(line)
                    fp.write(escape_ansi(line))
                    fp.flush()
                except Exception as e:
                    sys.stdout.write(f"Exception occured in thread {__name__}: {e}")


class RasaActions(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.log_file = f".\\logs\\voice_based\\{cur_date}_rasa_actions.log"

    def run(self):
        with open(self.log_file, "w") as fp:
            p = subprocess.Popen(['rasa', 'run', 'actions', '--debug'],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            for line in p.stdout:
                try:
                    sys.stdout.write(line)
                    fp.write(escape_ansi(line))
                    fp.flush()
                except:
                    pass
        # with open(self.log_file, "w") as fp:
        #     output, err = p.communicate()
        #     fp.writelines(output)
        #
        # fp.close()



class NgrokServer(Thread):
    def __init__(self, port):
        Thread.__init__(self)
        self.port = port
        self.log_file = f".\\logs\\voice_based\\{cur_date}_ngrok_server.log"

    def run(self):
        # make the local server visible from the outside, through ngrok services
        # N.B.: ngrok command must be downloaded and added to the environment variables under PATH.
        # the port (5004) must be the same of the local rasa server
        subprocess.Popen(['ngrok', 'http', str(self.port)], stdout=open(self.log_file, "w"))
        ngrok_lock.release()


class DucklingServer(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.log_file = f".\\logs\\voice_based\\{cur_date}_duckling_server.log"

    def run(self):
        if not self._is_duckling_running():
            subprocess.Popen(['docker', 'run', '-dp', '8000:8000', 'rasa/duckling'], stdout=open(self.log_file, "w"))
        else:
            print("Duckling server is already running")
    def _is_duckling_running(self):
        data = subprocess.Popen(['docker', 'ps',
                                 '--filter', 'ancestor=rasa/duckling',
                                 '--filter', 'status=running'], stdout=subprocess.PIPE)
        return False if len(data.stdout.readlines()) == 1 else True


class GactionsSetup(Thread):
    def __init__(self):
        Thread.__init__(self)
        # self.log_file = f"logs/{cur_date}_gactions.log"
        self.project_id = "test-70c96"
        self.ngrok_url = "localhost:4040"
        self.MAX_RETRY = 5

    def run(self):
        ngrok_lock.acquire()
        cont = 0
        forwarding_address = None
        while cont<self.MAX_RETRY and forwarding_address is None:
            logger.debug(f"run ngrok server. Trial #{cont+1}")
            response = requests.get('http://localhost:4040/api/tunnels')
            ngrok_json = response.json()
            if 'status_code' in ngrok_json and ngrok_json['status_code'] != 200:
                logger.error("Ngrok service not running!")
                exit(1)
            if len(ngrok_json['tunnels']) > 0:
                forwarding_address = ngrok_json['tunnels'][0]['public_url'] + "/webhooks/google_assistant/webhook"
            cont += 1
            logger.debug(f"forwarding address: {forwarding_address}")
        self._set_forwarding_address(forwarding_address)
        subprocess.run(['gactions', 'update', '--action_package', './action.json', '--project', self.project_id])
        subprocess.run(['gactions', 'test', '--action_package', './action.json', '--project', self.project_id])
        # subprocess.run(['gdeploy', 'deploy', 'alpha'])
        ngrok_lock.release()

    def _set_forwarding_address(self, address):
        action_file = open(".//action.json", "r+")
        action_json = json.load(action_file)
        action_json['conversations']['welcome']['url'] = address
        action_json['conversations']['rasa_intent']['url'] = address
        action_file.seek(0)
        action_file.truncate()
        json.dump(action_json, action_file)
        action_file.close()


rasa_server = RasaEndpoint()
rasa_actions_server = RasaActions()
ngrok_server = NgrokServer(port=rasa_server.port)
# duckling_server = DucklingServer()
gactions = GactionsSetup()

rasa_actions_server.start()
rasa_server.start()
ngrok_server.start()
gactions.start()
# duckling_server.start()
