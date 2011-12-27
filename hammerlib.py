# imports and globals # {{{
import logging, Queue, threading, json, zmq
from amitu import zutils

logger = logging.getLogger("hammerlib")
nodes = {}
hammer = None
binds = {}
app_binds = {}
sender = None
# }}}

# get_nodes # {{{
def get_nodes(): 
    ns = set()
    for (pub, ctrl) in nodes.values():
        ns.add(pub)
    return list(ns)
# }}}

# public API: # {{{
def add_node(nodeid, pub, ctrl):
    nodes[nodeid] = [pub, ctrl]

# initialize # {{{
def initialize(more_nodes=tuple()):
    global hammer, sender

    if hammer: return

    for nodeid, pub, ctrl in more_nodes:
        add_node(nodeid, pub, ctrl)

    hammer = Hammer(get_nodes(), get_subscriptions())
    sender = Sender()
# }}}

# send message helpers # {{{
def send_message_to_all(app, command, payload):
    for nodeid in nodes:
        sender.send(
            nodeid, "send_message_to_all:%s:%s:%s" % (
                app, command, json.dumps(payload)
            )
        )

def send_message_to_channel(channelid, app, command, payload):
    for nodeid in nodes:
        sender.send(
            nodeid, "send_message_to_channel:%s:%s:%s:%s" % (
                channelid, app, command, json.dumps(payload)
            )
        )

def send_message_to_client(clientid, nodeid, app, command, payload):
    sender.send(
        nodeid, "send_message_to_client:%s:%s:%s:%s" % (
            clientid, app, command, json.dumps(payload)
        )
    )

def send_message_to_session(sessionid, app, command, payload):
    for nodeid in nodes:
        sender.send(
            nodeid, "send_message_to_session:%s:%s:%s:%s" % (
                sessionid, app, command, json.dumps(payload)
            )
        )

def send_message_to_user(userid, app, command, payload):
    for nodeid in nodes:
        sender.send(
            nodeid, "send_message_to_user:%s:%s:%s:%s" % (
                userid, app, command, json.dumps(payload)
            )
        )
# }}}

# add/remove client from channel # {{{
def add_client_to_channel(nodeid, clientid, channelid):
    sender.send(
        nodeid, "add_client_to_channel:%s:%s" % (clientid, channelid)
    )

def remove_client_from_channel(nodeid, clientid, channelid):
    sender.send(
        nodeid, "remove_client_from_channel:%s:%s" % (clientid, channelid)
    )
# }}}

# add/remove user from session # {{{
def add_user_to_session(userid, sessionid):
    for nodeid in nodes:
        sender.send(
            nodeid, "add_user_to_session:%s:%s" % (userid, sessionid)
        )

def remove_user_from_session(userid, sessionid):
    for nodeid in nodes:
        sender.send(
            nodeid, "remove_user_from_session:%s:%s" % (userid, sessionid)
        )
# }}}

def main_loop():
    hammer.join()

def bind(app, command, cb):
    assert hammer is None, "cant bind after initialization"
    binds.setdefault("%s:%s" % (app, command), []).append(cb)

def bind_app(app, cb):
    assert hammer is None, "cant bind after initialization"
    app_binds.setdefault(app, []).append(cb)

# Request # {{{
class Request(dict):
    def __init__(self, line):
        logger.debug("Request.__init__: %s" % line)
        self.__dict__ = self
        (
            app, message_type, nodeid, clientid, sessionid, userid, payload
        ) = line.split(":", 6)
        self.nodeid = nodeid
        self.app = app
        self.message_type = message_type
        self.clientid = clientid
        self.sessionid = sessionid
        self.userid = userid
        try:
            self.payload = json.loads(payload)
        except ValueError:
            self.payload = payload
        logger.debug("Request.__init__ done")

    def send_message_to_client(self, message, message_type=None, app=None):
        if not app: app = self.app
        if not message_type: message_type = self.message_type
        send_message_to_client(
            self.clientid, self.nodeid, app, message_type, message
        )

    def add_client_to_channel(self, channelid):
        add_client_to_channel(self.nodeid, self.clientid, channelid)

    def remove_client_from_channel(self, channelid):
        remove_client_from_channel(self.nodeid, self.clientid, channelid)
# }}}
# }}}

# get_subscriptions # {{{
def get_subscriptions():
    subs = set(binds.keys()) 
    # chat.join, chat.leave, chat.create_room, hammerlib.client_gone
    app_subs = set(app_binds.keys())
    # chat, login
    items_to_remove = []
    for app in app_subs:
        for sub in subs:
            if sub.startswith(app): items_to_remove.append(sub)
    for item in set(items_to_remove):
        subs.remove(item)
    # chat, login, hammerlib.client_gone
    print list(app_subs.union(subs))
    return list(app_subs.union(subs))
# }}}

# Sender # {{{
class Sender(threading.Thread):
    def __init__(self):
        super(Sender, self).__init__()
        self.q = Queue.Queue()
        self.daemon = True
        self.start()

    def send(self, node, msg):
        self.q.put((node, msg))

    def run(self):
        # open sockets
        for v in nodes.values():
            s = zutils.CONTEXT.socket(zmq.PUSH)
            s.connect(v[1]);
            v.append(s)
        while True:
            node, msg = self.q.get()
            #print "sending to node", node, msg
            nodes[node][2].send(msg.encode("utf8"))
            self.q.task_done()
# }}}

# Hammer # {{{
class Hammer(zutils.ZSubscriber):
    def process(self, line):
        logger.debug("process: %s" % line)
        request = Request(line)
        logger.debug("Request: %s" % request)
        print request
        for cb in binds.get("%(app)s:%(message_type)s" % request, []):
            cb(request)
        for cb in app_binds.get(request["app"], []):
            cb(request)
# }}}

# utility apps # {{{
fwd_logger = logging.getLogger("fwd")
def fwd(request):
    fwd_logger.debug("fwd: %s" % request)
    if not "clientid" in request.payload:
        fwd_logger.info("fwd: %s" % "clientid not in request.payload")
        return
    cid = request.payload["clientid"]
    request.payload["clientid"] = request.clientid
    send_message_to_client(
        cid, "node1", "fwd", request.message_type, request.payload
    )

def activate_fwd_app():
    bind_app("fwd", fwd)

ping_logger = logging.getLogger("pingpong")

def pong(request):
    ping_logger.debug("pong: %s" % request)
    request.send_message_to_client(
        {"text": request.payload.get("text", "").upper()+" recvd"}, "pong"
    )

def activate_pingpong_app():
    bind("pingpong", "ping", pong)
# }}}

# TODO:
# * bind_to decorator
# * bind_to_app decorator

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='HammerLib App'
    )
    parser.add_argument("--node", default="node1")
    parser.add_argument("--pub", default="tcp://127.0.0.1:7777")
    parser.add_argument("--ctrl", default="tcp://127.0.0.1:7778")
    parser.add_argument("--fwd", default=False, action="store_true")
    parser.add_argument("--pingpong", default=False, action="store_true")

    args = parser.parse_args()

    if args.fwd: activate_fwd_app()
    if args.pingpong: activate_pingpong_app()

    initialize(((args.node, args.pub, args.ctrl),))
    main_loop()

if __name__ == "__main__":
    main()
