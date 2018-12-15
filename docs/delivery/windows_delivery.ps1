# Global settings
$scripts_dir = 'pyinstaller.exe'

# specs path
$binary_path = """start.spec"""
$launcher_path = """launcher.spec"""

function DeliverOctobotForWindows($name, $python_dir)
{
    $name
    cd $python_dir
    "Compiling launcher..."
    & $scripts_dir $binary_path
    "Compiling binary..."
    & $scripts_dir $launcher_path
}


#DeliverOctobotForWindows("32 bits", """PATH_TO_YOUR_PYTHON_32_SCRIPTS_FOLDER""")
DeliverOctobotForWindows("64 bits", """PATH_TO_YOUR_PYTHON_64_SCRIPTS_FOLDER""")