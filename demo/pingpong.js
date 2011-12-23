$.fn.on_enter = function (callback) {
    var ENTER_KEY = 13;
    return this.keypress(function (e){
        var key = e.charCode || e.keyCode || 0;
        if (key != ENTER_KEY) return;
        var value = $(this).val();
        if (value === "") return;

        if (!callback(value)) $(this).val("");
        return false;
    });
}

$(function(){
    var connected = false;

    hammerlib.bind("hammerlib", "opened", function(data) {
        connected = true;
        $("#status").text("connected");
    });

    hammerlib.bind("pingpong", "pong", function(data) {
        $("#thediv").text(data.text);
    });

    $('input').focus().on_enter(function(msg){
        if(!connected) {
            $("#status").text("not connected yet");
        }
        hammerlib.send("pingpong", "ping", { text: msg });
    });

    hammerlib.initialize("HNode", "localhost", 9999, "", "user_anon");
});
