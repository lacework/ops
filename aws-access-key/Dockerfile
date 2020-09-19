# dockerfile for AWS access key script
FROM ubuntu:latest

WORKDIR /opt/

RUN apt-get update && apt-get -y install wget gnupg2 vim
RUN wget -qO- https://repos.influxdata.com/influxdb.key |  apt-key add -
RUN echo "deb https://repos.influxdata.com/ubuntu bionic stable" | tee /etc/apt/sources.list.d/influxdb.list
RUN apt-get update && apt-get -y install telegraf python3 python3-pip

COPY requirements.txt .

RUN python3 -m pip install -r requirements.txt

COPY . .

RUN /bin/rm /etc/telegraf/telegraf.conf ; /bin/ln -s /opt/telegraf/telegraf.conf /etc/telegraf/telegraf.conf
RUN /bin/ln -s /opt/aws ~/.aws

CMD ["/usr/bin/telegraf", "--config", "/opt/telegraf.conf"]
