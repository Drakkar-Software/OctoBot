from octobot_poc import greet, add, fibonacci


def test_greet():
    assert greet("World") == "Hello, World!"
    assert greet("") == "Hello, !"
    assert greet("OctoBot") == "Hello, OctoBot!"


def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0


def test_fibonacci():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(2) == 1
    assert fibonacci(10) == 55
    assert fibonacci(20) == 6765
