import queue

test_dict = {
    "status": True,
    "msg": "Test message",
    "data": [1, 2, 3]
}

test_queue = queue.Queue()
test_queue.put(test_dict)

test_dict["msg"] = "Updated test message"

test_queue.put(test_dict)

print(test_queue.get())
print(test_queue.get())