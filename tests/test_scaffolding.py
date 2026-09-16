def test_package_is_importable():
    import ai_notifier

    assert ai_notifier.__version__ == "0.1.0"
