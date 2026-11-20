from score_review import passes


def test_names_a_bug():
    assert passes("bug at line 3") is True


if __name__ == "__main__":
    test_names_a_bug()
    print("1 passed")
