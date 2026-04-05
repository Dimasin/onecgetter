```
sudo useradd -r -U -m -d /opt/onecgetter -s /usr/sbin/nologin onecget
sudo cp onecgetter.py /opt/onecgetter/
sudo cp config.env.example /opt/onecgetter/
sudo cp requirements.txt /opt/onecgetter/
sudo cp /opt/onecgetter/config.env.example /opt/onecgetter/config.env
sudo chown -R onecget:onecget /opt/onecgetter/
sudo chmod 600 /opt/onecgetter/config.env
sudo chown root:root /opt/onecgetter/onecgetter.py
sudo chmod 644 /opt/onecgetter/onecgetter.py

sudo -u onecget -s /bin/bash

cd /opt/onecgetter/
python3 -m venv venv
source venv/bin/activate
which python
pip install -r requirements.txt
playwright install chromium
mcedit config.env
exit
cd

sudo cp onecgetter.service /etc/systemd/system
sudo cp onecgetter.timer /etc/systemd/system
sudo chown root:root /etc/systemd/system/onecgetter.service
sudo chown root:root /etc/systemd/system/onecgetter.timer
sudo chmod 644 /etc/systemd/system/onecgetter.service
sudo chmod 644 /etc/systemd/system/onecgetter.timer
ls -l /etc/systemd/system

sudo systemctl daemon-reload
sudo systemctl enable onecgetter.timer
sudo systemctl start onecgetter.timer
sudo systemctl status onecgetter.timer
systemctl list-timers
```
