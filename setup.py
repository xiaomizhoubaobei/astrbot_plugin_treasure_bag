from setuptools import setup, find_packages
from pathlib import Path

# 使用更健壮的方式读取README文件
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="astrbot_plugin_treasure_bag",
    version="0.0.2",
    description="一个用于 astrbot 的宝藏袋插件",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/xiaomizhoubaobei/astrbot_plugin_treasure_bag_plugin",
    author="祁筱欣", # Replace with your name
    author_email="mzapi@x.mizhoubaobei.top", # Replace with your email
    packages=find_packages(),
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    project_urls={
        "Homepage": "https://github.com/xiaomizhoubaobei/astrbot_plugin_treasure_bag_plugin",
        "Download": "https://github.com/xiaomizhoubaobei/astrbot_plugin_treasure_bag_plugin/releases",
        "Issues": "https://github.com/xiaomizhoubaobei/astrbot_plugin_treasure_bag_plugin/issues",
        "Bug": "https://github.com/xiaomizhoubaobei/astrbot_plugin_treasure_bag_plugin/issues",
        "GitHub": "https://github.com/xiaomizhoubaobei/astrbot_plugin_treasure_bag_plugin",
        "Twitter": "https://x.com/XinXiao12088",
    },
)