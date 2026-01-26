"""Unit tests for bitmap_manager operations."""

import pytest


def test_set_bit_first_bit():
	"""Test setting the first bit (index 0)."""
	from memora.services.progress_engine.bitmap_manager import set_bit

	bitmap = b'\x00'
	result = set_bit(bitmap, 0)
	assert result == b'\x01'


def test_set_bit_multiple_bits():
	"""Test setting multiple bits."""
	from memora.services.progress_engine.bitmap_manager import set_bit

	bitmap = b'\x00\x00'
	result = set_bit(bitmap, 0)
	result = set_bit(result, 1)
	result = set_bit(result, 8)
	assert result == b'\x03\x01'


def test_set_bit_same_bit():
	"""Test setting the same bit twice."""
	from memora.services.progress_engine.bitmap_manager import set_bit

	bitmap = b'\x00'
	result = set_bit(bitmap, 0)
	result = set_bit(result, 0)
	assert result == b'\x01'


def test_set_bit_expand_bytes():
	"""Test setting a bit that requires expanding the byte array."""
	from memora.services.progress_engine.bitmap_manager import set_bit

	bitmap = b'\x00'
	result = set_bit(bitmap, 15)
	assert len(result) == 2
	assert int.from_bytes(result, 'big') & (1 << 15)


def test_check_bit_set():
	"""Test checking a bit that is set."""
	from memora.services.progress_engine.bitmap_manager import check_bit

	bitmap = b'\x07'
	assert check_bit(bitmap, 0) is True
	assert check_bit(bitmap, 1) is True
	assert check_bit(bitmap, 2) is True


def test_check_bit_not_set():
	"""Test checking a bit that is not set."""
	from memora.services.progress_engine.bitmap_manager import check_bit

	bitmap = b'\x07'
	assert check_bit(bitmap, 3) is False
	assert check_bit(bitmap, 7) is False


def test_check_bit_empty_bitmap():
	"""Test checking a bit on an empty bitmap."""
	from memora.services.progress_engine.bitmap_manager import check_bit

	assert check_bit(b'', 0) is False


def test_check_bit_cross_byte_boundary():
	"""Test checking bits across byte boundaries."""
	from memora.services.progress_engine.bitmap_manager import check_bit, set_bit

	bitmap = b'\x00\x00'
	bitmap = set_bit(bitmap, 7)
	bitmap = set_bit(bitmap, 8)
	bitmap = set_bit(bitmap, 15)

	assert check_bit(bitmap, 7) is True
	assert check_bit(bitmap, 8) is True
	assert check_bit(bitmap, 15) is True
	assert check_bit(bitmap, 6) is False
	assert check_bit(bitmap, 9) is False


def test_bitmap_roundtrip():
	"""Test set and check operations work together."""
	from memora.services.progress_engine.bitmap_manager import set_bit, check_bit

	bitmap = b'\x00'
	for i in range(10):
		bitmap = set_bit(bitmap, i)

	for i in range(10):
		assert check_bit(bitmap, i) is True

	assert check_bit(bitmap, 10) is False


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
