#!/usr/bin/env python
###############################################################################
##
##  Copyright (C) 2014 Greg Fausak
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##        http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

import sys,os,argparse,six

from twisted.python import log
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.endpoints import clientFromString

#from myapprunner import MyApplicationRunner
from autobahn.twisted.wamp import ApplicationSession,ApplicationRunner

from autobahn import util
from autobahn.wamp import auth
from autobahn.wamp import types
from autobahn.wamp.exception import ApplicationError
from autobahn.twisted import wamp, websocket
from autobahn.twisted.wamp import ApplicationSession

class DB(ApplicationSession):
    """
    An application component providing db access
    """

    def __init__(self, *args, **kwargs):
        log.msg("__init__")

        self.db = {}
        self.svar = {}

        log.msg("got args {}, kwargs {}".format(args,kwargs))

        # reap init variables meant only for us
        for i in ( 'engine', 'topic_base', 'dsn', 'authinfo', 'debug', ):
            if i in kwargs:
                if kwargs[i] is not None:
                    self.svar[i] = kwargs[i]
                del kwargs[i]

        log.msg("sending to super.init args {}, kwargs {}".format(args,kwargs))
        ApplicationSession.__init__(self, *args, **kwargs)

    def onConnect(self):
        log.msg("onConnect")
        auth_type = 'none'
        auth_user = 'anon'
        if 'authinfo' in self.svar:
            auth_type = self.svar['authinfo']['auth_type']
            auth_user = self.svar['authinfo']['auth_user']
        log.msg("onConnect with {} {}".format(auth_type, auth_user))
        self.join(self.config.realm, [six.u(auth_type)], six.u(auth_user))

    def onChallenge(self, challenge):
        log.msg("onChallenge - maynard")
        password = 'unknown'
        if 'authinfo' in self.svar:
            password = self.svar['authinfo']['auth_password']
        log.msg("onChallenge with password {}".format(password))
        if challenge.method == u'wampcra':
            if u'salt' in challenge.extra:
                key = auth.derive_key(password.encode('utf8'),
                    challenge.extra['salt'].encode('utf8'),
                    challenge.extra.get('iterations', None),
                    challenge.extra.get('keylen', None))
            else:
                key = password.encode('utf8')
            signature = auth.compute_wcs(key, challenge.extra['challenge'].encode('utf8'))
            return signature.decode('ascii')
        else:
            raise Exception("don't know how to compute challenge for authmethod {}".format(challenge.method))

    @inlineCallbacks
    def onJoin(self, details):
        log.msg("db:onJoin session attached {}".format(details))

        if 'engine' in self.svar and 'topic_base' in self.svar:
            if self.svar['engine'] == 'PG9_4' or self.svar['engine'] == 'PG':
                import db.postgres
                dbo = db.postgres.PG9_4(topic_base = self.svar['topic_base'], app_session = self, debug = self.svar['debug'])
            elif self.svar['engine'] == 'MYSQL14_14' or self.svar['engine'] == 'MYSQL':
                import db.mysql
                dbo = db.mysql.MYSQL14_14(topic_base = self.svar['topic_base'], app_session = self, debug = self.svar['debug'])
            elif self.svar['engine'] == 'SQLITE3_3_8_2' or self.svar['engine'] == 'SQLITE3' or self.svar['engine'] == 'SQLITE':
                import db.ausqlite3
                dbo = db.ausqlite3.SQLITE3_3_8_2(topic_base = self.svar['topic_base'], app_session = self, debug = self.svar['debug'])
            else:
                raise Exception("Unsupported dbtype {} ".format(self.svar['engine']))
        else:
            raise Exception("when instantiating this class DB you must provide engine=X and topic_base=Y")

        self.db = { 'instance': dbo }
        self.db['registration'] = {}

        r = types.RegisterOptions(details_arg = 'details')
        self.db['registration']['connect'] = yield self.register(dbo.connect, self.svar['topic_base']+'.connect',r)
        self.db['registration']['disconnect'] = yield self.register(dbo.disconnect, self.svar['topic_base']+'.disconnect',r)
        self.db['registration']['query'] = yield self.register(dbo.query, self.svar['topic_base']+'.query',r)
        self.db['registration']['operation'] = yield self.register(dbo.operation, self.svar['topic_base']+'.operation',r)
        self.db['registration']['watch'] = yield self.register(dbo.watch, self.svar['topic_base']+'.watch',r)

        if 'dsn' in self.svar:
            log.msg("db:onJoin connecting... {}".format(self.svar['dsn']))
            yield self.call(self.svar['topic_base'] + '.connect', self.svar['dsn'])
            log.msg("db:onJoin connecting established")

        log.msg("db bootstrap procedures registered")

    def onLeave(self, details):
        print("onLeave: {}").format(details)

        yield self.db['registration']['connect'].unregister()
        yield self.db['registration']['disconnect'].unregister()
        yield self.db['registration']['query'].unregister()
        yield self.db['registration']['operation'].unregister()
        yield self.db['registration']['watch'].unregister()

        del self.db

        self.disconnect()

        return

    def onDisconnect(self):
        print("onDisconnect:")
        reactor.stop()


if __name__ == '__main__':
    prog = os.path.basename(__file__)

    def_wsocket = 'ws://127.0.0.1:8080/ws'
    def_user = 'db'
    def_secret = 'dbsecret'
    def_realm = 'realm1'
    def_topic_base = 'com.db'

    p = argparse.ArgumentParser(description="db admin manager for autobahn")

    p.add_argument('-w', '--websocket', action='store', dest='wsocket', default=def_wsocket,
                        help='web socket '+def_wsocket)
    p.add_argument('-r', '--realm', action='store', dest='realm', default=def_realm,
                        help='connect to websocket using "realm" '+def_realm)
    p.add_argument('-v', '--verbose', action='store_true', dest='verbose',
            default=False, help='Verbose logging for debugging')
    p.add_argument('-u', '--user', action='store', dest='user', default=def_user,
                        help='connect to websocket as "user" '+def_user)
    p.add_argument('-s', '--secret', action='store', dest='password', default=def_secret,
                        help='users "secret" password')
    p.add_argument('-e', '--engine', action='store', dest='engine', default=None,
                        help='if specified, a database engine will be attached. Note engine is rooted on --topic')
    p.add_argument('-d', '--dsn', action='store', dest='dsn', default=None,
                        help='if specified the database in dsn will be connected and ready')
    p.add_argument('-t', '--topic', action='store', dest='topic_base', default=def_topic_base,
                        help='if you specify --dsn then you will need a topic to root it on, the default ' + def_topic_base + ' is fine.')

    args = p.parse_args()
    if args.verbose:
        log.startLogging(sys.stdout)

    component_config = types.ComponentConfig(realm=args.realm)
    ai = {
            'auth_type':'wampcra',
            'auth_user':args.user,
            'auth_password':args.password
            }
    mdb = DB(config=component_config,
            authinfo=ai,engine=args.engine,topic_base=args.topic_base,dsn=args.dsn, debug=args.verbose)

    runner = ApplicationRunner(args.wsocket, args.realm)
    runner.run(lambda _: mdb)
