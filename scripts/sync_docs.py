#!/usr/bin/env python3
import os
import shutil
import yaml
from datetime import datetime

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def sync_readme_files():
    # 源目录和目标目录
    src_dirs = [
        "Fundamental-Theory",
        "Robot-Learning-and-Reinforcement-Learning",
        "Environment-Perception",
        "Motion-Planning",
        "Task-Planning",
        "Multimodal-Interaction",
        "Simulation-Platforms"
    ]

    # 确保docs目录存在
    ensure_dir("docs")

    # 同步每个分类的README文件
    for src_dir in src_dirs:
        if os.path.exists(src_dir):
            # 同步英文README
            if os.path.exists(f"{src_dir}/README.md"):
                dst_file = f"docs/{src_dir.lower().replace('-', '_')}.md"
                shutil.copy2(f"{src_dir}/README.md", dst_file)

            # 同步中文README
            if os.path.exists(f"{src_dir}/README_CN.md"):
                dst_file = f"docs/{src_dir.lower().replace('-', '_')}_cn.md"
                shutil.copy2(f"{src_dir}/README_CN.md", dst_file)

def update_config():
    # 更新_config.yml
    config = {
        "title": "Awesome Embodied AI",
        "description": "A curated list of awesome embodied AI papers with code implementations",
        "theme": "jekyll-theme-minimal",
        "lang": "zh-CN",
        "languages": ["en", "zh-CN"],
        "default_lang": "zh-CN",
        "exclude_from_langs": [],
        "lang_names": {
            "en": "English",
            "zh-CN": "中文"
        },
        "show_downloads": True
    }

    with open("docs/_config.yml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

def main():
    print("开始同步文档...")
    sync_readme_files()
    update_config()
    print("文档同步完成！")

if __name__ == "__main__":
    main()