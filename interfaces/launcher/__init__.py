def create_environment_file(file_to_dl, result_file_path):
    file_content = requests.get(file_to_dl).text
    directory = os.path.dirname(result_file_path)

    if not os.path.exists(directory) and directory:
        os.makedirs(directory)

    file_name = result_file_path
    if not os.path.isfile(file_name) and file_name:
        with open(file_name, "w") as new_file_from_dl:
            new_file_from_dl.write(file_content)