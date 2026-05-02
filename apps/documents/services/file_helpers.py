import os


def get_file_extension(filename):
    return os.path.splitext(filename)[1].lower()


def get_file_type(filename):
    extension = get_file_extension(filename)

    file_type_map = {
        ".pdf": "pdf",
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".doc": "document",
        ".docx": "document",
    }

    return file_type_map.get(extension, "file")