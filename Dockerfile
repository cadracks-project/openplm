FROM debian:wheezy

MAINTAINER Guillaume Florent <florentsailing@gmail.com>

RUN apt-get update && \
    apt-get install -y swig build-essential pkg-config gettext apache2 \
    libapache2-mod-wsgi python-pip python-dev python-imaging python-kjbuckets \
    python-pypdf ipython graphviz graphviz-dev python-pygraphviz \
    python-xapian rabbitmq-server postgresql libpq-dev python-tz python-pisa \
    libgsf-bin imagemagick python-pisa python-lxml && \
    rm -rf /var/lib/apt/lists/*

RUN pip install pip --upgrade --index-url=https://pypi.python.org/simple/
# RUN pip install odfpy docutils celery django-celery 'django==1.5.2' 'south==0.7.6' psycopg2 'django-haystack<2' librabbitmq markdown lepl
# RUN pip install odfpy docutils celery 'django-celery==3.1.0' 'django==1.5.2' 'south==0.7.6' psycopg2 'django-haystack<2' librabbitmq markdown lepl
RUN pip install odfpy docutils 'celery==3.1.9' 'django-celery==3.1.9' 'django==1.5.2' 'south==0.7.6' psycopg2 'django-haystack<2' librabbitmq markdown lepl

RUN apt-get update && \
    apt-get install -y poppler-utils html2text odt2txt antiword catdoc && \
    rm -rf /var/lib/apt/lists/*

RUN pip install openxmllib

COPY openPLM-2.0.1.tar.gz .

RUN tar xzf openPLM-2.0.1.tar.gz -C /var/

RUN mv /var/openplm /var/django

WORKDIR /var/django/openPLM

RUN sed -in 's#\(/var/django/\)openPLM/trunk/#\1#' settings.py apache/*.wsgi etc/default/celeryd

RUN mkdir /var/postgres

RUN chown postgres:postgres /var/postgres/

RUN locale-gen fr_FR.UTF-8

USER postgres

RUN export PATH=/usr/lib/postgresql/9.1/bin:$PATH

RUN /usr/lib/postgresql/9.1/bin/initdb --encoding=UTF-8 --locale=fr_FR.UTF-8 --pgdata=/var/postgres/

# Now this is interactive -> how to dockerize?
# psql
#   create database openplm;
#   create role django with password 'MyPassword' login;
#   exit
RUN  /etc/init.d/postgresql start && psql --command "create database openplm;" && psql --command "create role django with password 'MyPassword' login;"

USER root

RUN python bin/change_secret_key.py

# edit the file /var/django/openPLM/settings.py and set the database password (‘MyPassword’) It must be the one set with the command create role django with password 'MyPassword' login;

# if connection error for the manage.py commands below
# /etc/init.d/postgresql start

# cd /var/django/openPLM

# ./manage.py syncdb --all
#        will prompt for superuser and company
#        You have to create the superadmin user for Django and a special user named ‘company’.
#        The company can access all contents from openPLM and should sponsor other users.
#        The admin is here to administrate openPLM via its admin interface.
# ./manage.py migrate --all --fake
# ./manage.py loaddata extra_lifecycles



# 1.1.8. Configure where the files are saved
# mkdir /var/openPLM
# chown www-data:www-data /var/openPLM
# DOES NOT WORK ------ chown -R www-data:www-data /var/django/openPLM/trunk/openPLM/media/
# chown -R www-data:www-data /var/django/openPLM/media/

#1.1.9. Configure the search engine
#Although haystack supports several search engines, openPLM needs xapian.
# You may change the setting HAYSTACK_XAPIAN_PATH if you want to put the indexes in another directory.
#Once haystack is configured, you must rebuild the index:
# ./manage.py rebuild_index
# chown www-data:www-data -R /var/openPLM/xapian_index/

# 1.1.10. Configure Celery
# service rabbitmq-server start
# rabbitmqctl add_user openplm 'secret'
# rabbitmqctl add_vhost openplm
# rabbitmqctl set_permissions -p openplm openplm ".*" ".*" ".*"

#Then you must modify the BROKER_* settings in the settings.py, if you follow this tutorial, you only have to change BROKER_PASSWORD.
#
#For example:
#
## settings.py
#BROKER_HOST = "localhost"
#BROKER_PORT = 5672
#BROKER_USER = "openplm"
#BROKER_PASSWORD = "secret"
#BROKER_VHOST = "openplm"
#
#
# celeryd, celery’s daemon must be run. openPLM ships with an init script:
# cp /var/django/openPLM/etc/init.d/celeryd /etc/init.d/celeryd
# cp /var/django/openPLM/etc/default/celeryd /etc/default/celeryd
# chmod +x /etc/init.d/celeryd
# update-rc.d celeryd defaults
#
# To launch celeryd, run:
#  /etc/init.d/celeryd start


#1.1.11. Configure allowed hosts
#
#Django 1.5 checks the host before serving a request.
# You must edit the ALLOWED_HOSTS setting so that django accepts to serve your requests.

# ALLOWED_HOSTS = ["www.example.com", "localhost"]


#1.1.12. Configure Apache server
#
#Create a new apache’s site (/etc/apache2/sites-available/openplm) and add the following lines (replace the server name):
#
#<VirtualHost *:80>
#    ServerName openplm.example.com <----------- replace by localhost
#    DocumentRoot /var/www
#
#    WSGIScriptAlias / /var/django/openPLM/apache/django.wsgi
#    # required to enable webdav access
#    WSGIPassAuthorization On
#
#    <Location ~ "/media/(?!public)">
#        WSGIAccessScript /var/django/openPLM/apache/access_restricted.wsgi
#    </Location>
#
#    Alias /static /var/django/openPLM/static
#    <Directory /var/django/openPLM/static>
#        Order deny,allow
#        Allow from all
#    </Directory>
#
#    Alias /media /var/django/openPLM/media
#    <Directory /var/django/openPLM/media>
#        Order deny,allow
#        Allow from all
#    </Directory>
#
#</VirtualHost>


#1.1.13. Restart Apache server
#
# a2ensite openplm
# service apache2 reload
# service apache2 restart


















