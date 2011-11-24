window.hammerlib_transport = function(){
    var locals = {};

    var HammerTCPSocket = function (host, port) {

        var conn = new Orbited.TCPSocket();
        var opened = false;

        var close = function(){ conn.close(); }
        var send = function(msg){ conn.send(msg); };
        var open = function() {
            conn.open(host, port);
        }
        var close = function() {
            conn.close();
        }

        var ws = {
            "send": send, "close": close, "readyState": 0 /* CONNECTING */,
            "open": open, "onopen": function() {}, "close": close,
            "onmessage": function(msg) {},
            "onclose": function (code) {}
        }
        conn.onopen = function () { 
            ws.readyState = 1; /* OPEN */
            conn.send("hammerlib" + ":" + "get_clientid" + ":" + locals.sessionid + "\r\n")
        };
        conn.onread = function(msg) {
            if (opened) ws.onmessage(msg);
            else {
                var parsed = hammerlib.parse_message(msg);
                locals.clientid = parsed[2].replace(/\r\n/g, '');
                ws.onopen();
                Orbited.settings.POLL_INTERVAL = 2000;
                opened = true;
            }
        }
        conn.onclose = function(code) {
            ws.readyState = 2; /* CLOSED */
            ws.onclose(code);
        };
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
    transport.name = "orbited.TCPSocket";
    transport.get_websocket = get_websocket;
    return transport;
}();
