
import os, sys

sys.dont_write_bytecode = True
os.chdir(sys.path[0] or ".")
sys.path += ("irc", )

server     = 'irc.underworld.no'
port       = 9999
channels   = [('#IRCUFC', None)] # (chan, key)
use_ssl    = True

nickname = 'k43rw'
username = 'wrkslav'
realname = '** WE BOTTIN **'

master = "wr34k"

optkey= ","

DEBUG = True

if __name__ == '__main__':
    import irc
    irc.IrcBot(nickname, username, realname, server, port, use_ssl, channels, master, optkey, DEBUG).init()
