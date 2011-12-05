$.fn.on_enter = function (callback) {
    var ENTER_KEY = 13;
    return this.keypress(function (e){
        var key = e.charCode || e.keyCode || 0;
        if (key != ENTER_KEY) return;
        var value = $(this).val();
        if (value == "") return;

        if (!callback(value)) $(this).val("");
        return false;
    });
}

$(function(){
    var socket = io.connect('http://www.hammerdemo.com:8081', function(){
        console.log("connected");
    });
    socket.on('news', function (data) {
        console.log(data);
        socket.emit('my other event', { my: 'data' });
    });
});
