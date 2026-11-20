from cap import within_cap


def test_under():
    assert within_cap(4) is True


def test_over():
    assert within_cap(6) is False


if __name__ == "__main__":
    test_under()
    test_over()
    print("2 passed")
