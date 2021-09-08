![Envinorma Logo](./back_office/assets/favicon-light.ico)

# Envinorma back-office

Back office du projet Envinorma. Permet la gestion de la base de données des arrêtés ministériels. L'instance principale est accessible [ici](https://envinorma-back-office.herokuapp.com).

![back_office](./back_office/assets/screenshot.png)

# Exécuter en local

## 1. Créer une base de donnée

- Installer postgresql
- Initialiser les tables à partir du backup le plus récent contenu dans `backups/` :

```sh
pg_restore -d DATABASE_NAME 2021-09-01-15-56.dump
```

## 2. Cloner ce dépôt

```sh
git clone git@github.com:Envinorma/back-office.git
cd back-office
```

## 3. Initialiser les variables d'environnement

- Copier la config

```sh
cp config_template.ini config.ini
```

Définir les variables d'environnement suivantes :

- legifrance.client_id
- legifrance.client_secret
- storage.psql_dsn: postgres://\<USERNAME\>@0.0.0.0:5432/\<DATABASE_NAME\>
- slack.enrichment_notification_url: optionel, pour l'envoi des alertes slack
- login.username
- login.password
- login.secret_key

## 4. Installer les dépendances

```sh
virtualenv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

## 5. Exécuter les tests

```sh
make test-and-lint
```

## 6. Lancer l'application

```sh
make start
```

Visiter http://127.0.0.1:8050/

## 7. Déployer sur heroku

- installer la CLI heroku : https://devcenter.heroku.com/articles/heroku-cli
- s'identifier

```sh
heroku login
```

- ajouter le dépôt distant Heroku

```sh
heroku git:remote -a envinorma-back-office
```

- déployer 

```sh
git push heroku main:master
```

# Structure

```
back_office : sources files
|-- app.py : entry point for server running
|-- app_init.py : Dash initialization
|-- config.py : environment variables handling
|-- routing.py : routing
|-- utils.py : various utils
|-- assets : static assets
|-- components : isolated components shared between pages (am, diff, table,...)
|-- pages : pages mapped via router
|-- helpers : various helpers
```
