#!/usr/bin/env python3
import os
import shutil
import yaml
from datetime import datetime

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"创建目录: {directory}")

def clean_docs_dir():
    """清理 docs 目录，只保留必要的文件"""
    if os.path.exists("docs"):
        # 保留这些文件和目录
        keep_files = {
            "_config.yml",
            "_layouts",
            "assets",
            "index.md",
            "index_cn.md"
        }

        # 删除不需要的文件
        for item in os.listdir("docs"):
            if item not in keep_files:
                path = os.path.join("docs", item)
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
        print("已清理 docs 目录")

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

    # 同步根目录的README文件
    if os.path.exists("README.md"):
        shutil.copy2("README.md", "docs/index.md")
        print("已同步 README.md 到 docs/index.md")

    if os.path.exists("README_CN.md"):
        shutil.copy2("README_CN.md", "docs/index_cn.md")
        print("已同步 README_CN.md 到 docs/index_cn.md")

    # 同步每个分类的README文件
    for src_dir in src_dirs:
        if os.path.exists(src_dir):
            print(f"处理目录: {src_dir}")
            # 同步英文README
            if os.path.exists(f"{src_dir}/README.md"):
                dst_file = f"docs/{src_dir.lower().replace('-', '_')}.md"
                shutil.copy2(f"{src_dir}/README.md", dst_file)
                print(f"已同步 {src_dir}/README.md 到 {dst_file}")

            # 同步中文README
            if os.path.exists(f"{src_dir}/README_CN.md"):
                dst_file = f"docs/{src_dir.lower().replace('-', '_')}_cn.md"
                shutil.copy2(f"{src_dir}/README_CN.md", dst_file)
                print(f"已同步 {src_dir}/README_CN.md 到 {dst_file}")

def create_index_files():
    # 创建英文和中文的索引文件
    categories = [
        "fundamental_theory",
        "robot_learning_and_reinforcement_learning",
        "environment_perception",
        "motion_planning",
        "task_planning",
        "multimodal_interaction",
        "simulation_platforms"
    ]

    # 英文索引
    with open("docs/index.md", "w", encoding="utf-8") as f:
        f.write("# Awesome Embodied AI\n\n")
        f.write("> [English](index.md) | [中文](index_cn.md)\n\n")
        f.write("A curated list of awesome embodied AI papers with code implementations.\n\n")
        f.write("## Categories\n\n")
        for category in categories:
            title = category.replace("_", " ").title()
            f.write(f"- [{title}]({category}.md)\n")

    # 中文索引
    with open("docs/index_cn.md", "w", encoding="utf-8") as f:
        f.write("# 具身智能论文精选\n\n")
        f.write("> 中文 | [English](index.md)\n\n")
        f.write("精选的具身智能论文及代码实现。\n\n")
        f.write("## 分类\n\n")
        for category in categories:
            title_cn = {
                "fundamental_theory": "基础理论",
                "robot_learning_and_reinforcement_learning": "机器人学习与强化学习",
                "environment_perception": "环境感知",
                "motion_planning": "运动规划",
                "task_planning": "任务规划",
                "multimodal_interaction": "多模态交互",
                "simulation_platforms": "仿真平台"
            }.get(category, category)
            f.write(f"- [{title_cn}]({category}_cn.md)\n")

    print("已创建索引文件")

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
        "show_downloads": True,
        "baseurl": "",
        "url": "https://glimmerlab.github.io/Awesome-Embodied-AI"
    }

    with open("docs/_config.yml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    print("已更新 _config.yml")

def main():
    print("开始同步文档...")
    clean_docs_dir()  # 首先清理 docs 目录
    sync_readme_files()
    create_index_files()
    update_config()

    # 列出docs目录中的所有文件
    print("\ndocs目录中的文件:")
    for root, dirs, files in os.walk("docs"):
        for file in files:
            print(f"  {os.path.join(root, file)}")

    print("\n文档同步完成！")

if __name__ == "__main__":
    main()