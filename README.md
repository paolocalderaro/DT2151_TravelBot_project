# Travel Bot
### Environment Setup

#### Requirements:
- [Docker ](https://www.docker.com/get-started)
- [gactions](https://developers.google.com/assistant/actionssdk/gactions)
- [ngrok](https://ngrok.com/download)
- [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/download.html)
- [Rasa/duckling image](https://hub.docker.com/r/rasa/duckling): use **docker pull rasa/duckling** from CLI after downloading docker

> Make sure that the paths to ngrok and gactions are added to the PATH environment variable
> set PATH=%PATH%;C:\your\path\here\

#### Prepare the environment

Open the CLI

> conda create -n "rasa_env" python==3.8
> 
> conda activate rasa_env
> 
> pip install rasa==2.8.6
> 
> conda install -c conda-forge spacy
> 
> python -m spacy download en_core_web_md
> 
> pip install pip==20.2
> 
> pip3 install rasa-x==0.39.3 —-extra-index-url https://pypi.rasa.com/simple —-use-deprecated=legacy-resolver --use-feature=2020-resolver
> 
> pip install sanic-jwt==1.6.0
> 
> python run_servers.py

Additional requirements:

> pip install -U deep-translator
> 
> pip install langdetect


Then, you can finally open you Google Assistant console and test your project.



