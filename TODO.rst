Tutos openPLM
Test FreeCAD openPLM WB connection with an instance (URL of VM!)
  ******** Test login -> OK
  -> Continuer à debugger les commandes du WB

Dockerfile
----------
Use clone a repo (git) instead of copy tar archive

Hos to automate the django superuser and special user creation?
  /manage.py syncdb --all --noinput
  echo "from django.contrib.auth.models import User; User.objects.create_superuser('superuser', 'superuser@superuser.com', 'superuser')" | python manage.py shell
    and later (via web ui) create user 'company' that is active and part of the 'leading_group' group

The web server should work as a daemon