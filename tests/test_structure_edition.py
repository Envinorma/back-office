from back_office.pages.edit_am_new.callbacks.save_callback import _count_prefix_hashtags


def test_count_prefix_hashtags():
    assert _count_prefix_hashtags('') == 0
    assert _count_prefix_hashtags('###') == 3
    assert _count_prefix_hashtags(' ###') == 0
    assert _count_prefix_hashtags('###  ') == 3
