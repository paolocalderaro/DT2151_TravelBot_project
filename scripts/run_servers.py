import subprocess
from threading import Thread
import threading
import time
import json
import os
import requests
import logging

logger = logging.getLogger(__name__)
cur_time_ns = time.time_ns()
ngrok_lock = threading.Lock()
ngrok_lock.acquire()
os.chdir("..")


class RasaEndpoint(Thread):
    def __init__(self, port=5004):
        Thread.__init__(self)
        self.port = port
        self.log_file = f".//logs//{cur_time_ns}_rasa_server.out"

    def run(self):
        # run rasa server on localhost, port 'self.port'
        subprocess.run(['rasa', 'run', '--enable-api', '-p', str(self.port), '--log-file', self.log_file, '--debug'],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.STDOUT
                       )


class RasaActions(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.log_file = f"./logs/{cur_time_ns}_rasa_actions.out"

    def run(self):
        p = subprocess.Popen(['rasa', 'run', 'actions', '--debug'], stdout=subprocess.PIPE)
        # with open(self.log_file, "w") as fp:
        #     output, err = p.communicate()
        #     fp.writelines(output)
        #
        # fp.close()



class NgrokServer(Thread):
    def __init__(self, port):
        Thread.__init__(self)
        self.port = port
        self.log_file = f".//logs//{cur_time_ns}_ngrok_server.out"

    def run(self):
        # make the local server visible from the outside, through ngrok services
        # N.B.: ngrok command must be downloaded and added to the environment variables under PATH.
        # the port (5004) must be the same of the local rasa server
        subprocess.Popen(['ngrok', 'http', str(self.port)], stdout=open(self.log_file, "w"))
        ngrok_lock.release()


class DucklingServer(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.log_file = f".//logs//{cur_time_ns}_duckling_server.out"

    def run(self):
        subprocess.Popen(['docker', 'run', '-dp', '8000:8000', 'rasa/duckling'], stdout=open(self.log_file, "w"))


class GactionsSetup(Thread):
    def __init__(self):
        Thread.__init__(self)
        # self.log_file = f"logs/{cur_time_ns}_gactions.out"
        self.project_id = "test-70c96"
        self.ngrok_url = "localhost:4040"

    def run(self):
        ngrok_lock.acquire()
        response = requests.get('http://localhost:4040/api/tunnels')
        ngrok_json = response.json()
        if 'status_code' in ngrok_json and ngrok_json['status_code'] != 200:
            logger.error("Ngrok service not running!")
            exit(1)
        forwarding_address = ngrok_json['tunnels'][0]['public_url'] + "/webhooks/google_assistant/webhook"
        self._set_forwarding_address(forwarding_address)
        subprocess.run(['gactions', 'update', '--action_package', './action.json', '--project', self.project_id])
        subprocess.run(['gactions', 'test', '--action_package', './action.json', '--project', self.project_id])
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
duckling_server = DucklingServer()
gactions = GactionsSetup()

rasa_actions_server.start()
rasa_server.start()
ngrok_server.start()
gactions.start()
duckling_server.start()
