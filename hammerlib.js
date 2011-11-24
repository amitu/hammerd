window.hammerlib = function () {
    var remove = function(list,element) {
        for(var i=list.length; i>= 0; i--)
        {
            if(list[i]==element)
                list.splice(i,1);
        }
    }

    var HammerLib = {};
    var locals = {}

    locals.binds = {};
    locals.app_binds = {};
    locals.connection = undefined;
    locals.buffer = "";

    var parse_message = function(message) {
        var appname = message.substr(0, message.indexOf(":"));
        message = message.substr(appname.length + 1);
        var messagetype = message.substr(0, message.indexOf(":"));
        message = message.substr(messagetype.length + 1);
        return [appname, messagetype, message];
    }

    var fire_app_event = function(appname, messagetype, message) {
        var handlers = locals.app_binds[appname];
        if (handlers == undefined) return;
        for(i = handlers.length - 1; i >= 0; i--){
            handlers[i](messagetype, message);
        }
    }

    var fire_event = function(appname, messagetype, message) {
        var handlers = locals.binds[appname + ":" + messagetype];
        if (handlers == undefined) return;
        for(i = handlers.length - 1; i >= 0; i--){
            handlers[i](message);
        }
    }

    var fire = function(appname, messagetype, message) {
        fire_event(appname, messagetype, message);
        fire_app_event(appname, messagetype, message);
    }

    var readline_from_buffer = function(){
        var i = locals.buffer.indexOf("\r\n");
        if (i == -1) return "";
        var line = locals.buffer.substring(0, i);
        locals.buffer = locals.buffer.substring(i + 2, locals.buffer.length);
        return line;
    }

    var consume_buffer = function(){
        while(true) {
            var message = readline_from_buffer();
            if (message == "") return;
            var parsed = parse_message(message);
            try { parsed[2] = eval("(" + parsed[2] + ")"); }
            catch (e) { 
            	//console.log(message, e); 
            }
            fire(parsed[0], parsed[1], parsed[2]);
        }
    }

    /* public api */
    HammerLib.bind = function(appname, messagetype, handler){
        var key = appname + ":" + messagetype;
        var handlers = locals.binds[key];
        if (handlers == undefined) handlers = [];
        handlers[handlers.length] = handler;
        locals.binds[key] = handlers;
    }

    HammerLib.unbind = function(appname, messagetype, handler){
        var key = appname + ":" + messagetype;
        var handlers = locals.binds[key];
        if (handlers == undefined) return;
        remove(handlers, handler);
    }

    HammerLib.close = function() {
        locals.connection.close();
    }

    HammerLib.bind_app = function(appname, handler){
        var handlers = locals.app_binds[appname];
        if (handlers == undefined) handlers = [];
        handlers[handlers.length] = handler;
        locals.app_binds[appname] = handlers;
    }

    HammerLib.unbind_app = function(appname, handler){
        var handlers = locals.binds[appname];
        if (handlers == undefined) return;
        remove(handlers, handler);
    }


    HammerLib.send = function(appname, messagetype, message) {
        if (typeof message != "string") message = JSON.stringify(message);
        if (message.indexOf("\r\n") != 1) {
            message = message.replace(/\r\n/g, "\n");
        }
        locals.connection.send(appname + ":" + messagetype + ":" + message + "\r\n");
    }

    HammerLib.close = function() {
        locals.connection.close();
    }

    HammerLib.initialize = function(scheme, host, port, path, sessionid) {
        locals.connection = window.hammerlib_transport.get_websocket(
            scheme, host, port, path, sessionid
        );
        locals.connection.onopen = function(){
            fire("hammerlib", "opened", "");
        };
        locals.connection.onclose = function(code){
            fire("hammerlib", "closed", code);
        };
        locals.connection.onmessage = function(message) {
            locals.buffer += message;
            consume_buffer();
        };
        HammerLib.bind("hammerlib", "connected", function(data) {
            locals.connection.set_clientid(data);
        });
        locals.connection.open();
    }

    HammerLib.parse_message = parse_message;

    return HammerLib;
}();
