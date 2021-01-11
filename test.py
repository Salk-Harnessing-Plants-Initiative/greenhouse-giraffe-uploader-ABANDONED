import time
import threading

def hello():
    print("hello, world")



  # after 30 seconds, "hello, world" will be printed
time.sleep(5)
t.cancel()
t.cancel()
t.cancel()


while True:
	
	t.start()



lock = threading.Lock()

while True:
	with lock:
		t = threading.Timer(3.0, hello)
		t.start()
	t.join()
