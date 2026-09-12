from setuptools import find_packages, setup

package_name = "language_nav_runtime"

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
    maintainer="Emmanuel Alabi Olasubomi",
    maintainer_email="emmanuel@example.invalid",
    description="Fail-closed Research 2 and Nav2 live adapters for Research 3.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "monitor_bridge = language_nav_runtime.monitor_bridge:main",
            "semantic_route_node = language_nav_runtime.semantic_routes:main",
            "nav2_route_adapter = language_nav_runtime.nav2_adapter:main",
        ]
    },
)
