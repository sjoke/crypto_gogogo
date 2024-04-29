pip3 install pip3 -U
pip3 config set global.index-url https://mirrors.cloud.tencent.com/pypi/simple
pip3 install -r requirements.txt

cd ~/Downloads/taoli
jupyter lab
# sudo rm -rf /usr/lib/python3.12/EXTERNALLY-MANAGED