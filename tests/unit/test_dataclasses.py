import pytest
from DataClasses.DataClasses import CreateShortUrlDC
from pydantic import ValidationError

def test_valid_alias():
    dto = CreateShortUrlDC(url="http://example.com", alias="abc_123")
    assert dto.alias == "abc_123"

def test_alias_too_long():
    with pytest.raises(ValidationError):
        CreateShortUrlDC(url="http://example.com", alias="toolooooooooong")

def test_alias_invalid_chars():
    with pytest.raises(ValidationError):
        CreateShortUrlDC(url="http://example.com", alias="bad!@#")