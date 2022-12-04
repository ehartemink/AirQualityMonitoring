## What is this? 

I was curious about the air quality in and around my home. This repository implements data collection (and hopefully eventually visualization) for the concentration of various pollutants from a set of sensors I've connected to a raspberry pi.

## How to use?

* Register your sensors and supply their paths within your `/dev` folder at `config.json`
* From the path of the respository, `python3 main.py` runs the data ingestion
* Similarly, `python3 app.py` runs the dashboard
