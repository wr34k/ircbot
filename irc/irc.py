#!/usr/bin/python3

import sys, socket, ssl, time, os, re, select

sys.dont_write_bytecode = True
os.chdir(sys.path[0] or ".")
sys.path += ("..", )

import ircEvents

from log import Colors, Log
from mircformat import MIRCFormat
from ircCommands import IrcCommands


class IrcBot(object):

    def __init__(self, nickname, username, realname, server, port, use_ssl, channels, master, optkey, DEBUG):
        self.sock           = None
        self.ep             = None

        self.last_cmd       = {}
        self.flood_flag     = {}
        self.flood_count    = {}
        self.timeouts       = {}
        self.ops            = {}

        self.mirc           = MIRCFormat()
        self.log            = Log(DEBUG)
        self.cmds           = IrcCommands(self)

        self.server         = server
        self.port           = port
        self._ssl           = use_ssl

        self.nick           = nickname
        self.user           = username
        self.real           = realname

        self.master         = master

        self.optkey         = optkey

        self.channels = channels

        self.recvQueue = self.sendQueue = []

        self.partialLine = ''

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(0)
        try:
            self.sock.connect((self.server, self.port))
        except BlockingIOError:
            pass
        socketfd = self.sock.fileno()
        self.ep = select.epoll()
        self.ep.register(self.sock.fileno(), select.EPOLLIN | select.EPOLLOUT)
        ready = False
        while not ready:
            events = self.ep.poll(1)
            for _,evt in events:
                if evt & select.EPOLLOUT:
                    ready = True
                    break

        if self._ssl:
            self.sock = ssl.wrap_socket(self.sock, do_handshake_on_connect=False)
            ready = False
            while not ready:
                events = self.ep.poll(1)
                for _,evt in events:
                    if evt & select.EPOLLOUT:
                        try:
                            self.sock.do_handshake()
                            ready = True
                        except ssl.SSLWantReadError:
                            pass

    def init(self):
        self.connect()
        self.register()
        self.run()


    def run(self):
        while True:
            events = self.ep.poll(1)
            for _,evt in events:
                if evt & select.EPOLLIN:
                    self._recv()
                elif evt & select.EPOLLOUT and len(self.sendQueue) > 0:
                    self._send()

            self.handle_events()

    def register(self):
        self.queue("USER {} 0 * :{}".format(self.user, self.real))
        self.queue("NICK {}".format(self.nick))

    def updateNick(self):
        self.queue("NICK {}".format(self.nick))

    def _send(self):
        while self.sendQueue:
            msg = self.sendQueue[0]
            self.log.info(">> {}".format(msg.replace("\r\n", "")))
            datasent = self.sock.send(msg.encode())
            if datasent < len(msg):
                self.sendQueue[0] = msg[datasent:]
            else:
                del self.sendQueue[0]

    def _recv(self):
        lines = []
        while True:
            try:
                newLines = self.sock.recv(512)
            except BlockingIOError:
                self.recvQueue = lines
                return
            except ssl.SSLWantReadError:
                self.recvQueue = lines
                return
            if not newLines:
                lines += [None]
                break
            elif len(newLines) == 0:
                break
            else:
                newLines = str(newLines, 'utf-8', 'ignore')
                if newLines[-2:] == "\r\n":
                    msgs = (self.partialLine + newLines).split("\r\n")[:-1]
                    self.partialLine = ""
                else:
                    msgs = (self.partialLine + newLines).split("\r\n")
                    if len(msgs) > 1:
                        self.partialLine = msgs[-1]
                        msgs = msgs[:-1]
                lines += msgs

        self.recvQueue = lines

    def handle_events(self):
        while self.recvQueue:
            data = self.recvQueue[0]
            self.log.info("<< {}".format(data))
            line = data.split(" ")
            if line[0][1:] == 'ING':
                ircEvents.eventPING(self, line)
            else:
                try:
                    if hasattr(ircEvents, "event{}".format(line[1].upper())):
                        getattr(ircEvents, "event{}".format(line[1].upper()))(self, line)
                except Exception as e:
                    self.log.error("Error in getattr()", e)

            del self.recvQueue[0]

    def join(self, chan, key=None):
        self.queue("JOIN {} {}".format(chan, key)) if key else self.queue("JOIN {}".format(chan))


    def queue(self, msg):
        msg = msg.replace("\r", "")
        msg = msg.replace("\n", "")
        if len(msg) > (512 - len("\r\n")):
            for i in range(0, len(msg), 512 - len("\r\n")):
                m = msg[i:512 - len("\r\n")]
                m = m + "\r\n"
                self.sendQueue += [m]
        else:
            msg = msg + "\r\n"
            self.sendQueue += [msg]

    def isAdmin(self, ident):
        ret = False
        for line in [line.strip() for line in open('assets/admins', 'r').readlines() if line]:
            if re.compile(line.replace('*', '.*')).search(ident):
                ret = True
        return ret

    def isOp(self, ident):
        ret = False
        for line in [line.strip() for line in open('assets/ops', 'r').readlines() if line]:
            if re.compile(line.replace('*', '.*')).search(ident):
                ret = True
        return ret

    def isVoice(self, ident):
        ret = False
        for line in [line.strip() for line in open('assets/voices', 'r').readlines() if line]:
            if re.compile(line.replace('*', '.*')).search(ident):
                ret = True
        return ret


    def privmsg(self, chan, msg):
        if chan not in self.timeouts:
            self.timeouts[chan] = {'last_cmd': time.time(), 'burst': 0, 'timeout': 0}
        self.queue("PRIVMSG {} :{}".format(chan, msg))
        time.sleep(self.timeouts[chan]['timeout'])
        self.editTimeouts(chan)



    def editTimeouts(self, chan):
        if (time.time() - self.timeouts[chan]['last_cmd']) < 3:
            self.timeouts[chan]['burst'] += 1
        else:
            self.timeouts[chan]['burst'] = 0

        if self.timeouts[chan]['burst'] > 3:
            self.timeouts[chan]['timeout'] += 0.075
        else:
            self.timeouts[chan]['timeout'] = 0

        if self.timeouts[chan]['timeout'] > 0.4:
            self.timeouts[chan]['timeout'] = 0.4

        self.timeouts[chan]['last_cmd'] = time.time()


    def action(self, chan, msg):
        self.privmsg(chan, "\x01ACTION {}\x01".format(msg))
