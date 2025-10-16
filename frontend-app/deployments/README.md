**Быстрое разворачивание фронтенда**

**Установка git**
```sh
sudo apt install git
```
**Установка docker**
[Официальная документация](https://docs.docker.com/engine/install/ubuntu/)
```sh
sudo apt-get remove docker docker-engine docker.io containerd runc
sudo apt-get update
sudo apt-get install apt-transport-https ca-certificates curl gnupg lsb-release

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io
```
**Проверить установку**
```sh
sudo docker run hello-world
```
**Скачивание исходного кода из git**
```sh
git clone
```
**Далее заходим в папку с клонированным проектом**
```sh
cd <work folder>
```
**И запускаем сборку контейнера**
```sh
docker build -t rueo_front -f ./deployments/Dockerfile ./
```
**Запускаем контейнер**
```sh
docker run -d --name rueo_front -p 80:80 --rm -it rueo_front:latest
```
