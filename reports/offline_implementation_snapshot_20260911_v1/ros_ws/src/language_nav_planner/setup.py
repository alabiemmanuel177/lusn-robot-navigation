from setuptools import find_packages, setup

package_name = "language_nav_planner"
setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    tests_require=["pytest"],
    test_suite="test.test_node_import",
    zip_safe=True,
    entry_points={"console_scripts": ["planner_node = language_nav_planner.node:main"]},
)
