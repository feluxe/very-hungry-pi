from ..logging import logger as log, fix_str_len


def test_fixed_str_len():
    """"""
    # Test if output string looks the right way.
    result = fix_str_len('This is just an example sentence.', 20, '.')
    should = 'This is [...]ntence.'
    assert result == should
    # Test string len if input is shorter than desired len.
    assert len(fix_str_len('meow!', 10)) == 10
    # Test string len if input is longer than desired len.
    assert len(fix_str_len('Hello, I am a dog.', 3)) == 3

