Создаем системного пользователя с домашним каталогом, копируем в него python скрипт и задаем права.
```
sudo useradd -r -U -m -d /opt/onecgetter -s /usr/sbin/nologin onecget
sudo cp onecgetter.py /opt/onecgetter/
sudo cp requirements.txt /opt/onecgetter/
sudo chown root:root /opt/onecgetter/onecgetter.py
sudo chmod 644 /opt/onecgetter/onecgetter.py
```

Устанавливаем в домашний каталог системного пользователя необходимые переменные среды и ПО.
```
sudo -u onecget -s /bin/bash
cd /opt/onecgetter/
python3 -m venv venv
source venv/bin/activate -> (venv) onecget@host:~$
which python -> /opt/onecgetter/venv/bin/python
pip install -r requirements.txt
playwright install chromium
exit
cd
cd onecgetter/
sudo ls -l /opt/onecgetter
```

Делаем systemd юнит для запуска по расписанию, при необходимости корректируем время запуска и папку для хранения резерыных копий.
```
sudo cp onecgetter.service /etc/systemd/system
sudo cp onecgetter.timer /etc/systemd/system
sudo chown root:root /etc/systemd/system/onecgetter.service
sudo chown root:root /etc/systemd/system/onecgetter.timer
sudo chmod 644 /etc/systemd/system/onecgetter.service
sudo chmod 644 /etc/systemd/system/onecgetter.timer
sudo ls -l /etc/systemd/system
sudo mcedit /etc/systemd/system/onecgetter.timer
sudo mcedit /etc/systemd/system/onecgetter.service
```

Создаем каталог для файла конфигурации, копируем шаблон файла конфигурации, задаем нужные параметры, устанавливаем права.
```
sudo mkdir /etc/onecgetter
sudo cp config.env.example /etc/onecgetter/config.env
sudo mcedit /etc/onecgetter/config.env
sudo chown root:root -R /etc/onecgetter/
sudo chmod 600 /etc/onecgetter/config.env
sudo chmod 700 /etc/onecgetter/
sudo ls -l /etc/onecgetter/
```

Создаем папку для хранения резервных копий, указанную в onecgetter.service и config.env, устанавливаем права.
```
sudo mkdir /var/opt/backup/backups
sudo chown -R onecget:onecget /var/opt/backup/backups
sudo chmod 750 -R /var/opt/backup/backups
sudo find /var/opt/backup/backups -type f -exec chmod a-x {} \;
sudo ls -l /var/opt/backup/backups
```

Стартуем сервис, можно сразу сделать первый запуск.
```
sudo systemctl daemon-reload
sudo systemctl enable onecgetter.timer
sudo systemctl start onecgetter.timer
sudo systemctl status onecgetter.timer
systemctl list-timers
sudo systemctl start onecgetter.service
```

Если все прошло ОК, можно закрыть каталог /opt/onecgetter/venv от ззменения пользователем onecget.
```
sudo chown -R root:root /opt/onecgetter/venv
sudo chmod -R go-w /opt/onecgetter/venv
```

Если systemd не поддерживает LoadCredential, то файл конфигурации можно создать в домашнем каталоге пользователя onecget, где он автоматически будет найден.
```
sudo cp config.env.example /opt/onecgetter/configfo.env
mcedit /opt/onecgetter/configfo.env
sudo chmod 600 /opt/onecgetter/configfo.env
sudo chown onecget:onecget /opt/onecgetter/configfo.env

```
