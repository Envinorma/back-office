from back_office.pages.edit_am.callbacks.save_callback import count_prefix_hashtags


def test_count_prefix_hashtags():
    assert count_prefix_hashtags('') == 0
    assert count_prefix_hashtags('###') == 3
    assert count_prefix_hashtags(' ###') == 0
    assert count_prefix_hashtags('###  ') == 3
