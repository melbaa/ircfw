An extensible IRC framework built on top of ZeroMQ.

# Install
get python 3.4
pip install pyzmq
pip install lxml (or lxml-3.4.1.win32-py3.4.exe from http://www.lfd.uci.edu/~gohlke/pythonlibs/)
git clone github.com/melbaa/ircfw

# Usage
cd path/to/project
create a secrets.json with by following the example
python example_bot.py

# Plugins
see the examples in fw/plugins.
a main.py holds the entry point to a plugin (just a convention)
All plugins need unique triggers.

# About IRC
architecture http://www.irchelp.org/irchelp/rfc/rfc2810.txt
client protocol http://www.networksorcery.com/enp/rfc/rfc2812.txt

# Why make this
* IRC is a relatively simple text protocol, easy to debug
* have more than just a mental framework for a distributed system
* practice programming abstraction and refactoring
* mostly a proof of concept and for learning ZeroMQ aka. toy project

# Features
* main components communicating via ZeroMQ, meaning they can be started separately on different machines
* handle ssl and password protected servers and nicks
* plugin architecture
* multiple server support
* no busy loops

