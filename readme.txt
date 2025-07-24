sudo apt update
sudo apt upgrade
sudo apt install python3
sudo apt install python3-pip
sudo apt install chromium
sudo apt install chromium-driver

Now install requirements:

pip3 install -r requirements.txt

If upper command not worked for installing requirements:

pip3 install -r requirements.txt --break-system-packages

Fill .env

RUN Code:

python3 main.py


If you want to host on vps then stop your bot and give below commands:

sudo apt install screen
screen
python3 main.py
