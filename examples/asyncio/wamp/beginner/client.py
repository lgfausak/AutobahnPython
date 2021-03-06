###############################################################################
##
##  Copyright (C) 2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

import sys

try:
   import asyncio
except ImportError:
   ## Trollius >= 0.3 was renamed
   import trollius as asyncio

from autobahn.asyncio import wamp, websocket


class MyFrontendComponent(wamp.ApplicationSession):
   """
   Application code goes here. This is an example component that calls
   a remote procedure on a WAMP peer, subscribes to a topic to receive
   events, and then stops the world after some events.
   """
   def onConnect(self):
      self.join(u"realm1")

   @asyncio.coroutine
   def onJoin(self, details):

      ## call a remote procedure
      ##
      try:
         now = yield from self.call(u'com.timeservice.now')
      except Exception as e:
         print("Error: {}".format(e))
      else:
         print("Current time from time service: {}".format(now))

      ## subscribe to a topic
      ##
      self.received = 0

      def on_event(i):
         print("Got event: {}".format(i))
         self.received += 1
         if self.received > 5:
            self.leave()

      sub = yield from self.subscribe(on_event, u'com.myapp.topic1')
      print("Subscribed with subscription ID {}".format(sub.id))

   def onLeave(self, details):
      self.disconnect()

   def onDisconnect(self):
      asyncio.get_event_loop().stop()


if __name__ == '__main__':

   ## 1) create a WAMP application session factory
   session_factory = wamp.ApplicationSessionFactory()
   session_factory.session = MyFrontendComponent

   ## 2) create a WAMP-over-WebSocket transport client factory
   transport_factory = websocket.WampWebSocketClientFactory(session_factory,
                                                            debug = False,
                                                            debug_wamp = False)

   ## 3) start the client
   loop = asyncio.get_event_loop()
   coro = loop.create_connection(transport_factory, '127.0.0.1', 8080)
   loop.run_until_complete(coro)

   ## 4) now enter the asyncio event loop
   loop.run_forever()
   loop.close()
