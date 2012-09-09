# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

# system imports
import time, sys

#beer imports
import urllib2
import json
import random
import unicodedata

def beerquery():
    baileysurl = 'http://ec2-50-112-236-55.us-west-2.compute.amazonaws.com/api/baileys'
    f = urllib2.urlopen(baileysurl)
    response = f.read()
    obs = json.loads(response)
    return obs['data']

def beerlist():
  beerlist = []
  for i in beerquery().iteritems():
      beerlist.append(str(i[1]['beer']))
  return beerlist

def beerinfo(beer):
  beerinfo = {}
  for i in beerquery().iteritems():
    if i[1]['beer'].lower() == beer.lower():
       beerinfo = i[1]
  return beerinfo

def beerinfo_format(info):
  print info
  msg = info['beer']
  msg += ", Fill = {:.2%}".format(float(info['fill']))
  msg += ", Style = {0}".format(info['style'])
  msg += ", Prices = {0}".format(", ".join(info['prices']))
  msg = str(msg)
  return msg



class MessageLogger:
    """
    An independent logger class (because separation of application
    and protocol logic is a good thing).
    """
    def __init__(self, file):
        self.file = file

    def log(self, message):
        """Write a message to the file."""
        timestamp = time.strftime("[%H:%M:%S]", time.localtime(time.time()))
        self.file.write('%s %s\n' % (timestamp, message))
        self.file.flush()

    def close(self):
        self.file.close()


class BeerBot(irc.IRCClient):
    """A logging IRC bot."""
    """That also does beer things."""

    nickname = "beerbot"

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.logger = MessageLogger(open(self.factory.filename, "a"))
        self.logger.log("[connected at %s]" %
                        time.asctime(time.localtime(time.time())))

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.logger.log("[disconnected at %s]" %
                        time.asctime(time.localtime(time.time())))
        self.logger.close()


    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log("[I have joined %s]" % channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        self.logger.log("<%s> %s" % (user, msg))

        # Check to see if they're sending me a private message
        if channel == self.nickname:
            msg = "It isn't nice to whisper!  Play nice with the group."
            self.msg(user, msg)
            return

        # Otherwise check to see if it is a message directed at me
        if msg.startswith(self.nickname + ":"):
            msg = "%s: I am a Beer bot, see {help}" % user
            self.msg(channel, msg)
            self.logger.log("<%s> %s" % (self.nickname, msg))

        # dat help
        if msg.startswith("{help"):
            msg = "{beerlist}, {beer} [beername]"
            self.msg(channel, msg)
            self.logger.log("<%s> %s" % (self.nickname, msg))
            return

        #  list beers
        if msg.startswith("{beerlist"):
            beerkind = " ".join(msg.split()[1:])
            #bq = 'beerquerry for beer %s' % beerkind
            bq = ", ".join(beerlist())
            self.msg(channel, bq)
            self.logger.log("<%s> %s" % (user, msg))
            self.logger.log("<%s> %s" % (channel, bq))

        # output random beer
        if msg.startswith("{random"):
            self.logger.log("<%s> %s" % (user, msg))
            beerkind = random.choice(beerlist())
            info = beerinfo(beerkind)
            msg = beerinfo_format(info)
            self.msg(channel, msg)
            self.logger.log("<%s> %s" % (channel, msg))

        # output info on a beer
        if msg.startswith("{beer"):
            self.logger.log("<%s> %s" % (user, msg))
            beerkind = " ".join(msg.split()[1:])
            info = beerinfo(beerkind)
            msg = beerinfo_format(info)
            self.msg(channel, msg)
            self.logger.log("<%s> %s" % (channel, msg))
            self.logger.log("<%s> %s" % (user, msg))

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.logger.log("* %s %s" % (user, msg))

    # irc callbacks

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        self.logger.log("%s is now known as %s" % (old_nick, new_nick))


    # For fun, override the method that determines how a nickname is changed on
    # collisions. The default method appends an underscore.
    def alterCollidedNick(self, nickname):
        """
        Generate an altered version of a nickname that caused a collision in an
        effort to create an unused related name for subsequent registration.
        """
        return nickname + '^'



class BeerBotFactory(protocol.ClientFactory):
    """A factory for BeerBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, channel, filename):
        self.channel = channel
        self.filename = filename

    def buildProtocol(self, addr):
        p = BeerBot()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()


if __name__ == '__main__':
    # initialize logging
    log.startLogging(sys.stdout)

    # create factory protocol and application
    channel ='#beer'
    logfile = 'beerlog'
    f = BeerBotFactory(channel, logfile)

    # connect factory to this host and port
    reactor.connectTCP("irc.cat.pdx.edu", 6667, f)

    # run bot
    reactor.run()
