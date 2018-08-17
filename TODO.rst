Toolbar items in a more logical order (login not at the end when it is the first thing to do!)
Tutos openPLM
Test FreeCAD openPLM WB connection with an instance (URL of VM!)
  ******** Test login -> OK
  -> Continuer à debugger les commandes du WB
      DEV MODE FOR DJANGO SERVER  -> easier debug
          Prod vs Dev paths in manuel (commented part) of Dockerfile
      Traces dans openPLM.py

Dockerfile
----------
Use clone a repo (git) instead of copy tar archive

Hos to automate the django superuser and special user creation?
  /manage.py syncdb --all --noinput
  echo "from django.contrib.auth.models import User; User.objects.create_superuser('superuser', 'superuser@superuser.com', 'superuser')" | python manage.py shell
    and later (via web ui) create user 'company' that is active and part of the 'leading_group' group

The web server should work as a daemon
