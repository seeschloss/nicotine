# -*- coding: utf-8 -*-

from pynicotine.gtkgui.pluginsystem import BasePlugin

class Plugin(BasePlugin):
    __name__ = "Anti-SHOUT"
    __version__ = "2008-07-05r00"
    __MAXSCORE__ = 0.6
    __MINLENGTH__ = 5
    def IncomingPrivateChatEvent(self, nick, line):
        return (nick, self.antishout(line))
    def IncomingPublicChatEvent(self, room, nick, line):
        return (room, nick, self.antishout(line))
    def antishout(self, line):
        lowers = len([x for x in line if x.islower()])
        uppers = len([x for x in line if x.isupper()])
        score = -1
        if (lowers > 0):
            score = uppers/float(lowers)
        if len(line) > self.__MINLENGTH__ and (score == -1 or score > self.__MAXSCORE__):
            line = '. '.join([x.capitalize() for x in line.split('. ')]) + " (as)"
        return line
