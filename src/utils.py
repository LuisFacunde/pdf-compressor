def get_file_size(file_path) -> int:
    return file_path.stat().st_size if file_path.exists() else 0


def format_file_size(size_bytes: float) -> str:
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f}{size_names[i]}"


def calculate_compression_ratio(original_size: int, compressed_size: int) -> float:
    if original_size == 0:
        return 0.0
    return ((original_size - compressed_size) / original_size) * 100
