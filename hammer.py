#!/usr/bin/env python
# imports # {{{
import eventlet
from eventlet.green import zmq
from eventlet.hubs import use_hub
from eventlet.green.socket import error as socket_error
from eventlet.event import Event
import logging, argparse
# }}}

use_hub("zeromq")

# globals # {{{
logger = logging.getLogger("orbited_node")
ctx = zmq.Context()
publisher = ctx.socket(zmq.PUB)
publisher.bind("tcp://127.0.0.1:7777")
control = ctx.socket(zmq.PULL)
_id = long(0)
clients = {}
sessions = {}
users = {}
channels = {}
sockets = {}
# }}}

# get_next_id # {{{
def get_next_id():
    global _id
    _id += 1
    return str(_id)
# }}}

# send message functions # {{{
def send_message_to_all(app, messagetype, message):
    send_message_to_clients(clients.values(), app, messagetype, message)

def send_message_to_clients(clientids, app, messagetype, message):
    for client in clientids:
        if type(client) != dict:
            client = clients[client]
        client["socket"].send("%s:%s:%s\r\n" % (app, messagetype, message))

def send_message_to_client(clientid, app, messagetype, message):
    client = clients.get(clientid)
    if not client: return
    send_message_to_clients([client], app, messagetype, message)

def send_message_to_session(sessionid, app, messagetype, message):
    session = sessions.get(sessionid)
    if not session: return
    send_message_to_clients(session["clientids"], app, messagetype, message)

def send_message_to_user(userid, app, messagetype, message):
    user = users.get(userid)
    if not user: return
    for session in user["sessions"]:
        send_message_to_clients(session["clients"], app, messagetype, message)

def send_message_to_channel(channelid, app, messagetype, message):
    logger.warn(
        "send_message_to_channel: %s, %s, %s, %s" % (
            channelid, app, messagetype, message
        )
    )
    channel = channels.get(channelid)
    if not channel:
        logger.warn("send_message_to_channel: no channel")
        return
    send_message_to_clients(channel["clientids"], app, messagetype, message)

def send_message_to_app(socket, app, messagetype, message):
    logger.debug(
        "send_message_to_app: %s, %s, %s, %s" % (
            sockets.get(socket), app, messagetype, message
        )
    )
    client = sockets[socket]
    publisher.send(
        "%s:%s:node1:%s:%s:%s:%s" % (
            app, messagetype, client["clientid"], client["sessionid"],
            client.get("userid", ""), message
        )
    )
# }}}

# add_connection # {{{
def add_connection(socket, clientid, sessionid):
    logger.debug("add_connection: %s, %s, %s" % (socket, clientid, sessionid))
    assert socket not in sockets, "socket already there"
    assert clientid not in clients, "client already there"
    client = {
        "clientid": clientid, "sessionid": sessionid, "socket": socket,
        "channelids": set()
    }
    sockets[socket] = client
    clients[clientid] = client
    session = sessions.setdefault(
        sessionid, {"sessionid": sessionid, "userid": None, "clientids": set()}
    )
    session["clientids"].add(clientid)
    userid = session.get("userid")
    if userid:
        assert userid in users
        client["userid"] = userid
    logger.debug("add_connection: done")
# }}}

# remove_connection # {{{
def remove_connection(socket):
    logger.debug("remove_connection: %s" % socket)
    client = sockets.get(socket)
    if not client:
        logger.warn("remove_connection: socket not there")
        return
    clientid = client["clientid"]
    sessionid = client["sessionid"]
    session = sessions[sessionid]
    assert client.get("userid") == session.get("userid")
    session["clientids"].remove(clientid)
    del clients[clientid]
    del sockets[socket]

    if not session["clientids"]: 
        logger.info("remove_connection: session is empty, removing")
        del sessions[sessionid]
        userid = session.get("userid")
        user = users.get(userid)
        if user:
            user["sessionids"].remove(session)
            if not user["sessionids"]:
                # user has no sessions left, remove it
                del users[userid]

    for channelid in client.get("channelids", set()):
        channel = channels[channelid]
        channel["clientids"].remove(clientid)
        if not channel["clientids"]: del channels[channelid]
    logger.debug("remove_connection: done")
# }}}

# disconnect_connection # {{{
def disconnect_connection(clientid):
    logger.debug("disconnect_connection: %s" % clientid)
    client = clients.get(clientid)
    if not client: 
        logger.warn("disconnect_connection: no client")
        return
    remove_connection(client["socket"])
    client["socket"].close()
    logger.debug("disconnect_connection: done")
# }}}

# add_client_to_channel # {{{
def add_client_to_channel(clientid, channelid):
    client = clients[clientid]
    client["channelids"].add(channelid)
    channels.setdefault(
        channelid, {"channelid": channelid, "clientids": set()}
    )["clientids"].add(clientid)
# }}}

# remove_client_from_channel # {{{
def remove_client_from_channel(clientid, channelid):
    logger.debug("remove_client_from_channel: %s, %s" % (clientid, channelid))
    channel, client = channels.get(channelid), clients.get(clientid)
    if client: client["channelids"].remove(channelid)
    if channel and clientid in channel["clientids"]:
        channel["clientids"].remove(clientid)
    if channel and not channel["clientids"]:
        logger.warn("remove_client_from_channel: removing empty channel")
        del channels[channelid]
    logger.debug("remove_client_from_channel done")
# }}}

# add_user_to_session # {{{
def add_user_to_session(userid, sessionid):
    session = sessions.get(sessionid)
    if not session: return
    users.setdefault(
        userid, { "userid": userid, "sessions": set()}
    )["sessions"].add(session)
    session["userid"] = userid
    for client in session["clients"]:
        client["userid"] = userid
