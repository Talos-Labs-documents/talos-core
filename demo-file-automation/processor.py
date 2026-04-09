import os
from utils import read_file, write_file


def process_files(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for filename in os.listdir(input_folder):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)

        content = read_file(input_path)
        processed = content.upper()

        write_file(output_path, processed)