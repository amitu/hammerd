window.hammerlib_transport = function(){
    var locals = {};

    var HammerTCPSocket = function (host, port) {

        var conn;
        var opened = false;
        var ws = {}

        var close = function(){ conn.close(); }
        var send = function(msg){ conn.emit("browser", msg); };
        var open = function() {
            conn = io.connect('http://www.hammerdemo.com:8081');
            conn.on("connect", function() {
                conn.on("disconnect", function(){
                    ws.readyState = 2; /* CLOSED */
                    ws.onclose();
                });
                conn.on("server", function(msg) {
                    if (opened) ws.onmessage(msg.message);
                    else {
                        var parsed = hammerlib.parse_message(msg.message);
                        locals.clientid = parsed[2].replace(/\r\n/g, '');
                        opened = true;
                        ws.onopen();
                    }
                });
                ws.readyState = 1; /* OPEN */
                conn.emit(
                    "browser", (
                        "hammerlib" + ":" + "get_clientid" + ":" + 
                        locals.sessionid + "\r\n"
                    )
                );
            });
        }
        var close = function() {
            conn.close();
        }
        ws = {
            "send": send, "close": close, "readyState": 0 /* CONNECTING */,
            "open": open, "onopen": function() {}, "close": close,
            "onmessage": function(msg) {},
            "onclose": function (code) {}
        }
        return ws;
    };


    var get_websocket = function (scheme, host, port, path, sessionid) {
        locals.scheme = scheme;
        locals.host = host;
        locals.port = port;
        locals.path = path;

        locals.sessionid = sessionid;

        return HammerTCPSocket(host, port);
    };

    var transport = {};
    transport.name = "node.socket.io";
    transport.get_websocket = get_websocket;
    return transport;
}();
