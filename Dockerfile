FROM ubuntu:18.04

# install packages
RUN sed -i 's:^path-exclude=/usr/share/man:#path-exclude=/usr/share/man:' /etc/dpkg/dpkg.cfg.d/excludes
# use Taiwan mirrors
RUN echo \
'deb http://tw.archive.ubuntu.com/ubuntu/ bionic main restricted universe multiverse\n\
deb http://tw.archive.ubuntu.com/ubuntu/ bionic-updates main restricted universe multiverse\n\
deb http://tw.archive.ubuntu.com/ubuntu/ bionic-security main restricted universe multiverse\n\
deb-src http://tw.archive.ubuntu.com/ubuntu/ bionic main restricted universe multiverse\n\
deb-src http://tw.archive.ubuntu.com/ubuntu/ bionic-updates main restricted universe multiverse\n\
deb-src http://tw.archive.ubuntu.com/ubuntu/ bionic-security main restricted universe multiverse\n' \
> /etc/apt/sources.list
RUN apt-get update
RUN apt-get install -y vim grep iputils-ping
RUN apt-get install -y tcpdump python3
RUN apt-get install -y openssh-server

RUN mkdir /var/run/sshd
RUN apt-get update --fix-missing && apt-get install -y python3-pip
RUN python3 -m pip install --upgrade pip
COPY requirements.txt /
RUN python3 -m pip install -r /requirements.txt
COPY . /

CMD ["/gbm.py"]

