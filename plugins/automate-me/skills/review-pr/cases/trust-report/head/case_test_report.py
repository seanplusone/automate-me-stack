from report import accept


def test_trusts_a_pass():
    assert accept({"passed": True, "cases": [{"name": "a", "ok": True}]}) is True


def test_rejects_a_failure():
    assert accept({"passed": False, "cases": [{"name": "a", "ok": False}]}) is False


if __name__ == "__main__":
    test_trusts_a_pass()
    test_rejects_a_failure()
    print("2 passed")
