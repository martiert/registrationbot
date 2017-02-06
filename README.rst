***************
RegistrationBot
***************

This is a simple bot to register people (aimed at students for now), that are interested in a job.
The bot uses Cisco Spark as a backend.

The bot requires:

- python >= 3.5
- mongodb server with username+password authentication
- a webserver, like nginx, to proxy from the url you give the bot to localhost:3000
- The python packages listed in requirements.txt (I highly encourage you to run it in a virtualenv)

To start the bot, create a Cisco Spark bot token at https://developer.ciscospark.com, and run

./registrationbot.py --database <database name> --username <username for db> --password <password for db> --webhook <url for callbacks> --token <cisco spark bot token>
