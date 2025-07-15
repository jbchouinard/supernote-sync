from pydantic_settings import BaseSettings

from snsync.config import StrSet


class SomeConfig(BaseSettings):
    test_list_param: StrSet = "test1,test2,test3"


def test_strset_default():
    config = SomeConfig()
    assert config.test_list_param == {"test1", "test2", "test3"}


def test_strset_custom():
    config2 = SomeConfig(test_list_param="foo,bar")
    assert config2.test_list_param == {"foo", "bar"}
    assert isinstance(config2.test_list_param, frozenset)
