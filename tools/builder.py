import os

from setuptools import Extension


class Builder:
    def __init__(self):
        self.includeDir = ""

        # get the list of extensions
        self.extNames = self.scan_dir("dvedit")

        # and build up the set of Extension objects
        self.extensions = [self.make_extension(name) for name in self.extNames]

    # scan the 'dvedit' directory for extension files, converting
    # them to extension names in dotted notation
    def scan_dir(self, specified_dir, files=None):
        for file in os.listdir(specified_dir):
            path = os.path.join(specified_dir, file)
            if os.path.isfile(path) and path.endswith(".pyx"):
                files.append(path.replace(os.path.sep, ".")[:-4])
            elif os.path.isdir(path):
                self.scan_dir(path, files)
        return files

    # generate an Extension object from its dotted name
    def make_extension(self, ext_name):
        ext_path = ext_name.replace(".", os.path.sep) + ".pyx"
        return Extension(
            ext_name,
            [ext_path],
            include_dirs=[self.includeDir, "."],  # adding the '.' to include_dirs is CRUCIAL!!
            extra_compile_args=["-O3", "-Wall"],
            extra_link_args=['-g'],
            libraries=["dv", ],
        )
