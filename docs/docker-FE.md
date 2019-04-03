How to prepare the Frontend Docker container
============================================

To create a docker container which runs the frontend web component. We start with [uwsgi-nginx-flask](https://hub.docker.com/r/tiangolo/uwsgi-nginx-flask/) which is a base docker image which has both uWSGI and Nginx for running Flask applications.

# Installation Steps

1. Create dockerfile

2. Create uWSGI config files

3. Create app config file

4. Build docker container

5. Start docker container

6. It takes a little while for the web service to get running

7. Test application is running within container

```shell
cat << EOF > ~/planespotter/frontend/dockerfile
FROM tiangolo/uwsgi-nginx-flask:flask

MAINTAINER Darryl Cauldwell "darryl.cauldwell@gmail.com"

RUN pip install flask-paginate
RUN pip install requests
RUN pip install netifaces

COPY ./uwsgi.ini /etc/uwsgi/uwsgi.ini
COPY ./uwsgi-streaming.conf /etc/nginx/conf.d/
COPY ./app /app

EOF

cat << EOF > ~/planespotter/frontend/uwsgi-streaming.conf
uwsgi_buffering off;
uwsgi_cache off;

EOF

cat << EOF > ~/planespotter/frontend/uwsgi.ini
[uwsgi]
socket = /tmp/uwsgi.sock
chown-socket = nginx:nginx
chmod-socket = 664
cheaper = 2
processes = 16
enable-threads = true

EOF

cat << EOF > ~/planespotter/frontend/app/frontend.ini
[uwsgi]
module = wsgi:app
master = true
processes = 5
socket = frontend.sock
chmod-socket = 660
vacuum = true
die-on-term = true
logto = /var/log/uwsgi/%n.log
env = PLANESPOTTER_API_ENDPOINT=planespotter-api.darrylcauldwell.com
EOF

docker build -t planespotter-frontend:latest .
docker run -d --name planespotter-frontend -p 80:80 planespotter-frontend
sleep 1m
curl http://127.0.0.1
docker stop $(docker ps -a -q --filter ancestor=planespotter-frontend --format="{{.ID}}")
docker commit -m "Created Planespotter frontend" -a "NAME" planespotter-frontend dcauldwell/planespotter-frontend:latest
docker login
docker push dcauldwell/planespotter-frontend
```