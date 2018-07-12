#!/usr/bin/env python3

import time

def eventPING(IRC, line):
    IRC.queue("PONG {}".format(line[1]))

def event001(IRC, line):
    for c,k in IRC.channels:
        IRC.join(c, k)

def event433(IRC, line):
    IRC.nick += "_"
    IRC.updateNick()

def eventJOIN(IRC, line):
    IRC.log.info("{} JOIN to {}".format(line[0], line[2][1:]))
    chan = line[2][1:]
    if chan not in IRC.ops:
        IRC.ops[chan] = False
    if IRC.ops[chan]:
        if IRC.isOp(line[0][1:]):
            nick = line[0][1:].split("@")[0].split("!")[0]
            IRC.raw("MODE {} +o {}".format(chan, nick))
        if IRC.isVoice(line[0][1:]):
            nick = line[0][1:].split("@")[0].split("!")[0]
            IRC.raw("MODE {} +v {}".format(chan, nick))

def eventPART(IRC, line):
    IRC.log.info("{} PART from {}".format(line[0], line[2]))

def eventKICK(IRC, line):
    if line[3] == IRC.nick:
        IRC.log.warn("Got kicked from {} !".format(line[2]))
        chan = line[2]
        for c,k in IRC.channels:
            if chan == c:
                IRC.join(c, k)

def eventQUIT(IRC, line):
    if line[0][1:].split("@")[0].split("!")[0] == IRC.nick:
        IRC.log.warn("quit ! Reconnecting in 15 seconds..")
        time.sleep(15)
        IRC.init()

def eventINVITE(IRC, line):
    IRC.log.info("{} invited the bot to {}".format(line[0][1:].split("!")[0], line[3][1:]))

def eventMODE(IRC, line):
    modeNicks = line[4:]
    for i in range(len(modeNicks)):
        if IRC.nick == modeNicks[i]:
            idx=-1
            for j in range(len(line[3])):
                if line[3][j] not in ("+","-"):
                    idx+=1
                else:
                    last_mode = line[3][j]
                if idx == i:
                    if line[3][j] == 'o':
                        if last_mode == '+':
                            IRC.log.info("GOT OPS")
                            IRC.ops[line[2]] = True
                        else:
                            IRC.log.info("NO MOAR OPS")
                            IRC.ops[line[2]] = False

def eventPRIVMSG(IRC, line):
    nick,user   = line[0][1:].split("@")[0].split("!")
    user        = user[1:] if user[0] == '~' else user
    host        = line[0].split("@")[1]
    try:
        IRC.cmds.handle_msg(line[2], IRC.isAdmin(line[0][1:]), nick, user, host, ' '.join(line[3:])[1:])
    except:
        pass