# }}}

# remove_user_from_session # {{{
def remove_user_from_session(userid, sessionid):
    session = sessions.get(sessionid)
    if not session: return
    assert session["userid"] == userid
    session["userid"] = None
    for client in session["clients"]:
        client["userid"] = None
    user = users[userid]
    user["sessions"].remove(session)
    if not user["sessions"]:
        del user[userid]
# }}}

def parse(msg): return msg.split(":", 2)

# reader # {{{
def consume_buffer(buf, sock):
    while True:
        if "\r\n" not in buf: return buf
        line, buf = buf.split("\r\n", 1)
        app, command, payload = parse(line)
        send_message_to_app(sock, app, command, payload)
    return ""

def reader(sock, event):
    with_exception = ""
    buf = ""
    while True:
        try:
            logger.info("sock members: %s", dir(sock))
            buf += sock.recv(2048)
        except socket_error, e:
            logger.exception(e)
            with_exception = str(e)
            break
        logger.info("read: %s" % buf)
        if not buf: break
        buf = consume_buffer(buf, sock)
    send_message_to_app(sock, "hammerlib", "client_gone", with_exception)
    remove_connection(sock)
    event.send("done")
# }}}

# error # {{{
def error(sock, msg):
    sock.send("hammerlib:error:%s\r\n" % msg)
    logger.info("hammerlib:error: %s" % msg)
    sock.close()
# }}}

# handler # {{{
def handler(sock, client):
    # socket opened
    # first message is either hammerlib:get_clientid:sessionid
    #                   or    hammerlib:have_clientid:sessionid:clientid
    app, command, payload = parse(sock.recv(2048)) # FIXME: what about framing?
    payload = payload.strip() # FIXME: dirty hack
    if app != "hammerlib": return error(sock, "no handshake")
    if command == "get_clientid":
        clientid, sessionid = get_next_id(), payload
        add_connection(sock, clientid, payload)
    elif command == "have_clientid":
        # assert the proper session for given clientid
        sessionid, clientid = payload.split(":")
        client = clients.get(clientid)
        if client:
            if client["sessionid"] != sessionid:
                return error(sock, "bad sessionid")
        else:
            add_connection(sock, clientid, sessionid)
    else:
        return error(sock, "bad handshake")

    send_message_to_client(clientid, "hammerlib", "connected", clientid)
    send_message_to_app(sock, "hammerlib", "client_connected", "")
    event = Event()
    eventlet.spawn_n(reader, sock, event)
    event.wait()
# }}}

# handler_ # {{{
def handler_(sock, client):
    logger.info("New connection: %s" % str(client))
    try:
        handler(sock, client)
    except Exception, e:
        logger.exception(e)
        return error(sock, e)
    logger.info("Connection closing gracefully: %s" % str(client))
# }}}

# handle_line # {{{
def handle_line(line):
    logger.debug("handle_line: %s" % line)
    if line.startswith("send_message_to_client"):
        _, clientid, app, messagetype, message = line.split(":", 4)
        send_message_to_client(clientid, app, messagetype, message)
    elif line.startswith("send_message_to_session"):
        _, sessionid, app, messagetype, message = line.split(":", 4)
        send_message_to_session(sessionid, app, messagetype, message)
    elif line.startswith("send_message_to_user"):
        _, userid, app, messagetype, message = line.split(":", 4)
        send_message_to_user(userid, app, messagetype, message)
    elif line.startswith("send_message_to_channel"):
        _, channelid, app, messagetype, message = line.split(":", 4)
        send_message_to_channel(channelid, app, messagetype, message)
    elif line.startswith("send_message_to_all"):
        _, app, messagetype, message = line.split(":", 3)
        send_message_to_all(app, messagetype, message)
    elif (
        line.startswith("disconnect_connection") or
        line.startswith("kick_client")
    ):
        _, clientid = line.split(":", 1)
        disconnect_connection(clientid)
    elif line.startswith("add_client_to_channel"):
        _, clientid, channelid = line.split(":", 2)
        add_client_to_channel(clientid, channelid)
    elif line.startswith("remove_client_from_channel"):
        _, clientid, channelid = line.split(":", 2)
        remove_client_from_channel(clientid, channelid)
    elif line.startswith("add_user_to_session"):
        _, userid, sessionid = line.split(":", 2)
        add_user_to_session(userid, sessionid)
    elif line.startswith("remove_user_from_session"):
        _, userid, sessionid = line.split(":", 2)
        remove_user_from_session(userid, sessionid)
    else:
        logger.warn("unknown command: %s" % line)
        return "unknown command"
    logger.debug("handle_line: done")
    return "ok"
# }}}

# zcommand_handler # {{{
def zcommand_handler():
    logger.debug("zcommand_handler")
    while True:
        line = control.recv(2048)
        try:
            handle_line(line)
        except Exception, e:
            logger.exception(e)
    logger.warn("zcommand_handler: done")
# }}}

def main():
    logger.info("Starting orbited_node")
    parser = argparse.ArgumentParser(
        description='HammerD Server'
    )
    parser.add_argument("--ip", default="127.0.0.1")
    parser.add_argument("--zmqport", default="7778")
    parser.add_argument("--tcpport", default="9999")
    arguments = parser.parse_args()

    control.bind("tcp://%s:%s" % (arguments.ip, arguments.zmqport))
    eventlet.spawn_n(zcommand_handler)
    eventlet.serve(
        eventlet.listen((arguments.ip, int(arguments.tcpport))), handler_
    )

def debug_main():
    logging.basicConfig(level=logging.DEBUG)
    main()

if __name__ == "__main__":
    debug_main()

