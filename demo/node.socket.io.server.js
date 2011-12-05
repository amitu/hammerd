var app = require('http').createServer(handler)
  , io = require('socket.io').listen(app)
  , fs = require('fs')
  , net = require('net')

app.listen(8081);

function handler (req, res) {
    fs.readFile(__dirname + '/index.html',
    function (err, data) {
        if (err) {
            res.writeHead(500);
            return res.end('Error loading index.html');
        }

        res.writeHead(200);
        res.end(data);
    });
}

io.sockets.on('connection', function (socket) {
    var client = net.connect(9999);
    client.on("data", function(data) {
        socket.emit('server', { message: data.toString() });
    });
    socket.on('browser', function (data) {
        client.write(data.toString());
    });
});

