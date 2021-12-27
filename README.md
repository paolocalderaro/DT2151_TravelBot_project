# Travel Bot
### Environment Setup

#### Requirements:
- [Docker ](https://www.docker.com/get-started)
- [gactions](https://developers.google.com/assistant/actionssdk/gactions)
- [ngrok](https://ngrok.com/download)
- [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/download.html)
- [Rasa/duckling image](https://hub.docker.com/r/rasa/duckling): use **docker pull rasa/duckling** from CLI after downloading docker

> Make sure that the paths to ngrok and gactions are added to the PATH environment variable

#### Prepare the environment

Open the CLI from the path of the project (same location of **requirements.txt**)

> conda create -n "rasa_env" --file requirements.txt 
> 
> conda activate rasa_env
> 
> cd scripts	
> 
> python run_servers.py



