"""
Local Storage Manager for CDN Export.

Handles atomic file writes, versioning, and disk space management.
"""

import frappe
import json
import os
import shutil
import tempfile
import hashlib


def get_local_base_path() -> str:
	"""
	Get the absolute path to the memora_content directory.

	Returns:
		str: e.g., /home/frappe/frappe-bench/sites/mysite/public/memora_content
	"""
	current_site = frappe.local.site if hasattr(frappe, 'local') and hasattr(frappe.local, 'site') else None
	
	if not current_site:
		frappe.throw("Site not found in context")
	
	bench_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	while os.path.basename(bench_path) != 'apps':
		bench_path = os.path.dirname(bench_path)
	
	bench_path = os.path.dirname(bench_path)
	public_path = os.path.join(bench_path, 'sites', str(current_site), 'public')
	return os.path.join(public_path, 'memora_content')


def check_disk_space(threshold_percent: float = 10.0) -> tuple[bool, float]:
	"""
	Check if disk has sufficient space.

	Parameters:
		threshold_percent: Minimum free disk percentage required

	Returns:
		tuple[bool, float]: (is_ok, free_percent) - is_ok is False if below threshold
	"""
	base_path = get_local_base_path()
	usage = shutil.disk_usage(base_path)
	free_percent = (usage.free / usage.total) * 100
	return free_percent >= threshold_percent, free_percent


def write_content_file(path: str, data: dict, require_min_disk_percent: float = 10.0) -> tuple[bool, str | None]:
	"""
	Write JSON content to local storage with atomic writes and version retention.

	Parameters:
		path (str): Relative path from memora_content root (e.g., "plans/PLAN-001/manifest.json")
		data (dict): JSON data to write
		require_min_disk_percent (float): Minimum disk space percentage required (default 10.0)

	Returns:
		tuple[bool, str | None]: (success, error_message) - error is None on success

	Write Process:
	1. Check disk space
	2. If file exists, move to .prev (delete existing .prev first)
	3. Write to temp file (.tmp.{uuid})
	4. Atomic rename to final path
	"""
	try:
		base_path = get_local_base_path()
		full_path = os.path.join(base_path, path)
		dir_path = os.path.dirname(full_path)

		is_ok, free_percent = check_disk_space(threshold_percent=require_min_disk_percent)
		if not is_ok:
			frappe.log_error(
				f"Insufficient disk space for {path}: {free_percent:.1f}% free, need {require_min_disk_percent}%",
				"Local Storage Write Failed"
			)
			return False, f"Insufficient disk space: {free_percent:.1f}% free"

		os.makedirs(dir_path, exist_ok=True)

		if os.path.exists(full_path):
			prev_path = full_path + ".prev"
			if os.path.exists(prev_path):
				os.unlink(prev_path)
			os.rename(full_path, prev_path)

		fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix='.tmp')
		try:
			with os.fdopen(fd, 'w', encoding='utf-8') as f:
				json.dump(data, f, ensure_ascii=False, indent=2)
			os.replace(tmp_path, full_path)
		except:
			if os.path.exists(tmp_path):
				os.unlink(tmp_path)
			raise

		return True, None

	except Exception as e:
		error_msg = f"Failed to write content file {path}: {str(e)}"
		frappe.log_error(error_msg, "Local Storage Write Failed")
		return False, error_msg


def file_exists(path: str) -> bool:
	"""
	Check if a file exists in local storage.

	Parameters:
		path (str): Relative path from memora_content root

	Returns:
		bool: True if file exists, False otherwise
	"""
	try:
		base_path = get_local_base_path()
		full_path = os.path.join(base_path, path)
		return os.path.isfile(full_path)
	except Exception:
		return False


def get_file_hash(path: str) -> str:
	"""
	Calculate MD5 hash of a file in local storage.

	Parameters:
		path (str): Relative path from memora_content root

	Returns:
		str: MD5 hash as hexadecimal string

	Raises:
		FileNotFoundError: If file doesn't exist
	"""
	base_path = get_local_base_path()
	full_path = os.path.join(base_path, path)

	md5 = hashlib.md5()
	with open(full_path, 'rb') as f:
		for chunk in iter(lambda: f.read(8192), b''):
			md5.update(chunk)
	return md5.hexdigest()


def delete_content_file(path: str) -> tuple[bool, str | None]:
	"""
	Delete a file from local storage, including its .prev version.

	Parameters:
		path (str): Relative path from memora_content root (e.g., "units/UNIT-001.json")

	Returns:
		tuple[bool, str | None]: (success, error_message) - error is None on success

	Deletion Process:
	1. Delete .prev file if exists
	2. Delete the main file
	3. Remove empty parent directories
	"""
	try:
		base_path = get_local_base_path()
		full_path = os.path.join(base_path, path)
		prev_path = full_path + ".prev"

		if os.path.exists(prev_path):
			os.unlink(prev_path)

		if os.path.exists(full_path):
			os.unlink(full_path)

		_dir_path = os.path.dirname(full_path)
		while _dir_path != base_path and os.path.exists(_dir_path):
			if not os.listdir(_dir_path):
				os.rmdir(_dir_path)
				_dir_path = os.path.dirname(_dir_path)
			else:
				break

		return True, None

	except Exception as e:
		error_msg = f"Failed to delete content file {path}: {str(e)}"
		frappe.log_error(error_msg, "Local Storage Delete Failed")
		return False, error_msg


def delete_content_directory(path: str) -> tuple[bool, str | None]:
	"""
	Delete a directory and all its contents from local storage.

	Parameters:
		path (str): Relative path from memora_content root (e.g., "plans/PLAN-001")

	Returns:
		tuple[bool, str | None]: (success, error_message) - error is None on success

	Note:
		This recursively deletes all files and subdirectories.
		Empty parent directories are also cleaned up.
	"""
	try:
		base_path = get_local_base_path()
		full_path = os.path.join(base_path, path)

		if not os.path.exists(full_path):
			return True, None

		if os.path.isdir(full_path):
			shutil.rmtree(full_path)

		_dir_path = os.path.dirname(full_path)
		while _dir_path != base_path and os.path.exists(_dir_path):
			if not os.listdir(_dir_path):
				os.rmdir(_dir_path)
				_dir_path = os.path.dirname(_dir_path)
			else:
				break

		return True, None

	except Exception as e:
		error_msg = f"Failed to delete content directory {path}: {str(e)}"
		frappe.log_error(error_msg, "Local Storage Delete Failed")
		return False, error_msg
