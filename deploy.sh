sudo mkdir /run/screen
sudo chmod 777 /run/screen
screen -X -S main kill
screen -X -S app kill
screen -d -S air_quality_data_ingestion -m python3 main.py
screen -d -S air_quality_dashboard -m python3 app.py
