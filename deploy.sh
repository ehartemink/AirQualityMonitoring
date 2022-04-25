sudo mkdir /run/screen
sudo chmod 777 /run/screen
screen -X -S main kill
screen -X -S app kill
screen -d -S main -m python3 main.py -S
screen -d -S app -m python3 app.py -S
