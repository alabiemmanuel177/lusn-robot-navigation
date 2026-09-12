from glob import glob
from setuptools import setup

package_name = "language_nav_bringup"
setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    tests_require=["pytest"],
    test_suite="test.test_launch_source",
    zip_safe=True,
    entry_points={
        "console_scripts": [
            "landmark_bridge_runner = language_nav_bringup.landmark_bridge_runner:main",
        ],
    },
)
