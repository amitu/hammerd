import hammerlib

def pong(request):
    print "ping", request
    request.send_message_to_client(
        {"text": request.payload.get("text", "").upper()+" recvd"}, "pong"
    )

def left(request):
    print request

def main():
    hammerlib.bind("hammerlib", "client_gone", left)
    hammerlib.bind("pingpong", "ping", pong)
    hammerlib.initialize(
        (("node1", "tcp://127.0.0.1:7777", "tcp://127.0.0.1:7778"),)
    )
    hammerlib.main_loop()

if __name__ == "__main__":
    main()
