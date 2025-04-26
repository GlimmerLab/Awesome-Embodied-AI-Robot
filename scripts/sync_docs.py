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
            "_includes",
            "assets",
            "index.md",
            "index_en.md",
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

def add_front_matter(content, title, description, lang="en"):
    """添加Jekyll前置元数据"""
    front_matter = f"""---
layout: default
title: {title}
description: {description}
lang: {lang}
---

"""
    return front_matter + content

def sync_readme_files():
    # 源目录和目标目录
    categories = {
        "Fundamental-Theory": {
            "en": "Fundamental Theory",
            "cn": "基础理论",
            "description_en": "Core theoretical foundations of embodied AI",
            "description_cn": "具身智能的核心理论基础"
        },
        "Robot-Learning-and-Reinforcement-Learning": {
            "en": "Robot Learning and Reinforcement Learning",
            "cn": "机器人学习与强化学习",
            "description_en": "Papers on robot learning and reinforcement learning",
            "description_cn": "机器人学习和强化学习相关论文"
        },
        "Environment-Perception": {
            "en": "Environment Perception",
            "cn": "环境感知",
            "description_en": "Research on environment perception in embodied AI",
            "description_cn": "具身智能中的环境感知研究"
        },
        "Motion-Planning": {
            "en": "Motion Planning",
            "cn": "运动规划",
            "description_en": "Motion planning algorithms and implementations",
            "description_cn": "运动规划算法与实现"
        },
        "Task-Planning": {
            "en": "Task Planning",
            "cn": "任务规划",
            "description_en": "Task planning and execution in embodied AI",
            "description_cn": "具身智能中的任务规划与执行"
        },
        "Multimodal-Interaction": {
            "en": "Multimodal Interaction",
            "cn": "多模态交互",
            "description_en": "Multimodal interaction research in embodied AI",
            "description_cn": "具身智能中的多模态交互研究"
        },
        "Simulation-Platforms": {
            "en": "Simulation Platforms",
            "cn": "仿真平台",
            "description_en": "Simulation platforms for embodied AI research",
            "description_cn": "具身智能研究的仿真平台"
        }
    }

    # 确保docs目录存在
    ensure_dir("docs")

    # 同步每个分类的README文件
    for src_dir, info in categories.items():
        if os.path.exists(src_dir):
            print(f"处理目录: {src_dir}")

            # 同步英文README
            if os.path.exists(f"{src_dir}/README.md"):
                with open(f"{src_dir}/README.md", "r", encoding="utf-8") as f:
                    content = f.read()

                # 添加前置元数据
                content = add_front_matter(
                    content,
                    info["en"],
                    info["description_en"],
                    "en"
                )

                dst_file = f"docs/{src_dir.lower().replace('-', '_')}.md"
                with open(dst_file, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"已同步 {src_dir}/README.md 到 {dst_file}")

            # 同步中文README
            if os.path.exists(f"{src_dir}/README_CN.md"):
                with open(f"{src_dir}/README_CN.md", "r", encoding="utf-8") as f:
                    content = f.read()

                # 添加前置元数据
                content = add_front_matter(
                    content,
                    info["cn"],
                    info["description_cn"],
                    "zh"
                )

                dst_file = f"docs/{src_dir.lower().replace('-', '_')}_cn.md"
                with open(dst_file, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"已同步 {src_dir}/README_CN.md 到 {dst_file}")

def create_index_files():
    # 创建英文和中文的索引文件
    categories = [
        ("fundamental_theory", "Fundamental Theory", "基础理论"),
        ("robot_learning_and_reinforcement_learning", "Robot Learning and Reinforcement Learning", "机器人学习与强化学习"),
        ("environment_perception", "Environment Perception", "环境感知"),
        ("motion_planning", "Motion Planning", "运动规划"),
        ("task_planning", "Task Planning", "任务规划"),
        ("multimodal_interaction", "Multimodal Interaction", "多模态交互"),
        ("simulation_platforms", "Simulation Platforms", "仿真平台")
    ]

    # 英文索引
    index_en_content = """---
layout: default
title: Awesome Embodied AI
description: A curated list of awesome embodied AI papers with code implementations
lang: en
---

# Awesome Embodied AI

> [English](index_en.html) | [中文](index_cn.html)

A curated list of awesome embodied AI papers with code implementations.

## Categories

"""
    for category, title_en, _ in categories:
        index_en_content += f"- [{title_en}]({category}.html)\n"

    with open("docs/index_en.md", "w", encoding="utf-8") as f:
        f.write(index_en_content)

    # 中文索引
    index_cn_content = """---
layout: default
title: 具身智能论文精选
description: 精选的具身智能论文及代码实现
lang: zh
---

# 具身智能论文精选

> 中文 | [English](index_en.html)

精选的具身智能论文及代码实现。

## 分类

"""
    for category, _, title_cn in categories:
        index_cn_content += f"- [{title_cn}]({category}_cn.html)\n"

    with open("docs/index_cn.md", "w", encoding="utf-8") as f:
        f.write(index_cn_content)

    print("已创建索引文件")

def update_config():
    # 更新_config.yml
    config = {
        "title": "Awesome Embodied AI",
        "description": "A curated list of awesome embodied AI papers with code implementations",
        "baseurl": "",
        "url": "https://glimmerlab.github.io/Awesome-Embodied-AI",
        "github_username": "LJoson",
        "theme": "jekyll-theme-minimal",
        "lang": "en",
        "languages": ["en", "zh"],
        "default_lang": "en",
        "exclude_from_langs": [],
        "lang_names": {
            "en": "English",
            "zh": "中文"
        },
        "show_downloads": True,
        "markdown": "kramdown",
        "kramdown": {
            "input": "GFM",
            "hard_wrap": False
        }
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