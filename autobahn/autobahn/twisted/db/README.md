# AUTODB - Autobahn Database Service

Database Service for Autobahn

## Summary

A simple database construct for Autobahn allowing for different implementations.

Command to start database engine:

```python
import db.py
yield self.call('adm.db.start', 'DRIVER', 'topic_root')
```

valid DRIVERs are:
* PG9\_4	Postgres version v9.4b2 (PG alias)
* MYSQL14\_14	Mysql v14.14 (MYSQL alias)
* SQLITE3\_3\_8\_2	sqlite3 v3.8.2 (SQLITE alias)

what this does is set up the rpc with a prefix of com.db, and calls named:
connect, disconnect, query, operation, watch for the database engine.
The rpc calls in this example would be :

* com.db.connect    start a postgres connection, the dsn is passed, dsn in psycopg2 format
* com.db.disconnect stop the postgres connection
* com.db.query      run a database query async
* com.db.operation  run a database query (no results expected)
* com.db.watch      postgres has a LISTEN operator.  watch lets us specify what to listen for, and what to call when an event is triggered. I think that other drivers will probably just stub this out (unless they have a notify/listen behavior)

The class also has a main routine which will connect to your Autobahn realm as required.  There is a convenience startup feature in the main routine to establish a connection with a database if desired.

```
./db.py --help yields:
usage: db.py [-h] [-w WSOCKET] [-r REALM] [-v] [-u USER] [-s PASSWORD]
             [-e ENGINE] [-d DSN] [-t TOPIC_BASE]

db admin manager for autobahn

optional arguments:
  -h, --help            show this help message and exit
  -w WSOCKET, --websocket WSOCKET
                        web socket ws://127.0.0.1:8080/ws
  -r REALM, --realm REALM
                        connect to websocket using "realm" realm1
  -v, --verbose         Verbose logging for debugging
  -u USER, --user USER  connect to websocket as "user" db
  -s PASSWORD, --secret PASSWORD
                        users "secret" password
  -e ENGINE, --engine ENGINE
                        if specified, a database engine will be attached. Note
                        engine is rooted on --topic
  -d DSN, --dsn DSN     if specified the database in dsn will be connected and
                        ready
  -t TOPIC_BASE, --topic TOPIC_BASE
                        if you specify --dsn then you will need a topic to
                        root it on, the default com.db is fine.
I don't like passing the user and password on the command line, I'll have to get back to that.
```

```sh
python db.py
```

You can fire up the db engine like this, but, it is more useful to use it to fire up your database connections.  For postgres, I would do this:

```
db.py -r dbrealm -u autodb -s autodbsecret -e PG9_4 -t 'com.db' -d 'dbname=autobahn host=ab user=autouser' -v
db.py -r dbrealm -u autodb -s autodbsecret -e MYSQL -t 'com.db' -d 'database=autobahn user=autouser password=123test' -v
db.py -r dbrealm -u autodb -s autodbsecret -e SQLITE -t 'com.db' -d 'dbname=/tmp/autobahn' -v
```

This sets up service for your autobahn router.  The service connects to autobahn using autodb/autodbsecret .  The service is anchored on topic 'com.db' (meaning that all of the calls registered and subscriptions offered will be rooted here, like com.db.query). The postgres database is connected to using the dsn describe by the -d flag. Finally, the -e is the engine, PG9\_4 and MYSQL14\_14 are supported.

