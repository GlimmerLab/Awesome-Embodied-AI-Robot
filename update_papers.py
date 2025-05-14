import os
import re
import json
import requests
import arxiv
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from tqdm import tqdm
import string
import logging
import traceback
import argparse

"""
论文更新脚本 - 具身AI与机器人相关论文收集工具

主要功能:
1. 从arXiv获取最新的具身AI与机器人相关论文
2. 对论文进行智能分类和评分
3. 自动更新各分类目录下的README文件
4. 支持按发布日期过滤论文(新功能)

使用方法:
- 基本运行: python update_papers.py
  (默认获取最近30天内发布的论文)

- 指定日期范围: python update_papers.py --days 60
  (获取最近60天内发布的论文)

- 获取更长时间范围: python update_papers.py --days 90
  (获取最近90天内发布的论文)

- 仅获取最新论文: python update_papers.py --days 7
  (获取最近7天内发布的论文)
"""

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PaperUpdater:
    def __init__(self, days_filter=30):
        """
        初始化论文更新器
        Args:
            days_filter: 筛选最近多少天内的论文，默认30天
        """
        # 保存日期筛选配置
        self.days_filter = days_filter
        logger.info(f"初始化论文更新器，筛选最近 {self.days_filter} 天内发表的论文")

        # 分类名称及对应的arXiv分类和关键词
        self.categories = {
            "Motion-Planning": "cs.RO OR cs.AI AND (motion planning OR path planning OR trajectory planning OR navigation)",
            "Task-Planning": "cs.AI OR cs.RO AND (task planning OR hierarchical planning OR symbolic planning OR goal reasoning)",
            "Simulation-Platforms": "cs.RO OR cs.AI AND (simulation OR simulator OR virtual environment OR digital twin)",
            "Robot-Learning-and-Reinforcement-Learning": "cs.LG OR cs.AI OR cs.RO AND (robot learning OR reinforcement learning OR imitation learning)",
            "Multimodal-Interaction": "cs.HC OR cs.AI OR cs.RO AND (human-robot interaction OR multimodal interaction OR natural language instruction OR gesture recognition)",
            "Environment-Perception": "cs.CV OR cs.RO AND (perception OR object detection OR scene understanding OR 3D reconstruction OR SLAM)",
            "Fundamental-Theory": "cs.AI OR cs.RO AND (theory OR algorithm OR topology OR kinematics OR dynamics)"
        }

        # 机器人特定硬件关键词 - 添加到查询中以提高相关性
        self.robot_hardware_keywords = [
            "humanoid", "quadruped", "biped", "manipulator", "end-effector", "gripper",
            "drone", "mobile robot", "legged", "wheeled", "soft robot", "exoskeleton",
            "UAV", "surgical robot", "prosthetic", "omnidirectional", "underactuated",
            "dexterous hand", "assistive robot", "industrial robot", "collaborative robot",
            "atlas", "anymal", "spot", "cassie", "digit", "nao", "icub", "tiago", "baxter",
            "pepper", "stretch", "go1", "aliengo", "unitree", "asimo", "romeo", "valkyrie",
            "jaco", "panda", "sawyer", "franka", "ur5", "ur10", "abb", "kuka", "fanuc",
            "motoman", "yaskawa", "denso", "kinova", "schunk", "robotiq", "barrett",
            "shadow hand", "allegro", "dynamixel", "robobee", "darwin", "talos", "husky",
            "jackal", "clearpath", "turtlebot", "roomba", "laikago", "a1", "mini cheetah"
        ]

        # 机器人任务关键词 - 添加到查询中以提高相关性
        self.robot_task_keywords = [
            "locomotion", "manipulation", "grasping", "navigation", "exploration",
            "planning", "control", "learning", "perception", "interaction", "teleoperation",
            "surveillance", "inspection", "mapping", "tracking", "recognition", "detection",
            "segmentation", "localization", "SLAM", "path planning", "motion planning",
            "task planning", "skill learning", "policy learning", "reinforcement learning",
            "imitation learning", "sim2real", "transfer learning", "multi-task learning",
            "dexterous manipulation", "whole-body control", "agile motion", "parkour",
            "obstacle avoidance", "trajectory optimization", "reactive planning",
            "climbing", "contact-rich manipulation", "precision control", "assembly",
            "pick-and-place", "bin-picking", "in-hand manipulation", "multi-fingered",
            "visual servoing", "terrain traversal", "dynamic balance", "jumping", "running"
        ]

        # 机器人特定技术关键词 - 添加到查询中以提高相关性
        self.robot_tech_keywords = [
            "trajectory optimization", "model predictive control", "optimal control",
            "inverse kinematics", "forward kinematics", "dynamics", "whole-body control",
            "impedance control", "force control", "visual servoing", "sensor fusion",
            "perception", "deep learning", "reinforcement learning", "computer vision",
            "state estimation", "motion capture", "human-robot interaction", "HRI",
            "collision avoidance", "path planning", "SLAM", "odometry", "point cloud",
            "operational space control", "task space control", "torque control",
            "position control", "velocity control", "compliance control", "admittance control",
            "null-space control", "hierarchical control", "task priority", "differential IK",
            "contact planning", "multi-contact", "centroidal dynamics", "zero-moment point",
            "capture point", "divergent component of motion", "momentum-based control",
            "passivity-based control", "adaptive control", "robust control", "learning-based control",
            "neural network control", "model-based RL", "model-free RL", "sim-to-real transfer"
        ]

        # 初始化手动添加的论文字典
        self.manually_added_papers = {}

        # 定义各主题的标签和关键词
        self.tags = {
            # 强化学习标签
            "Robot-Learning-and-Reinforcement-Learning": {
                "Foundational": ["robot foundational", "robot fundamental", "robot core", "robot basic", "robot essential", "robot pioneering", "robot seminal"],
                "Imitation": ["robot imitation", "robot demonstration", "robot expert", "robot teacher", "robot learning from demonstration", "robot behavioral cloning", "robot apprenticeship learning"],
                "Milestone": ["robot milestone", "robot breakthrough", "robot significant", "robot important", "robot key", "robot landmark", "robot pivotal"],
                "Biped": ["biped robot", "bipedal robot", "humanoid robot", "two-legged robot", "robot walking", "robot running", "robot jumping"],
                "Quadruped": ["quadruped robot", "four-legged robot", "dog robot", "robot animal", "robot canine", "robot feline", "robot mammal"],
                "AMP": ["robot AMP", "robot adversarial", "robot motion prior", "robot style", "robot character", "robot motion style", "robot motion imitation"],
                "Adaptation": ["robot adaptation", "robot transfer", "robot generalization", "robot robust", "robot resilient", "robot domain adaptation", "robot zero-shot", "robot few-shot"],
                "Policy": ["robot policy", "robot actor-critic", "robot PPO", "robot SAC", "robot DDPG", "robot TRPO", "robot policy optimization", "robot policy gradient", "robot value function"],
                "Sim2Real": ["robot sim2real", "robot sim-to-real", "robot transfer", "robot domain", "robot reality gap", "robot simulation transfer", "robot simulation adaptation"],
                "Hierarchical": ["robot hierarchical", "robot HRL", "robot option", "robot skill", "robot subgoal", "robot hierarchical RL", "robot option discovery", "robot skill discovery"],
                "Multi-Task": ["robot multi-task", "robot multi-task learning", "robot generalist", "robot versatile", "robot multi-task RL", "robot task generalization", "robot task transfer"],
                "Offline": ["robot offline", "robot batch", "robot off-policy", "robot data-driven", "robot offline RL", "robot batch RL", "robot conservative RL", "robot data-efficient"],
                "Meta": ["robot meta", "robot meta-learning", "robot few-shot", "robot adaptation", "robot meta-RL", "robot model-agnostic meta-learning", "robot reptile", "robot maml"],
                "Multi-Agent": ["robot multi-agent", "robot collaboration", "robot cooperation", "robot interaction", "robot multi-agent RL", "robot team learning", "robot collective intelligence"]
            },
            # 运动规划标签
            "Motion-Planning": {
                "Trajectory": ["robot trajectory", "robot path", "robot motion", "robot planning", "robot optimization", "robot trajectory optimization", "robot path planning", "robot motion planning", "robot trajectory generation"],
                "Collision": ["robot collision", "robot avoidance", "robot safety", "robot obstacle", "robot collision avoidance", "robot obstacle avoidance", "robot safety constraints", "robot collision-free"],
                "Real-time": ["robot real-time", "robot realtime", "robot fast", "robot efficient", "robot computational", "robot real-time planning", "robot fast planning", "robot efficient planning"],
                "Learning": ["robot learning", "robot learned", "robot neural", "robot deep", "robot ML", "robot learning-based planning", "robot neural planning", "robot deep planning"],
                "Dynamic": ["robot dynamic", "robot dynamics", "robot kinematic", "robot kinematics", "robot dynamic planning", "robot dynamics-aware", "robot kinematic planning", "robot dynamic constraints"],
                "Uncertainty": ["robot uncertainty", "robot robust", "robot stochastic", "robot probabilistic", "robot uncertainty-aware", "robot robust planning", "robot stochastic planning"],
                "Multi-robot": ["multi-robot", "robot swarm", "robot collaborative", "robot coordination", "multi-robot planning", "robot swarm planning", "robot collaborative planning"],
                "Reactive": ["robot reactive", "robot reaction", "robot responsive", "robot adaptive", "robot reactive planning", "robot reactive control", "robot responsive planning", "robot adaptive planning"],
                "Whole-body": ["robot whole-body", "robot full-body", "robot whole-body planning", "robot full-body planning", "robot whole-body motion", "robot full-body motion", "robot whole-body control"],
                "Humanoid": ["humanoid robot", "humanoid planning", "humanoid control", "humanoid motion", "humanoid locomotion", "humanoid walking", "humanoid running"],
                "Adaptive": ["adaptive robot", "adaptive motion", "adaptive control", "adaptive planning", "adaptive optimization", "adaptive trajectory", "adaptive locomotion", "adaptive whole-body"],
                "Hyper-Dexterous": ["hyper-dexterous robot", "dexterous robot", "dexterous manipulation", "dexterous control", "dexterous motion", "high dexterity robot", "complex manipulation"]
            },
            # 任务规划标签
            "Task-Planning": {
                "Hierarchical": ["robot hierarchical", "robot hierarchy", "robot decomposition", "robot subtask", "robot hierarchical planning", "robot task decomposition", "robot subtask planning"],
                "Temporal": ["robot temporal", "robot temporal logic", "robot sequence", "robot ordering", "robot temporal planning", "robot sequence planning", "robot temporal constraints"],
                "Learning": ["robot task learning", "robot task learned", "robot task neural", "robot task deep", "robot task ML", "robot learning-based planning", "robot neural planning"],
                "Semantic": ["robot semantic", "robot language", "robot instruction", "robot command", "robot semantic planning", "robot language-based planning", "robot instruction-based planning"],
                "Multi-agent": ["robot multi-agent", "robot task collaboration", "robot task cooperation", "robot task interaction", "robot multi-agent planning", "robot collaborative planning"],
                "Uncertainty": ["robot task uncertainty", "robot task robust", "robot task stochastic", "robot task probabilistic", "robot task uncertainty-aware", "robot robust planning"],
                "Interactive": ["robot interactive", "robot human", "robot user", "robot feedback", "robot interactive planning", "robot human-in-the-loop", "robot user feedback"],
                "Long-horizon": ["robot long-horizon", "robot long-term", "robot complex", "robot sequential", "robot long-horizon planning", "robot long-term planning", "robot complex task"],
                "TAMP": ["robot TAMP", "robot task and motion planning", "robot integrated planning", "robot combined planning", "robot task-motion", "robot task-motion integration"],
                "Reasoning": ["robot reasoning", "robot logical", "robot symbolic", "robot abstract", "robot task reasoning", "robot logical planning", "robot symbolic planning"]
            },
            # 仿真平台标签
            "Simulation-Platforms": {
                "en": "This directory collects papers and code implementations related to simulation platforms in embodied AI.",
                "cn": "本目录收集了具身智能中与仿真平台相关的论文和代码实现。"
            },
            "Multimodal-Interaction": {
                "en": "This directory collects papers and code implementations related to multimodal interaction in embodied AI.",
                "cn": "本目录收集了具身智能中与多模态交互相关的论文和代码实现。"
            },
            "Environment-Perception": {
                "en": "This directory collects papers and code implementations related to environment perception in embodied AI.",
                "cn": "本目录收集了具身智能中与环境感知相关的论文和代码实现。"
            },
            "Fundamental-Theory": {
                "en": "This directory collects papers and code implementations related to fundamental theory in embodied AI.",
                "cn": "本目录收集了具身智能中与基础理论相关的论文和代码实现。"
            }
        }

        self.existing_papers = self.load_existing_papers()
        self.keywords = self.extract_keywords_from_existing_papers()

    def ensure_directory_exists(self, directory):
        """确保目录存在，如果不存在则创建"""
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"创建目录: {directory}")
        except Exception as e:
            logger.error(f"创建目录 {directory} 失败: {str(e)}")
            raise

    def load_existing_papers(self):
        """加载现有论文信息，包括手动添加和自动更新的论文"""
        existing_papers = {}
        for category in self.categories.keys():
            existing_papers[category] = []
            en_file = f"{category}/README.md"
            cn_file = f"{category}/README_CN.md"

            # 确保目录存在
            self.ensure_directory_exists(category)

            if os.path.exists(en_file):
                try:
                    with open(en_file, "r", encoding="utf-8") as f:
                        content = f.read()

                        # 检查是否有手动添加的论文块
                        manual_papers_match = re.search(r'## Manually Added Papers\n\n(.*?)(?=\n## |$)', content, re.DOTALL)
                        if manual_papers_match:
                            manual_papers_content = manual_papers_match.group(1)
                            # 提取手动添加的论文信息
                            manual_table_rows = re.findall(r'\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|', manual_papers_content)
                            for row in manual_table_rows:
                                # 跳过表头行
                                if row[0].strip() == "Date" or row[0].strip() == "日期":
                                    continue
                                if row[0].strip() == ":---:":
                                    continue

                                try:
                                    date, title, pdf_link, code_link, rating = row
                                    # 提取PDF链接
                                    pdf_url_match = re.search(r'\[\[pdf\]\]\((.*?)\)', pdf_link)
                                    pdf_url = pdf_url_match.group(1) if pdf_url_match else pdf_link

                                    # 提取代码链接
                                    code_url_match = re.search(r'\[(.*?)\]\((.*?)\)', code_link)
                                    if code_url_match:
                                        code_url = code_url_match.group(2)
                                    else:
                                        code_url = code_url_match.group(0) if code_url_match else code_link.strip()

                                    # 清理标题
                                    clean_title = title.strip()

                                    paper_info = {
                                        "date": date.strip(),
                                        "title": clean_title,
                                        "pdf_url": pdf_url,
                                        "code_url": code_url,
                                        "rating": rating.strip(),
                                        "manual": True  # 标记为手动添加
                                    }
                                    existing_papers[category].append(paper_info)

                                    # 将手动添加的论文保存到manually_added_papers字典中
                                    if category not in self.manually_added_papers:
                                        self.manually_added_papers[category] = []
                                    self.manually_added_papers[category].append(paper_info)
                                except Exception as e:
                                    logger.error(f"解析手动添加的论文行时出错: {str(e)}\n行内容: {row}")
                                    continue

                        # 提取自动更新的论文信息
                        auto_papers_match = re.search(r'## Auto-Updated Papers\n\n(.*?)(?=\n## |$)', content, re.DOTALL)
                        if auto_papers_match:
                            auto_papers_content = auto_papers_match.group(1)
                            table_rows = re.findall(r'\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|', auto_papers_content)
                            for row in table_rows:
                                # 跳过表头行
                                if row[0].strip() == "Date" or row[0].strip() == "日期":
                                    continue
                                if row[0].strip() == ":---:":
                                    continue

                                try:
                                    date, title, pdf_link, code_link, rating = row
                                    # 提取PDF链接
                                    pdf_url_match = re.search(r'\[\[pdf\]\]\((.*?)\)', pdf_link)
                                    pdf_url = pdf_url_match.group(1) if pdf_url_match else pdf_link

                                    # 提取代码链接
                                    code_url_match = re.search(r'\[(.*?)\]\((.*?)\)', code_link)
                                    if code_url_match:
                                        code_url = code_url_match.group(2)
                                    else:
                                        code_url = code_url_match.group(0) if code_url_match else code_link.strip()

                                    # 清理标题
                                    clean_title = title.strip()

                                    # 提取标签（如果有）
                                    tag = ""
                                    tag_match = re.match(r'\[(.*?)\](.*)', clean_title)
                                    if tag_match:
                                        tag = tag_match.group(1)
                                        clean_title = tag_match.group(2).strip()

                                    existing_papers[category].append({
                                        "date": date.strip(),
                                        "title": clean_title,
                                        "tag": tag,
                                        "pdf_url": pdf_url,
                                        "code_url": code_url,
                                        "rating": rating.strip(),
                                        "manual": False  # 标记为自动更新
                                    })
                                except Exception as e:
                                    logger.error(f"解析自动更新的论文行时出错: {str(e)}\n行内容: {row}")
                                    continue
                except Exception as e:
                    logger.error(f"读取文件 {en_file} 时出错: {str(e)}")
                    logger.error(traceback.format_exc())

        return existing_papers

    def extract_keywords_from_existing_papers(self):
        """从现有论文标题中提取关键词，结合类别定义的机器人相关关键词"""
        keywords = {}
        for category, papers in self.existing_papers.items():
            try:
                # 如果没有现有论文，直接使用类别定义的关键词
                if not papers:
                    keywords[category] = self.categories[category]
                    continue

                # 收集所有标题和主题内容关键词
                titles = [paper["title"] for paper in papers]

                # 处理手动添加的论文，这些通常更相关
                manual_papers = [p for p in papers if p.get("manual", False)]
                manual_titles = [p["title"] for p in manual_papers] if manual_papers else []

                # 从标题中提取关键词
                all_words = []
                # 如果有手动添加的论文，优先使用这些
                title_list = manual_titles if manual_titles else titles
                for title in title_list:
                    # 分词，按空格和标点符号分割
                    words = re.findall(r'\b\w+\b', title.lower())
                    # 过滤掉太短的词和常见停用词
                    words = [word for word in words if len(word) > 3 and word not in ['with', 'from', 'that', 'this', 'for', 'and', 'the', 'based', 'using', 'via']]
                    all_words.extend(words)

                # 统计词频
                word_freq = {}
                for word in all_words:
                    if word in word_freq:
                        word_freq[word] += 1
                    else:
                        word_freq[word] = 1

                # 定义机器人相关核心关键词
                robot_core_keywords = ['robot', 'embodied', 'humanoid', 'legged', 'quadruped', 'biped', 'manipulation', 'locomotion', 'autonomous', 'dexterous']

                # 定义各类别特定的关键词
                category_specific_keywords = {
                    "Motion-Planning": ['motion', 'planning', 'trajectory', 'path', 'collision', 'avoidance', 'whole-body', 'dynamic', 'kinodynamic', 'reactive', 'agile'],
                    "Task-Planning": ['task', 'planning', 'tamp', 'hierarchical', 'decomposition', 'scheduling', 'semantic', 'symbolic', 'reasoning', 'long-horizon', 'belief'],
                    "Robot-Learning-and-Reinforcement-Learning": ['reinforcement', 'learning', 'policy', 'imitation', 'skill', 'sim2real', 'transfer', 'adaptation', 'meta', 'offline', 'hierarchical'],
                    "Simulation-Platforms": ['physics', 'simulation', 'simulator', 'environment', 'digital', 'twin', 'benchmark', 'testbed', 'synthetic', 'domain', 'randomization'],
                    "Multimodal-Interaction": ['multimodal', 'interaction', 'vision', 'language', 'gesture', 'speech', 'tactile', 'haptic', 'teleoperation', 'interface', 'dialog'],
                    "Environment-Perception": ['perception', 'environment', 'scene', 'object', 'slam', 'mapping', 'sensor', 'fusion', 'detection', 'recognition', 'segmentation', 'estimation'],
                    "Fundamental-Theory": ['theory', 'cognitive', 'control', 'representation', 'generalization', 'reasoning', 'foundation', 'world', 'model', 'benchmark', 'survey']
                }

                # 选择最常见的词作为关键词，但确保必须包含机器人相关词
                robot_words = []

                # 首先添加核心机器人关键词出现在标题中的词
                for word in robot_core_keywords:
                    if any(word in title.lower() for title in title_list):
                        robot_words.append(word)

                # 然后添加类别特定的关键词
                category_words = []
                if category in category_specific_keywords:
                    for word in category_specific_keywords[category]:
                        if any(word in title.lower() for title in title_list):
                            category_words.append(word)

                # 从词频统计中选择高频词
                frequent_words = [word for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:15]]

                # 组合所有关键词，确保每个都以"robot"为前缀
                combined_keywords = []

                # 核心机器人关键词直接加入
                for word in robot_words:
                    combined_keywords.append(f"robot {word}")

                # 类别特定关键词加入
                for word in category_words:
                    combined_keywords.append(f"robot {word}")

                # 常见词加入（避免重复）
                for word in frequent_words:
                    if word not in robot_words and word not in category_words and word not in ['with', 'from', 'that', 'this', 'for', 'and', 'the', 'based', 'using', 'via']:
                        combined_keywords.append(f"robot {word}")

                # 构建查询
                if combined_keywords:
                    keyword_query = " OR ".join(combined_keywords)
                    # 确保查询始终包含原始类别关键词作为基础
                    keywords[category] = f"({self.categories[category]}) AND ({keyword_query})"
                else:
                    keywords[category] = self.categories[category]
            except Exception as e:
                logger.error(f"为类别 {category} 提取关键词时出错: {str(e)}")
                logger.error(traceback.format_exc())
                # 失败时使用默认关键词
                keywords[category] = self.categories[category]

        return keywords

    def get_paper_info(self, paper_id):
        """获取论文的详细信息，包括代码链接"""
        try:
            code_url = self.base_url + paper_id
            response = requests.get(code_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "official" in data and "url" in data["official"]:
                    return data["official"]["url"]
            return None
        except Exception as e:
            logger.warning(f"获取论文 {paper_id} 的代码链接时出错: {str(e)}")
            return None

    def identify_tag(self, category, title, abstract):
        """识别论文的标签，根据标题和摘要内容匹配最合适的标签"""
        if category not in self.tags:
            return ""

        # 将标题和摘要转为小写以进行匹配
        text = (title + " " + abstract).lower()

        # 确保论文内容与机器人或具身智能相关
        robot_related_terms = ['robot', 'embodied', 'humanoid', 'legged', 'quadruped', 'biped', 'manipulation', 'locomotion', 'autonomous', 'dexterous']
        if not any(term in text for term in robot_related_terms):
            return ""  # 如果没有任何机器人相关术语，返回空标签

        # 计算每个标签的匹配分数
        tag_scores = {}
        for tag, keywords in self.tags[category].items():
            score = 0
            matched_keywords = []

            for keyword in keywords:
                if keyword.lower() in text:
                    # 提高与机器人直接相关关键词的权重
                    if 'robot' in keyword or 'embodied' in keyword:
                        score += 2
                        matched_keywords.append(keyword)
                    else:
                        score += 1
                        matched_keywords.append(keyword)

            # 给标题中出现的关键词额外权重
            for keyword in keywords:
                if keyword.lower() in title.lower():
                    score += 2
                    if keyword not in matched_keywords:
                        matched_keywords.append(keyword)

            if score > 0:
                tag_scores[tag] = {
                    'score': score,
                    'matched_keywords': matched_keywords
                }

        # 如果找到匹配的标签，返回得分最高的
        if tag_scores:
            # 对于相同分数的标签，优先选择更具体的标签（匹配关键词数量更多或名称更长）
            best_tags = sorted(tag_scores.items(), key=lambda x: (x[1]['score'], len(x[1]['matched_keywords']), len(x[0])), reverse=True)
            return best_tags[0][0]

        # 如果没有找到匹配，尝试从标题中提取
        if ":" in title:
            prefix = title.split(":")[0].strip()
            # 只有当前缀较短且不含常见词时才使用它作为标签
            common_words = ['a', 'an', 'the', 'on', 'for', 'in', 'with', 'and', 'or', 'of', 'to', 'from']
            if len(prefix) < 20 and not any(word in prefix.lower().split() for word in common_words):
                return prefix

        return ""

    def determine_paper_category(self, title, abstract):
        """
        根据论文标题和摘要确定其最适合归类的目录
        使用加权评分系统进行精细分类
        """
        combined_text = (title + " " + abstract).lower()

        # 各类别的核心关键词权重
        category_core_keywords = {
            "Motion-Planning": {
                'motion planning': 10, 'trajectory optimization': 10, 'path planning': 10,
                'collision avoidance': 8, 'whole-body control': 8, 'humanoid control': 8,
                'motion generation': 7, 'trajectory planning': 7, 'legged locomotion': 8,
                'navigation': 6, 'parkour': 9, 'agile motion': 7, 'dynamic motion': 7,
                'real-time planning': 6, 'kinodynamic planning': 7, 'hybrid planning': 6,
                'locomotion control': 8, 'motion synthesis': 7, 'motion primitives': 6,
                'contact planning': 7, 'multi-contact': 7, 'mpc': 6, 'model predictive control': 6
            },
            "Task-Planning": {
                'task planning': 10, 'task decomposition': 9, 'hierarchical planning': 8,
                'tamp': 10, 'task and motion planning': 10, 'long-horizon planning': 8,
                'semantic planning': 7, 'manipulation planning': 8, 'multi-agent planning': 7,
                'task scheduling': 7, 'symbolic planning': 7, 'sequence planning': 6,
                'plan adaptation': 7, 'goal reasoning': 7, 'pddl': 8, 'belief planning': 7,
                'plan verification': 6, 'abstract planning': 6, 'temporal planning': 7,
                'logical planning': 7, 'resource planning': 6, 'constraint planning': 6
            },
            "Robot-Learning-and-Reinforcement-Learning": {
                'reinforcement learning': 10, 'rl': 9, 'policy learning': 8,
                'imitation learning': 9, 'sim2real': 9, 'offline rl': 8,
                'meta learning': 7, 'transfer learning': 8, 'multi-task learning': 8,
                'adaptive learning': 7, 'deep reinforcement learning': 9, 'skill learning': 8,
                'policy optimization': 8, 'hierarchical rl': 8, 'curriculum learning': 7,
                'motion prior': 7, 'adversarial motion prior': 9, 'amp': 7,
                'zero-shot learning': 8, 'few-shot learning': 7, 'model-based rl': 8,
                'self-supervised learning': 7, 'representation learning': 6,
                'inverse reinforcement learning': 8, 'reward learning': 7
            },
            "Multimodal-Interaction": {
                'human-robot interaction': 10, 'hri': 9, 'multimodal interaction': 10,
                'vision-language': 8, 'gesture recognition': 8, 'speech interaction': 8,
                'teleoperation': 9, 'social robotics': 9, 'tactile interaction': 8,
                'natural language': 7, 'embodied communication': 8, 'interface': 6,
                'haptic': 7, 'human-robot co-learning': 8, 'dialog': 6,
                'emotion recognition': 7, 'human tracking': 7, 'assistive robotics': 8,
                'shared autonomy': 8, 'telemanipulation': 9, 'human-in-the-loop': 7,
                'robot teaching': 7, 'multi-modal fusion': 7, 'human-robot teaming': 7
            },
            "Environment-Perception": {
                'perception': 9, 'environment perception': 10, 'visual perception': 8,
                'slam': 10, 'scene understanding': 9, 'object detection': 9,
                'semantic segmentation': 8, 'depth estimation': 8, '3d reconstruction': 8,
                'point cloud processing': 8, 'sensor fusion': 8, 'mapping': 8,
                'terrain understanding': 9, 'object recognition': 8, 'visual navigation': 8,
                'object tracking': 7, 'active perception': 7, 'novelty detection': 7,
                'self-localization': 8, 'semantic mapping': 8, 'affordance detection': 7,
                'place recognition': 7, 'anomaly detection': 7, 'geometric perception': 7
            },
            "Simulation-Platforms": {
                'simulation': 10, 'simulator': 10, 'physics engine': 9,
                'digital twin': 9, 'synthetic data': 8, 'benchmark platform': 8,
                'virtual environment': 8, 'learning environment': 8, 'embodied simulation': 9,
                'simulation framework': 8, 'test environment': 7, 'high-fidelity simulation': 8,
                'physics-based simulation': 9, 'domain randomization': 8, 'sim-to-real': 8,
                'differentiable simulation': 8, 'simulator calibration': 7, 'benchmark': 7,
                'evaluation platform': 7, 'simulation testbed': 8, 'robot environment': 8
            },
            "Fundamental-Theory": {
                'embodied ai theory': 10, 'embodied intelligence': 10, 'embodied learning': 9,
                'cognitive science': 8, 'control theory': 8, 'embodied cognition': 9,
                'computational models': 7, 'learning theory': 9, 'evaluation methods': 7,
                'embodied representation': 8, 'generalization': 7, 'reasoning': 8,
                'foundation model': 9, 'survey': 8, 'benchmark': 7, 'theoretical framework': 8,
                'world model': 8, 'intrinsic motivation': 7, 'self-supervision': 7,
                'developmental robotics': 8, 'robot cognition': 8, 'robot intelligence': 9,
                'meta-learning theory': 7, 'representation theory': 7, 'robot optimization': 7
            }
        }

        # 特殊关键词组合，如果匹配则直接分类
        special_combination_categories = {
            ('adaptive motion optimization', 'humanoid'): "Motion-Planning",
            ('amo', 'humanoid'): "Motion-Planning",
            ('humanoid', 'whole-body', 'control'): "Motion-Planning",
            ('legged', 'locomotion', 'control'): "Motion-Planning",
            ('parkour', 'robot'): "Motion-Planning",
            ('agile', 'motion', 'robot'): "Motion-Planning",
            ('tamp', 'robot'): "Task-Planning",
            ('task and motion planning', 'robot'): "Task-Planning",
            ('task', 'decomposition', 'planning'): "Task-Planning",
            ('long-horizon', 'task', 'planning'): "Task-Planning",
            ('semantic', 'task', 'planning'): "Task-Planning",
            ('reinforcement learning', 'robot'): "Robot-Learning-and-Reinforcement-Learning",
            ('rl', 'robot'): "Robot-Learning-and-Reinforcement-Learning",
            ('imitation learning', 'robot'): "Robot-Learning-and-Reinforcement-Learning",
            ('policy', 'learning', 'robot'): "Robot-Learning-and-Reinforcement-Learning",
            ('sim2real', 'robot'): "Robot-Learning-and-Reinforcement-Learning",
            ('human-robot', 'interaction'): "Multimodal-Interaction",
            ('hri', 'robot'): "Multimodal-Interaction",
            ('teleoperation', 'interface'): "Multimodal-Interaction",
            ('multimodal', 'communication', 'robot'): "Multimodal-Interaction",
            ('gesture', 'recognition', 'robot'): "Multimodal-Interaction",
            ('speech', 'interaction', 'robot'): "Multimodal-Interaction",
            ('slam', 'robot'): "Environment-Perception",
            ('mapping', 'robot'): "Environment-Perception",
            ('environment', 'perception', 'robot'): "Environment-Perception",
            ('object', 'detection', 'robot'): "Environment-Perception",
            ('sensor', 'fusion', 'robot'): "Environment-Perception",
            ('simulation', 'platform', 'robot'): "Simulation-Platforms",
            ('physics', 'engine', 'robot'): "Simulation-Platforms",
            ('digital', 'twin', 'robot'): "Simulation-Platforms",
            ('synthetic', 'data', 'robot'): "Simulation-Platforms",
            ('embodied', 'theory'): "Fundamental-Theory",
            ('embodied', 'intelligence'): "Fundamental-Theory",
            ('control', 'theory', 'robot'): "Fundamental-Theory",
            ('cognitive', 'model', 'robot'): "Fundamental-Theory",
            ('foundation', 'model', 'robot'): "Fundamental-Theory",
            ('world', 'model', 'robot'): "Fundamental-Theory"
        }

        try:
            # 特殊论文类型的直接分类
            if ('adaptive motion optimization' in combined_text or 'amo' in combined_text) and ('humanoid' in combined_text or 'whole-body' in combined_text):
                return "Motion-Planning"

            if (('omnih2o' in combined_text or 'human-to-humanoid' in combined_text) and
                ('teleoperation' in combined_text or 'whole-body' in combined_text)):
                # 如果包含强化学习相关内容，则归入强化学习类别
                if 'reinforcement learning' in combined_text or 'rl' in combined_text:
                    return "Robot-Learning-and-Reinforcement-Learning"
                # 否则归入运动规划
                return "Motion-Planning"

            # 特殊情况处理：对于"Real-time Robot Xxx Xxx"类型的论文
            if 'real-time robot' in combined_text or 'realtime robot' in combined_text:
                if any(kw in combined_text for kw in ['motion', 'trajectory', 'path', 'locomotion']):
                    return "Motion-Planning"
                elif any(kw in combined_text for kw in ['perception', 'detection', 'recognition', 'slam']):
                    return "Environment-Perception"

            # 特殊情况处理：对于机器狗、人形机器人等特定机器人类型
            quadruped_terms = ['quadruped robot', 'robot dog', 'go1', 'anymal', 'spot', 'laikago', 'aliengo', 'a1', 'mini cheetah']
            humanoid_terms = ['humanoid robot', 'atlas', 'digit', 'cassie', 'nao', 'pepper', 'talos', 'romeo', 'valkyrie', 'asimo', 'icub']

            if any(term in combined_text for term in quadruped_terms):
                if any(term in combined_text for term in ['reinforcement learning', 'rl', 'policy learning']):
                    return "Robot-Learning-and-Reinforcement-Learning"
                elif any(term in combined_text for term in ['motion', 'control', 'locomotion', 'planning']):
                    return "Motion-Planning"

            if any(term in combined_text for term in humanoid_terms):
                if any(term in combined_text for term in ['reinforcement learning', 'rl', 'policy learning']):
                    return "Robot-Learning-and-Reinforcement-Learning"
                elif any(term in combined_text for term in ['motion', 'control', 'locomotion', 'planning']):
                    return "Motion-Planning"
                elif any(term in combined_text for term in ['interaction', 'communication', 'teleoperation']):
                    return "Multimodal-Interaction"

            # 特殊关键词组合检查
            for combo, category in special_combination_categories.items():
                if all(kw in combined_text for kw in combo):
                    return category

            # 使用加权评分系统进行分类
            category_scores = {}
            for category, keywords in category_core_keywords.items():
                score = 0
                matched_keywords = []

                for keyword, weight in keywords.items():
                    if keyword in combined_text:
                        score += weight
                        matched_keywords.append(keyword)

                    # 如果关键词出现在标题中，额外加分
                    if keyword in title.lower():
                        score += weight//2  # 额外加一半的权重

                category_scores[category] = {
                    'score': score,
                    'matched_keywords': matched_keywords
                }

            # 返回得分最高的类别，如果最高分为0，返回None
            best_category = max(category_scores.items(), key=lambda x: x[1]['score'])
            if best_category[1]['score'] > 0:
                return best_category[0]

            # 如果没有匹配到任何关键词，根据标题进行简单分类
            title_lower = title.lower()
            if any(kw in title_lower for kw in ['motion', 'trajectory', 'path', 'control', 'locomotion']):
                return "Motion-Planning"
            elif any(kw in title_lower for kw in ['task', 'planning', 'schedule', 'decomposition']):
                return "Task-Planning"
            elif any(kw in title_lower for kw in ['reinforcement', 'learning', 'policy', 'rl', 'skill']):
                return "Robot-Learning-and-Reinforcement-Learning"
            elif any(kw in title_lower for kw in ['interaction', 'teleoperation', 'human-robot', 'communication']):
                return "Multimodal-Interaction"
            elif any(kw in title_lower for kw in ['perception', 'slam', 'detection', 'recognition', 'segmentation']):
                return "Environment-Perception"
            elif any(kw in title_lower for kw in ['simulation', 'simulator', 'environment', 'platform', 'benchmark']):
                return "Simulation-Platforms"
            elif any(kw in title_lower for kw in ['theory', 'intelligence', 'embodied', 'cognitive', 'foundation']):
                return "Fundamental-Theory"

        except Exception as e:
            logger.error(f"确定论文类别时出错: {str(e)}")
            logger.error(f"标题: {title}")
            logger.error(traceback.format_exc())

        # 如果无法确定，返回None
        return None

    def get_daily_papers(self, category, query, max_results=500, days=None):
        """
        获取每日论文，使用官方Client API替代旧的Search接口
        添加更精细的相关性检测和分类

        Args:
            category: 论文类别
            query: 搜索查询
            max_results: 最大返回结果数
            days: 如果提供，只返回最近days天内的论文
        """
        papers = []
        try:
            logger.info(f"开始获取 {category} 类别的论文...")

            # 构建更精细的查询
            basic_query = self.categories[category]

            # 添加日期筛选，进行多次尝试以确保获取最新论文
            date_ranges = []
            if days:
                # 主日期范围 - 从过去days天到现在
                today = datetime.now()
                from_date = today - timedelta(days=days)

                # 按照arxiv API要求的格式构建日期范围：[YYYYMMDDTTTT+TO+YYYYMMDDTTTT]
                from_date_str = from_date.strftime('%Y%m%d0000')
                to_date_str = today.strftime('%Y%m%d2359')

                # 构建日期范围列表，包括完整范围以及更短的最近时间段
                # 这样即使最近论文很多，也会确保最新的论文被获取到
                date_ranges.append({
                    "filter": f" AND submittedDate:[{from_date_str}+TO+{to_date_str}]",
                    "description": f"完整{days}天日期范围"
                })

                # 添加最近7天的范围，确保最新论文优先获取
                if days > 7:
                    recent_date = today - timedelta(days=7)
                    recent_date_str = recent_date.strftime('%Y%m%d0000')
                    date_ranges.append({
                        "filter": f" AND submittedDate:[{recent_date_str}+TO+{to_date_str}]",
                        "description": "最近7天日期范围"
                    })

                # 添加最近14天的范围
                if days > 14:
                    recent_date = today - timedelta(days=14)
                    recent_date_str = recent_date.strftime('%Y%m%d0000')
                    date_ranges.append({
                        "filter": f" AND submittedDate:[{recent_date_str}+TO+{to_date_str}]",
                        "description": "最近14天日期范围"
                    })
            else:
                # 如果未指定天数，默认尝试获取最近30天的论文
                today = datetime.now()
                from_date = today - timedelta(days=30)
                from_date_str = from_date.strftime('%Y%m%d0000')
                to_date_str = today.strftime('%Y%m%d2359')
                date_ranges.append({
                    "filter": f" AND submittedDate:[{from_date_str}+TO+{to_date_str}]",
                    "description": "默认30天日期范围"
                })

            # 创建客户端，增加重试次数和延迟以应对API限制
            client = arxiv.Client(
                page_size=100,
                delay_seconds=3,
                num_retries=5
            )

            # 记录所有获取到的论文的ID，避免重复
            found_paper_ids = set()

            # 对每个日期范围进行查询，合并结果
            for date_range in date_ranges:
                date_filter = date_range["filter"]
                full_query = basic_query + date_filter

                logger.info(f"尝试使用{date_range['description']}查询: {full_query}")

                # 构建查询对象
                search_query = arxiv.Search(
                    query=full_query,
                    max_results=max_results,
                    sort_by=arxiv.SortCriterion.SubmittedDate
                )

                try:
                    # 获取结果
                    results = list(client.results(search_query))
                    logger.info(f"使用{date_range['description']}从ArXiv获取到 {len(results)} 篇论文")

                    # 输出最新5篇论文的信息进行调试
                    if results:
                        logger.info(f"{date_range['description']}最近论文示例:")
                        for i, result in enumerate(results[:5]):
                            logger.info(f"  论文 {i+1}: {result.title} (发布日期: {result.published.date()})")

                    # 处理获取到的论文
                    for result in results:
                        try:
                            paper_id = result.get_short_id()

                            # 检查是否已经处理过这篇论文
                            if paper_id in found_paper_ids:
                                continue

                            # 添加到已处理集合
                            found_paper_ids.add(paper_id)

                            # 检查是否已存在
                            if any(paper["title"] == result.title for paper in self.existing_papers[category]):
                                logger.debug(f"论文已存在，跳过: {result.title}")
                                continue

                            # 获取标题和摘要，用于相关性检查
                            title = result.title
                            abstract = result.summary

                            # 输出特别关注的论文信息（调试用）
                            if any(keyword in title.lower() for keyword in ['adaptive motion', 'hyper-dexterous', 'amo:', 'parkour']):
                                logger.info(f"找到潜在重要论文: {title}")
                                logger.info(f"  发布日期: {result.published.date()}")
                                logger.info(f"  ID: {paper_id}")

                            # 进行相关性评估
                            relevance_assessment = self.assess_paper_relevance(title, abstract, category)

                            # 如果不相关，跳过
                            if not relevance_assessment["is_relevant"]:
                                logger.debug(f"论文不相关，跳过: {title}")
                                logger.debug(f"  相关性分数: {relevance_assessment['score']}")
                                logger.debug(f"  原因: {', '.join(relevance_assessment['reasons'][:3])}")
                                continue

                            # 在相关的情况下继续处理
                            relevance_score = relevance_assessment["score"]
                            is_special_paper = relevance_assessment["is_special_paper"]

                            # 获取代码链接
                            code_url = self.get_paper_info(paper_id)

                            # 尝试识别标签
                            tag = self.identify_tag(category, title, abstract)

                            # 如果标题中有冒号，且没有自动识别出标签，尝试提取前缀作为标签
                            if not tag and ":" in title:
                                prefix = title.split(":")[0].strip()
                                # 只有当前缀较短时才使用它作为标签
                                if len(prefix) < 20:
                                    tag = prefix

                            # 确定论文的最佳分类类别
                            best_category = self.determine_paper_category(title, abstract)
                            category_switched = False

                            # 如果该论文被确定为更适合其他类别，标记它
                            if best_category and best_category != category:
                                category_switched = True

                            # 创建论文信息对象
                            paper_info = {
                                "date": str(result.published.date()),
                                "title": title,
                                "tag": tag,
                                "authors": [author.name for author in result.authors],
                                "abstract": abstract,
                                "pdf_url": result.entry_id,
                                "code_url": code_url if code_url else "⚠️",
                                "rating": "⭐️⭐️⭐️",  # 默认评分
                                "has_code": code_url is not None,
                                "manual": False,  # 标记为自动更新
                                "relevance_score": relevance_score,  # 记录相关性分数
                                "is_special_paper": is_special_paper,  # 标记是否为特殊论文
                                "relevance_reasons": relevance_assessment["reasons"][:3],  # 记录相关性的主要原因
                                "best_category": best_category,  # 记录最佳分类
                                "category_switched": category_switched  # 标记是否需要重新分类
                            }
                            papers.append(paper_info)

                            # 记录高相关性论文（仅用于调试）
                            if relevance_score > 15:  # 高相关性论文
                                logger.info(f"高相关性论文: {title}")
                                logger.info(f"  相关性分数: {relevance_score}")
                                logger.info(f"  相关性原因: {', '.join(relevance_assessment['reasons'][:3])}")
                        except Exception as e:
                            logger.error(f"处理论文 {result.title if hasattr(result, 'title') else '未知标题'} 时发生错误: {str(e)}")
                            logger.error(traceback.format_exc())
                            continue

                except arxiv.UnexpectedEmptyPageError as e:
                    logger.warning(f"{date_range['description']}查询时ArXiv API返回空页面错误: {str(e)}")
                except Exception as e:
                    logger.error(f"{date_range['description']}查询时发生错误: {str(e)}")
                    logger.error(traceback.format_exc())

            # 如果没有找到任何论文，尝试直接通过直接关键词搜索
            if not papers:
                logger.info("没有找到任何论文，尝试无日期限制的关键词搜索...")

                # 使用更宽泛的关键词搜索
                try:
                    search_query = arxiv.Search(
                        query=basic_query,
                        max_results=50,
                        sort_by=arxiv.SortCriterion.SubmittedDate
                    )

                    results = list(client.results(search_query))
                    logger.info(f"无日期限制搜索找到 {len(results)} 篇论文")

                    # 处理论文（使用与上面相同的逻辑，但仅处理最近30天的论文）
                    cutoff_date = datetime.now() - timedelta(days=30)
                    for result in results:
                        try:
                            # 仅处理最近30天的论文
                            if result.published.date() < cutoff_date.date():
                                continue

                            paper_id = result.get_short_id()

                            # 检查是否已经处理过这篇论文
                            if paper_id in found_paper_ids:
                                continue

                            # 添加到已处理集合
                            found_paper_ids.add(paper_id)

                            # 检查是否已存在
                            if any(paper["title"] == result.title for paper in self.existing_papers[category]):
                                logger.debug(f"论文已存在，跳过: {result.title}")
                                continue

                            # 获取标题和摘要，用于相关性检查
                            title = result.title
                            abstract = result.summary

                            # 输出特别关注的论文信息（调试用）
                            if any(keyword in title.lower() for keyword in ['adaptive motion', 'hyper-dexterous', 'amo:', 'parkour']):
                                logger.info(f"找到潜在重要论文: {title}")
                                logger.info(f"  发布日期: {result.published.date()}")
                                logger.info(f"  ID: {paper_id}")

                            # 进行相关性评估
                            relevance_assessment = self.assess_paper_relevance(title, abstract, category)

                            # 如果不相关，跳过
                            if not relevance_assessment["is_relevant"]:
                                logger.debug(f"论文不相关，跳过: {title}")
                                logger.debug(f"  相关性分数: {relevance_assessment['score']}")
                                logger.debug(f"  原因: {', '.join(relevance_assessment['reasons'][:3])}")
                                continue

                            # 在相关的情况下继续处理
                            relevance_score = relevance_assessment["score"]
                            is_special_paper = relevance_assessment["is_special_paper"]

                            # 获取代码链接
                            code_url = self.get_paper_info(paper_id)

                            # 尝试识别标签
                            tag = self.identify_tag(category, title, abstract)

                            # 如果标题中有冒号，且没有自动识别出标签，尝试提取前缀作为标签
                            if not tag and ":" in title:
                                prefix = title.split(":")[0].strip()
                                # 只有当前缀较短时才使用它作为标签
                                if len(prefix) < 20:
                                    tag = prefix

                            # 确定论文的最佳分类类别
                            best_category = self.determine_paper_category(title, abstract)
                            category_switched = False

                            # 如果该论文被确定为更适合其他类别，标记它
                            if best_category and best_category != category:
                                category_switched = True

                            # 创建论文信息对象
                            paper_info = {
                                "date": str(result.published.date()),
                                "title": title,
                                "tag": tag,
                                "authors": [author.name for author in result.authors],
                                "abstract": abstract,
                                "pdf_url": result.entry_id,
                                "code_url": code_url if code_url else "⚠️",
                                "rating": "⭐️⭐️⭐️",  # 默认评分
                                "has_code": code_url is not None,
                                "manual": False,  # 标记为自动更新
                                "relevance_score": relevance_score,  # 记录相关性分数
                                "is_special_paper": is_special_paper,  # 标记是否为特殊论文
                                "relevance_reasons": relevance_assessment["reasons"][:3],  # 记录相关性的主要原因
                                "best_category": best_category,  # 记录最佳分类
                                "category_switched": category_switched  # 标记是否需要重新分类
                            }
                            papers.append(paper_info)

                            # 记录高相关性论文（仅用于调试）
                            if relevance_score > 15:  # 高相关性论文
                                logger.info(f"高相关性论文: {title}")
                                logger.info(f"  相关性分数: {relevance_score}")
                                logger.info(f"  相关性原因: {', '.join(relevance_assessment['reasons'][:3])}")
                        except Exception as e:
                            logger.error(f"处理论文 {result.title if hasattr(result, 'title') else '未知标题'} 时发生错误: {str(e)}")
                            logger.error(traceback.format_exc())
                            continue
                except Exception as e:
                    logger.error(f"无日期限制搜索时发生错误: {str(e)}")
                    logger.error(traceback.format_exc())

            # 按相关性分数排序，确保最相关的论文排在前面
            papers.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

            # 如果论文数量过多，只保留得分最高的一部分
            max_papers_per_category = 20  # 每个类别最多保留的论文数
            if len(papers) > max_papers_per_category:
                papers = papers[:max_papers_per_category]

            logger.info(f"类别 {category} 处理完成，找到 {len(papers)} 篇相关论文")

        except Exception as e:
            logger.error(f"处理{category}时发生错误: {str(e)}")
            logger.error(traceback.format_exc())

        return papers

    def update_category_readme(self, category, new_papers):
        """
        更新分类目录的README文件
        修复更新逻辑，确保新论文添加在现有论文之后而不是覆盖它们
        """
        # 确保目录存在
        self.ensure_directory_exists(category)

        # 获取现有的手动添加论文
        existing_manual_papers = self.manually_added_papers.get(category, [])

        # 获取现有的自动更新论文（从self.existing_papers中获取非手动添加的论文）
        existing_auto_papers = [p for p in self.existing_papers.get(category, []) if not p.get("manual", False)]

        # 过滤掉已经存在于手动添加论文或自动更新论文中的新论文
        filtered_new_papers = []
        existing_titles = set(p['title'] for p in existing_manual_papers + existing_auto_papers)

        for paper in new_papers:
            if paper['title'] not in existing_titles:
                filtered_new_papers.append(paper)
                existing_titles.add(paper['title'])  # 添加到已存在集合，避免重复

        # 合并所有自动更新的论文（保留现有的自动更新论文，并添加新的）
        all_auto_papers = existing_auto_papers + filtered_new_papers

        # 按日期排序
        existing_manual_papers.sort(key=lambda x: x['date'], reverse=True)
        all_auto_papers.sort(key=lambda x: x['date'], reverse=True)

        # 定义各主题的简介和主要内容
        category_intros = {
            "Motion-Planning": {
                "en": "This directory collects papers and code implementations related to motion planning in embodied AI.",
                "cn": "本目录收集了具身智能中与运动规划相关的论文和代码实现。"
            },
            "Task-Planning": {
                "en": "This directory collects papers and code implementations related to task planning in embodied AI.",
                "cn": "本目录收集了具身智能中与任务规划相关的论文和代码实现。"
            },
            "Simulation-Platforms": {
                "en": "This directory collects papers and code implementations related to simulation platforms in embodied AI.",
                "cn": "本目录收集了具身智能中与仿真平台相关的论文和代码实现。"
            },
            "Robot-Learning-and-Reinforcement-Learning": {
                "en": "This directory collects papers and code implementations related to robot learning and reinforcement learning in embodied AI.",
                "cn": "本目录收集了具身智能中与机器人学习和强化学习相关的论文和代码实现。"
            },
            "Multimodal-Interaction": {
                "en": "This directory collects papers and code implementations related to multimodal interaction in embodied AI.",
                "cn": "本目录收集了具身智能中与多模态交互相关的论文和代码实现。"
            },
            "Environment-Perception": {
                "en": "This directory collects papers and code implementations related to environment perception in embodied AI.",
                "cn": "本目录收集了具身智能中与环境感知相关的论文和代码实现。"
            },
            "Fundamental-Theory": {
                "en": "This directory collects papers and code implementations related to fundamental theory in embodied AI.",
                "cn": "本目录收集了具身智能中与基础理论相关的论文和代码实现。"
            }
        }

        # 定义各主题的主要内容
        category_contents = {
            "Motion-Planning": {
                "en": [
                    "Dynamic Motion Planning",
                    "Whole-Body Motion Planning",
                    "Trajectory Optimization",
                    "Collision Avoidance",
                    "Real-time Planning",
                    "Humanoid Robot Control"
                ],
                "cn": [
                    "动态运动规划",
                    "全身运动规划",
                    "轨迹优化",
                    "碰撞避免",
                    "实时规划",
                    "人形机器人控制"
                ]
            },
            "Task-Planning": {
                "en": [
                    "High-level Task Planning",
                    "Hierarchical Planning",
                    "Task and Motion Planning (TAMP)",
                    "Learning-based Planning",
                    "Multi-agent Planning"
                ],
                "cn": [
                    "高层任务规划",
                    "分层规划",
                    "任务与运动规划(TAMP)",
                    "基于学习的规划",
                    "多智能体规划"
                ]
            },
            "Simulation-Platforms": {
                "en": [
                    "Physics Simulators",
                    "Robot Simulation Environments",
                    "Learning Environments",
                    "Benchmarking Platforms",
                    "Digital Twins",
                    "Synthetic Data Generation"
                ],
                "cn": [
                    "物理仿真器",
                    "机器人仿真环境",
                    "学习环境",
                    "基准测试平台",
                    "数字孪生",
                    "合成数据生成"
                ]
            },
            "Robot-Learning-and-Reinforcement-Learning": {
                "en": [
                    "Foundational Works",
                    "Imitation Learning",
                    "Skill Learning",
                    "Multi-task and Transfer Learning",
                    "Advanced Policy Learning",
                    "Sim-to-Real Transfer",
                    "Cross-Morphology Learning"
                ],
                "cn": [
                    "奠基性工作",
                    "模仿学习",
                    "技能学习",
                    "多任务与迁移学习",
                    "高级策略学习",
                    "Sim-to-Real迁移",
                    "跨形态学习"
                ]
            },
            "Multimodal-Interaction": {
                "en": [
                    "Human-Robot Interaction",
                    "Natural Language Processing for Robots",
                    "Gesture Recognition and Understanding",
                    "Multi-modal Learning and Fusion",
                    "Social Robotics",
                    "Robot Reasoning and Memory"
                ],
                "cn": [
                    "人机交互",
                    "机器人自然语言处理",
                    "手势识别与理解",
                    "多模态学习与融合",
                    "社交机器人",
                    "机器人推理与记忆"
                ]
            },
            "Environment-Perception": {
                "en": [
                    "Visual Perception",
                    "Terrain Understanding",
                    "SLAM and Mapping",
                    "Scene Understanding",
                    "Sensor Fusion"
                ],
                "cn": [
                    "视觉感知",
                    "地形理解",
                    "SLAM与地图构建",
                    "场景理解",
                    "传感器融合"
                ]
            },
            "Fundamental-Theory": {
                "en": [
                    "Cognitive Foundations of Embodied Intelligence",
                    "Computational Models of Embodied Intelligence",
                    "Learning Theory in Embodied Intelligence",
                    "Evaluation Methods for Embodied Intelligence"
                ],
                "cn": [
                    "具身智能的认知基础",
                    "具身智能的计算模型",
                    "具身智能的学习理论",
                    "具身智能的评估方法"
                ]
            }
        }

        # 修改代码链接格式
        def format_code_link(code_url):
            if code_url == "⚠️":
                return "⚠️"
            else:
                # 提取代码名称
                if "github.com" in code_url:
                    # 从GitHub URL获取项目名
                    parts = code_url.split("/")
                    if len(parts) >= 5:
                        code_name = f"{parts[-2]}/{parts[-1]}"
                    else:
                        code_name = parts[-1]
                else:
                    # 如果不是GitHub，使用链接最后部分
                    code_name = code_url.split("/")[-1]

                # 清理可能的结尾括号
                code_name = code_name.replace(")", "")

                # 返回标准的 Markdown 链接格式
                return f"[{code_name}]({code_url})"

        try:
            # 更新英文README
            en_file = f"{category}/README.md"
            if os.path.exists(en_file):
                with open(en_file, "r", encoding="utf-8") as f:
                    content = f.read()

                    # 提取标题和语言切换部分
                    title_match = re.match(r'(#.*?\n\n>.*?\n\n)', content, re.DOTALL)
                    if title_match:
                        title_section = title_match.group(1)
                        en_content = f"{title_section}{category_intros[category]['en']}\n\n"
                        en_content += "## Main Contents\n\n"
                        for content_item in category_contents[category]['en']:
                            en_content += f"- {content_item}\n"
                        en_content += "\n"

                        # 添加手动添加的论文
                        en_content += "## Manually Added Papers\n\n"
                        if existing_manual_papers:
                            en_content += "|Date|Title|Paper|Code|Rating|\n"
                            en_content += "|:---:|:---:|:---:|:---:|:---:|\n"
                            for paper in existing_manual_papers:
                                code_link = format_code_link(paper['code_url'])
                                en_content += f"|{paper['date']}|{paper['title']}|[[pdf]]({paper['pdf_url']})|{code_link}|{paper['rating']}|\n"
                        en_content += "\n"

                        # 添加自动更新的论文
                        en_content += "## Auto-Updated Papers\n\n"
                        if all_auto_papers:
                            en_content += "|Date|Title|Paper|Code|Rating|\n"
                            en_content += "|:---:|:---:|:---:|:---:|:---:|\n"
                            for paper in all_auto_papers:
                                # 如果有标签，添加到标题前
                                title_with_tag = f"[{paper['tag']}] {paper['title']}" if paper.get('tag') else paper['title']
                                code_link = format_code_link(paper['code_url'])
                                en_content += f"|{paper['date']}|{title_with_tag}|[[pdf]]({paper['pdf_url']})|{code_link}|{paper['rating']}|\n"
                        en_content += "\n"

                        # 添加统计信息
                        total_papers = len(existing_manual_papers) + len(all_auto_papers)
                        code_implementations = sum(1 for p in existing_manual_papers + all_auto_papers if p['code_url'] != "⚠️")
                        en_content += "## 📊 Statistics\n\n"
                        en_content += f"- Total Papers: {total_papers}\n"
                        en_content += f"- Code Implementations: {code_implementations}\n"
                        en_content += f"- Last Updated: {datetime.now().strftime('%B %Y')}\n"

                        # 写入英文README
                        with open(en_file, "w", encoding="utf-8") as f:
                            f.write(en_content)

            # 更新中文README
            cn_file = f"{category}/README_CN.md"
            if os.path.exists(cn_file):
                with open(cn_file, "r", encoding="utf-8") as f:
                    content = f.read()

                    # 提取标题和语言切换部分
                    title_match = re.match(r'(#.*?\n\n>.*?\n\n)', content, re.DOTALL)
                    if title_match:
                        title_section = title_match.group(1)
                        cn_content = f"{title_section}{category_intros[category]['cn']}\n\n"
                        cn_content += "## 主要内容\n\n"
                        for content_item in category_contents[category]['cn']:
                            cn_content += f"- {content_item}\n"
                        cn_content += "\n"

                        # 添加手动添加的论文
                        cn_content += "## 手动添加的论文\n\n"
                        if existing_manual_papers:
                            cn_content += "|日期|标题|论文|代码|推荐指数|\n"
                            cn_content += "|:---:|:---:|:---:|:---:|:---:|\n"
                            for paper in existing_manual_papers:
                                code_link = format_code_link(paper['code_url'])
                                cn_content += f"|{paper['date']}|{paper['title']}|[[pdf]]({paper['pdf_url']})|{code_link}|{paper['rating']}|\n"
                        cn_content += "\n"

                        # 添加自动更新的论文
                        cn_content += "## 自动更新的论文\n\n"
                        if all_auto_papers:
                            cn_content += "|日期|标题|论文|代码|推荐指数|\n"
                            cn_content += "|:---:|:---:|:---:|:---:|:---:|\n"
                            for paper in all_auto_papers:
                                # 如果有标签，添加到标题前
                                title_with_tag = f"[{paper['tag']}] {paper['title']}" if paper.get('tag') else paper['title']
                                code_link = format_code_link(paper['code_url'])
                                cn_content += f"|{paper['date']}|{title_with_tag}|[[pdf]]({paper['pdf_url']})|{code_link}|{paper['rating']}|\n"
                        cn_content += "\n"

                        # 添加统计信息
                        total_papers = len(existing_manual_papers) + len(all_auto_papers)
                        code_implementations = sum(1 for p in existing_manual_papers + all_auto_papers if p['code_url'] != "⚠️")
                        cn_content += "## 📊 统计\n\n"
                        cn_content += f"- 论文总数：{total_papers}篇\n"
                        cn_content += f"- 代码实现：{code_implementations}个\n"
                        cn_content += f"- 最后更新：{datetime.now().strftime('%Y年%m月')}\n"

                        # 写入中文README
                        with open(cn_file, "w", encoding="utf-8") as f:
                            f.write(cn_content)

            # 更新现有论文列表 - 记录合并后的论文列表，保证累加而不是覆盖
            self.existing_papers[category] = existing_manual_papers + all_auto_papers
            logger.info(f"类别 {category} 的README已更新，包含 {len(existing_manual_papers)} 篇手动添加论文和 {len(all_auto_papers)} 篇自动更新论文")

        except Exception as e:
            logger.error(f"更新类别 {category} 的README时发生错误: {str(e)}")
            logger.error(traceback.format_exc())

    def update_root_readme(self):
        """更新根目录的README文件，更新统计信息"""
        try:
            total_papers = 0
            total_codes = 0

            # 统计所有分类的论文和代码数量
            for category in self.categories.keys():
                if os.path.exists(f"{category}/README.md"):
                    with open(f"{category}/README.md", "r", encoding="utf-8") as f:
                        content = f.read()
                        # 计算论文数量（减去表头）
                        papers = len(re.findall(r'\|.*?\|.*?\|.*?\|.*?\|.*?\|', content)) - 1
                        # 计算有代码实现的论文数量
                        codes = len(re.findall(r'\[\[(?!⚠️).*?\]\]', content))
                        total_papers += papers
                        total_codes += codes

            # 读取现有的英文README内容
            with open("README.md", "r", encoding="utf-8") as f:
                content = f.read()

            # 只更新统计信息部分
            new_content = re.sub(
                r'## Statistics\n\n- Total Papers: \d+\n- Code Implementations: \d+',
                f'## Statistics\n\n- Total Papers: {total_papers}\n- Code Implementations: {total_codes}',
                content
            )

            # 写入更新后的内容
            with open("README.md", "w", encoding="utf-8") as f:
                f.write(new_content)

            # 读取现有的中文README内容
            with open("README_CN.md", "r", encoding="utf-8") as f:
                content = f.read()

            # 只更新统计信息部分
            new_content = re.sub(
                r'## 📊统计\n\n- 论文总数：\d+篇\n- 代码实现：\d+个',
                f'## 📊统计\n\n- 论文总数：{total_papers}篇\n- 代码实现：{total_codes}个',
                content
            )

            # 写入更新后的内容
            with open("README_CN.md", "w", encoding="utf-8") as f:
                f.write(new_content)

            logger.info(f"根目录README更新完成，总论文数：{total_papers}，代码实现：{total_codes}")
        except Exception as e:
            logger.error(f"更新根目录README时出错: {str(e)}")
            logger.error(traceback.format_exc())

    def run(self):
        """运行更新程序，完成论文采集、智能分类和更新"""
        logger.info("开始更新论文列表...")

        # 使用初始化时设置的日期筛选参数
        logger.info(f"筛选最近 {self.days_filter} 天内发表的论文")

        # 第一步：获取各类别的论文
        all_papers = {}
        for category, query in self.keywords.items():
            try:
                logger.info(f"\n处理分类: {category}")
                logger.info(f"使用查询: {query}")
                papers = self.get_daily_papers(category, query, days=self.days_filter)
                if papers:
                    logger.info(f"找到 {len(papers)} 篇新论文")
                    all_papers[category] = papers
                else:
                    logger.info("没有找到新论文")
                    all_papers[category] = []
            except Exception as e:
                logger.error(f"处理分类 {category} 时出错: {str(e)}")
                logger.error(traceback.format_exc())
                logger.warning("跳过此分类，继续处理其他分类...")
                all_papers[category] = []

        # 第二步：检查论文分类并重新归类
        try:
            logger.info("\n开始论文智能重分类...")
            reclassified_papers = {}
            for category in self.categories.keys():
                reclassified_papers[category] = []

            # 初始化一个集合来跟踪已处理的论文标题，避免重复
            processed_titles = set()

            for category, papers in all_papers.items():
                for paper in papers:
                    try:
                        # 如果已经处理过这篇论文，跳过
                        if paper["title"] in processed_titles:
                            continue

                        # 添加到已处理集合
                        processed_titles.add(paper["title"])

                        # 确定论文应该归入的类别
                        title = paper["title"]
                        abstract = paper.get("abstract", "")
                        best_category = self.determine_paper_category(title, abstract)

                        # 如果不能确定类别或者最佳类别就是当前类别，则保持不变
                        if not best_category or best_category == category:
                            reclassified_papers[category].append(paper)
                        else:
                            # 如果论文应该归入其他类别，将其移动到正确的类别
                            logger.info(f"论文 '{title}' 从 {category} 移动到 {best_category}")
                            # 记录原始类别，以便以后参考
                            paper["original_category"] = category
                            reclassified_papers[best_category].append(paper)
                    except Exception as e:
                        logger.error(f"重新分类论文 '{paper.get('title', '未知标题')}' 时出错: {str(e)}")
                        logger.error(traceback.format_exc())
                        # 发生错误时，保留在原始类别中
                        reclassified_papers[category].append(paper)
        except Exception as e:
            logger.error(f"在重新分类论文时出错: {str(e)}")
            logger.error(traceback.format_exc())
            logger.warning("继续使用现有分类...")
            # 出现错误时，使用原始分类
            reclassified_papers = all_papers

        # 第三步：更新各个类别的README文件
        for category, papers in reclassified_papers.items():
            try:
                if papers:
                    logger.info(f"\n更新 {category} 的README（{len(papers)} 篇论文）")
                    self.update_category_readme(category, papers)
                else:
                    logger.info(f"\n{category} 没有新论文需要更新")
            except Exception as e:
                logger.error(f"更新 {category} 的README时出错: {str(e)}")
                logger.error(traceback.format_exc())
                logger.warning("跳过此类别的README更新...")

        # 第四步：为特殊论文添加额外评分
        try:
            self.update_special_papers_ratings()
        except Exception as e:
            logger.error(f"更新特殊论文评分时出错: {str(e)}")
            logger.error(traceback.format_exc())
            logger.warning("跳过特殊论文评分更新...")

        # 更新根目录README
        try:
            self.update_root_readme()
            logger.info("\n更新完成！")
        except Exception as e:
            logger.error(f"更新根目录README时出错: {str(e)}")
            logger.error(traceback.format_exc())
            logger.warning("根目录README更新失败。")
            logger.info("\n部分更新完成！")

        # 输出统计信息
        try:
            total_papers = sum(len(papers) for category, papers in self.existing_papers.items())
            total_new_papers = sum(len(papers) for category, papers in reclassified_papers.items())
            total_code_implementations = sum(sum(1 for p in papers if p.get('code_url') != "⚠️")
                                         for category, papers in self.existing_papers.items())

            logger.info(f"\n====== 更新统计 ======")
            logger.info(f"总论文数: {total_papers}篇")
            logger.info(f"新增论文: {total_new_papers}篇")
            logger.info(f"代码实现: {total_code_implementations}个")
            logger.info(f"更新完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"========================")
        except Exception as e:
            logger.error(f"生成统计数据时出错: {str(e)}")
            logger.error(traceback.format_exc())

    def update_special_papers_ratings(self):
        """为特殊论文添加额外评分"""
        logger.info("开始更新特殊论文评分...")

        # 特殊论文关键词及对应评分 - 更全面的关键词列表
        special_paper_keywords = {
            # 顶级论文评分关键词
            'adaptive motion optimization': '⭐️⭐️⭐️⭐️⭐️',
            'amo': '⭐️⭐️⭐️⭐️⭐️',
            'human-to-humanoid': '⭐️⭐️⭐️⭐️⭐️',
            'omnih2o': '⭐️⭐️⭐️⭐️⭐️',
            'dexterous humanoid': '⭐️⭐️⭐️⭐️⭐️',
            'hyper-dexterous': '⭐️⭐️⭐️⭐️⭐️',
            'parkour robot': '⭐️⭐️⭐️⭐️⭐️',
            'agile humanoid': '⭐️⭐️⭐️⭐️⭐️',
            'humanoid backflip': '⭐️⭐️⭐️⭐️⭐️',
            'acrobatic': '⭐️⭐️⭐️⭐️⭐️',

            # 高水平评分关键词
            'agile robot': '⭐️⭐️⭐️⭐️',
            'atlas': '⭐️⭐️⭐️⭐️',
            'digit': '⭐️⭐️⭐️⭐️',
            'cassie': '⭐️⭐️⭐️⭐️',
            'anymal': '⭐️⭐️⭐️⭐️',
            'spot': '⭐️⭐️⭐️⭐️',
            'go1': '⭐️⭐️⭐️⭐️',
            'tesla optimus': '⭐️⭐️⭐️⭐️',
            'figure 01': '⭐️⭐️⭐️⭐️',
            'whole-body control': '⭐️⭐️⭐️⭐️',
            'dynamic locomotion': '⭐️⭐️⭐️⭐️',
            'legged': '⭐️⭐️⭐️',
            'quadruped': '⭐️⭐️⭐️',

            # 特殊类别
            'diffusion': '⭐️⭐️⭐️',
            'transformer': '⭐️⭐️⭐️',
            'vision language': '⭐️⭐️⭐️',
            'embodied ai': '⭐️⭐️⭐️⭐️',
            'foundation model': '⭐️⭐️⭐️⭐️',
            'embodied intelligence': '⭐️⭐️⭐️⭐️',

            # 特殊公司/机构
            'deepmind': '⭐️⭐️⭐️⭐️',
            'nvidia': '⭐️⭐️⭐️⭐️',
            'berkeley': '⭐️⭐️⭐️⭐️',
            'stanford': '⭐️⭐️⭐️⭐️',
            'mit': '⭐️⭐️⭐️⭐️',
            'cmu': '⭐️⭐️⭐️⭐️',
            'eth zurich': '⭐️⭐️⭐️⭐️',
            'google': '⭐️⭐️⭐️⭐️',
        }

        # 特殊论文类型（可能覆盖上面的关键词评分）
        special_paper_types = {
            # 重要会议/期刊的论文
            'icra': '⭐️⭐️⭐️⭐️',
            'iros': '⭐️⭐️⭐️⭐️',
            'corl': '⭐️⭐️⭐️⭐️',
            'rss': '⭐️⭐️⭐️⭐️⭐️',
            'science robotics': '⭐️⭐️⭐️⭐️⭐️',
            'nature': '⭐️⭐️⭐️⭐️⭐️',
            'science': '⭐️⭐️⭐️⭐️⭐️',
            'icml': '⭐️⭐️⭐️⭐️',
            'nips': '⭐️⭐️⭐️⭐️',
            'neurips': '⭐️⭐️⭐️⭐️',
            'cvpr': '⭐️⭐️⭐️⭐️',
            'iccv': '⭐️⭐️⭐️⭐️',
        }

        # 遍历各个类别下的论文并更新评分
        updated_count = 0
        for category in self.existing_papers.keys():
            for paper in self.existing_papers[category]:
                title = paper.get('title', '').lower()
                abstract = paper.get('abstract', '').lower()

                # 如果是手动添加的论文，保持其评分不变
                if paper.get('manual', False):
                    continue

                # 默认评分为3星
                max_rating = '⭐️⭐️⭐️'

                # 检查特殊论文类型（如顶级会议）
                for type_keyword, type_rating in special_paper_types.items():
                    if type_keyword in title.lower() or type_keyword in abstract.lower():
                        if type_rating > max_rating:
                            max_rating = type_rating
                            logger.debug(f"论文 '{paper['title']}' 属于特殊类型 '{type_keyword}'，评分提升为 {max_rating}")

                # 根据内容关键词检查并更新评分
                for keyword, rating in special_paper_keywords.items():
                    if keyword in title.lower() or keyword in abstract.lower():
                        if rating > max_rating:
                            max_rating = rating
                            logger.debug(f"论文 '{paper['title']}' 包含关键词 '{keyword}'，评分提升为 {max_rating}")

                # 提升有代码的论文评分
                if paper.get('has_code', False) and paper.get('code_url', '') != '⚠️':
                    # 如果有代码且评分低于4星，提升一级
                    if max_rating == '⭐️⭐️⭐️':
                        max_rating = '⭐️⭐️⭐️⭐️'
                        logger.debug(f"论文 '{paper['title']}' 有代码实现，评分提升为 {max_rating}")

                # 根据相关性分数提升评分
                relevance_score = paper.get('relevance_score', 0)
                if relevance_score > 20 and max_rating < '⭐️⭐️⭐️⭐️⭐️':
                    max_rating = '⭐️⭐️⭐️⭐️⭐️'
                    logger.debug(f"论文 '{paper['title']}' 相关性极高 ({relevance_score})，评分提升为 {max_rating}")
                elif relevance_score > 15 and max_rating < '⭐️⭐️⭐️⭐️':
                    max_rating = '⭐️⭐️⭐️⭐️'
                    logger.debug(f"论文 '{paper['title']}' 相关性很高 ({relevance_score})，评分提升为 {max_rating}")

                # 更新论文评分
                if paper.get('rating', '') != max_rating:
                    logger.debug(f"更新论文 '{paper['title']}' 的评分从 {paper.get('rating', '')} 到 {max_rating}")
                    paper['rating'] = max_rating
                    updated_count += 1

        logger.info(f"特殊论文评分更新完成，共更新了 {updated_count} 篇论文的评分")

    def assess_paper_relevance(self, title, abstract, category):
        """
        评估论文与机器人和具身智能的相关性，返回相关性分数和原因
        使用多维度评分系统分析论文标题和摘要内容
        """
        combined_text = (title + " " + abstract).lower()

        # 初始化相关性分数和原因
        relevance_score = 0
        relevance_reasons = []

        # 核心机器人关键词 - 高权重
        core_robot_keywords = {
            'robot': 5, 'embodied': 5, 'humanoid': 4, 'quadruped': 4, 'biped': 4,
            'legged': 4, 'manipulation': 3, 'locomotion': 3, 'teleop': 3, 'teleoperation': 3,
            'gripper': 3, 'dexterous': 4, 'manipulator': 3, 'end-effector': 3
        }

        # 领域特定关键词 - 中等权重
        domain_specific_keywords = {
            'motion planning': 3, 'path planning': 3, 'trajectory optimization': 3,
            'reinforcement learning': 3, 'imitation learning': 3, 'sim2real': 3,
            'whole-body control': 3, 'collision avoidance': 3, 'dynamic motion': 3,
            'task planning': 3, 'manipulation planning': 3, 'perception': 2,
            'slam': 2, 'navigation': 2, 'grasping': 2, 'control': 2, 'parkour': 4,
            'agile motion': 3, 'adaptive control': 3, 'multimodal': 2, 'human-robot': 3,
            'tactile': 2, 'vision-language': 3, 'zero-shot': 3, 'few-shot': 2,
            'model predictive control': 3, 'optimal control': 2, 'kinematics': 2,
            'dynamics': 2, 'impedance control': 3, 'force control': 3, 'visual servoing': 3,
            'sensor fusion': 2, 'deep learning for robotics': 3, 'computer vision for robotics': 3,
            'state estimation': 2, 'motion capture': 2, 'collision detection': 2,
            'physical interaction': 3, 'human-in-the-loop': 3, 'haptic feedback': 3,
            'trajectory planning': 3, 'motion primitives': 3, 'optimization-based control': 3,
            'sampling-based planning': 3, 'contact planning': 3, 'multi-contact planning': 3,
            'dexterous manipulation': 3, 'object grasping': 3, 'robot grasping': 3,
            'terrain traversal': 3, 'terrain understanding': 3, 'legged locomotion': 3,
            'arm manipulation': 3, 'compliant control': 3, 'inverse kinematics': 2,
            'forward kinematics': 2, 'operational space control': 3, 'joint space control': 2,
            'torque control': 2, 'position control': 2, 'velocity control': 2,
            'force/torque sensing': 2, 'depth sensing': 2, 'visual-inertial odometry': 3,
            'lidar odometry': 3, 'simultaneous localization and mapping': 3
        }

        # 机器人硬件和平台 - 专业术语
        robot_hardware_keywords = {
            'atlas': 3, 'spot': 3, 'anymal': 3, 'go1': 3, 'cassie': 3, 'digit': 3,
            'tiago': 3, 'baxter': 3, 'ur5': 3, 'ur10': 3, 'franka': 3, 'panda': 3,
            'kuka': 3, 'abb': 3, 'fanuc': 3, 'pr2': 3, 'fetch': 3, 'youbot': 3,
            'nao': 3, 'pepper': 3, 'icub': 3, 'asimo': 3, 'valkyrie': 3, 'boston dynamics': 3,
            'unitree': 3, 'nvidia': 2, 'omni': 2, 'isaac': 2, 'isaac gym': 3, 'isaac sim': 3,
            'mujoco': 3, 'pybullet': 3, 'gazebo': 3, 'webots': 3, 'rviz': 2, 'ros': 2,
            'ros2': 2, 'robotic operating system': 3, 'openai gym': 2, 'raisim': 3,
            'nvidia omniverse': 3, 'flexiv': 3, 'stretch': 3, 'moma': 2, 'talos': 3,
            'juliette': 3, 'romeo': 3, 'darwin': 3, 'stretch re1': 3, 'hello robot': 3,
            'clearpath': 3, 'jackal': 3, 'husky': 3, 'robotis': 3, 'dynamixel': 3,
            'allegro': 3, 'shadowhand': 3, 'barrett': 3, 'schunk': 3, 'kinova': 3, 'jaco': 3,
            'gen3': 3, 'aloha': 3, 'stretch': 3, 'mobile manipulator': 3, 'laikago': 3,
            'aliengo': 3, 'mini cheetah': 3, 'tello': 2, 'dji': 2, 'crazyflie': 2
        }

        # 机器人算法和框架 - 专业术语
        robot_algorithms = {
            'rrt': 3, 'rapidly-exploring random tree': 3, 'rrt*': 3, 'prm': 3,
            'probabilistic roadmap': 3, 'a*': 3, 'dijkstra': 3, 'wavefront': 3,
            'potential field': 3, 'ddpg': 3, 'ppo': 3, 'trpo': 3, 'sac': 3, 'td3': 3,
            'rl for robotics': 3, 'mpc': 3, 'ilqr': 3, 'ddp': 3, 'differential dynamic programming': 3,
            'trajectory optimization': 3, 'topp': 3, 'toppra': 3, 'chomp': 3, 'stomp': 3,
            'trajopt': 3, 'fabrik': 3, 'ccd': 3, 'cycloid': 3, 'bezier': 3, 'quaternion': 2,
            'jacobian': 3, 'euler-lagrange': 3, 'newton-euler': 3, 'raibert': 3,
            'whole-body control': 3, 'centroidal dynamics': 3, 'zero moment point': 3,
            'zmp': 3, 'capture point': 3, 'divergent component of motion': 3, 'dcm': 3,
            'hierarchical control': 3, 'task-space control': 3, 'null-space projection': 3,
            'virtual model control': 3, 'operational space control': 3, 'hybrid position/force control': 3,
            'finite state machine': 2, 'behavior tree': 2, 'hfsm': 2, 'qp controller': 3,
            'convex optimization': 3, 'humanoid trajectory optimization': 3, 'contact-implicit optimization': 3,
            'contact planning': 3, 'multi-contact planning': 3, 'hrp': 3, 'neural network control': 3,
            'transformer for robotics': 3, 'foundation model for robotics': 3, 'voxel': 2,
            'octree': 2, 'pointcloud': 2, 'keypoint': 2, 'rgb-d': 2, 'inverse kinematics': 3,
            'forward kinematics': 3, 'admittance control': 3, 'impedance control': 3, 'compliance control': 3,
            'pid control': 2, 'soft actor-critic': 3, 'proximal policy optimization': 3
        }

        # 机器人应用场景和任务 - 中低权重
        robot_applications = {
            'industrial robot': 1, 'service robot': 1, 'mobile robot': 1,
            'surgical robot': 1, 'agile robot': 2, 'humanoid robot': 2,
            'social robot': 1, 'collaborative robot': 1, 'cobot': 1,
            'legged robot': 2, 'walking robot': 2, 'assistive robot': 1,
            'swarm robot': 1, 'flying robot': 1, 'underwater robot': 1,
            'space robot': 2, 'soft robot': 2, 'micro robot': 1,
            'pick and place': 2, 'bin picking': 2, 'peg-in-hole': 2,
            'assembly task': 2, 'door opening': 2, 'cabinet opening': 2,
            'cooking task': 2, 'cleaning task': 2, 'table clearing': 2,
            'object manipulation': 2, 'rope manipulation': 2, 'cloth manipulation': 2,
            'deformable manipulation': 2, 'articulated object': 2, 'dexterous manipulation': 2
        }

        # 可能不相关的关键词（如果仅有这些而没有其他机器人关键词，可能是误报）
        potentially_irrelevant = [
            'autonomous vehicle', 'self-driving', 'uav', 'drone', 'simulation',
            'virtual reality', 'augmented reality', 'game', 'animation',
            'reinforcement learning', 'blockchain', 'crypto', 'finance',
            'medical imaging', 'natural language processing', 'language model',
            'large language model', 'chatgpt', 'gpt-4', 'llama', 'bert', 'transformer'
        ]

        # 相关学术领域和会议 - 增加可靠性
        relevant_venues = {
            'icra': 3, 'iros': 3, 'rss': 3, 'corl': 3, 'humanoids': 3,
            'ral': 3, 'ijrr': 3, 'tro': 3, 'isrr': 3, 'iser': 3,
            'icml for robotics': 2, 'neurips for robotics': 2, 'iclr for robotics': 2,
            'learning for dynamics and control': 2, 'robot learning': 2,
            'haptics': 2, 'hri': 3, 'human-robot interaction': 3,
            'ieee robotics': 2, 'science robotics': 3, 'world robot': 2
        }

        # 特定机器人子领域 - 特定于类别的相关性
        category_specific_terms = {
            "Motion-Planning": {
                'trajectory': 2, 'path': 2, 'planning': 2, 'motion': 2, 'collision': 2,
                'avoidance': 2, 'navigation': 2, 'optimal': 2, 'differential flatness': 3,
                'spline': 2, 'interpolation': 2, 'motion generation': 2, 'riemannian': 2,
                'geodesic': 2, 'manifold': 2, 'so(3)': 3, 'se(3)': 3, 'configuration space': 3,
                'c-space': 3, 'cspace': 3, 'planning under uncertainty': 3
            },
            "Task-Planning": {
                'task': 2, 'plan': 2, 'scheduling': 2, 'hierarchical': 2, 'goal': 2,
                'tamp': 3, 'task and motion': 3, 'symbolic': 2, 'logic': 2, 'pddl': 3,
                'strips': 3, 'htn': 3, 'hierarchical task network': 3, 'temporal logic': 3,
                'belief space': 3, 'belief planning': 3, 'task specification': 3,
                'linear temporal logic': 3, 'ltl': 3, 'signal temporal logic': 3,
                'stl': 3, 'formal methods': 3, 'constraint satisfaction': 3
            },
            "Robot-Learning-and-Reinforcement-Learning": {
                'learning': 2, 'reinforcement': 2, 'policy': 2, 'reward': 2, 'agent': 2,
                'rl': 3, 'ppo': 3, 'sac': 3, 'trpo': 3, 'ddpg': 3, 'td3': 3,
                'imitation': 2, 'demonstration': 2, 'supervised': 2, 'unsupervised': 2,
                'self-supervised': 2, 'adversarial': 2, 'amp': 3, 'motion prior': 3,
                'skill': 2, 'primitive': 2, 'curriculum': 2, 'exploration': 2,
                'exploitation': 2, 'q-learning': 3, 'actor-critic': 3, 'value function': 3
            },
            "Environment-Perception": {
                'perception': 2, 'vision': 2, 'camera': 2, 'sensor': 2, 'lidar': 2,
                'depth': 2, 'rgb-d': 2, 'stereo': 2, 'semantic': 2, 'instance': 2,
                'object detection': 2, 'segmentation': 2, 'slam': 3, 'mapping': 2,
                'localization': 2, 'odometry': 2, 'registration': 2, 'pointcloud': 2,
                '3d': 2, 'reconstruction': 2, 'tracking': 2, 'visual-inertial': 3
            }
        }

        try:
            # 检查核心机器人关键词
            for keyword, weight in core_robot_keywords.items():
                if keyword in combined_text:
                    relevance_score += weight
                    relevance_reasons.append(f"包含核心关键词: {keyword} (+{weight})")

            # 检查领域特定关键词
            for keyword, weight in domain_specific_keywords.items():
                if keyword in combined_text:
                    relevance_score += weight
                    relevance_reasons.append(f"包含领域关键词: {keyword} (+{weight})")

            # 检查机器人硬件和平台
            for keyword, weight in robot_hardware_keywords.items():
                if keyword in combined_text:
                    relevance_score += weight
                    relevance_reasons.append(f"包含机器人硬件/平台: {keyword} (+{weight})")

            # 检查机器人算法和框架
            for keyword, weight in robot_algorithms.items():
                if keyword in combined_text:
                    relevance_score += weight
                    relevance_reasons.append(f"包含机器人算法/框架: {keyword} (+{weight})")

            # 检查机器人应用场景
            for keyword, weight in robot_applications.items():
                if keyword in combined_text:
                    relevance_score += weight
                    relevance_reasons.append(f"包含应用场景: {keyword} (+{weight})")

            # 检查学术领域和会议
            for keyword, weight in relevant_venues.items():
                if keyword in combined_text:
                    relevance_score += weight
                    relevance_reasons.append(f"包含相关会议/期刊: {keyword} (+{weight})")

            # 检查类别特定的术语
            if category in category_specific_terms:
                for keyword, weight in category_specific_terms[category].items():
                    if keyword in combined_text:
                        relevance_score += weight
                        relevance_reasons.append(f"包含{category}特定术语: {keyword} (+{weight})")

            # 检查标题中是否直接包含机器人关键词（额外加分）
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in core_robot_keywords.keys()):
                relevance_score += 3
                relevance_reasons.append("标题直接包含机器人关键词 (+3)")

            # 检查与当前类别的特定相关性
            category_keywords = {
                "Motion-Planning": ["motion", "planning", "trajectory", "path", "collision", "avoidance", "navigation", "control", "dynamic"],
                "Task-Planning": ["task", "planning", "decomposition", "hierarchical", "scheduling", "semantic", "symbolic", "reasoning"],
                "Robot-Learning-and-Reinforcement-Learning": ["reinforcement", "learning", "policy", "imitation", "training", "adaptation", "skill"],
                "Simulation-Platforms": ["simulation", "simulator", "environment", "platform", "digital", "physics", "synthetic"],
                "Multimodal-Interaction": ["interaction", "multimodal", "human-robot", "language", "speech", "gesture", "interface", "hri"],
                "Environment-Perception": ["perception", "vision", "sensing", "detection", "recognition", "slam", "mapping", "segmentation"],
                "Fundamental-Theory": ["theory", "cognitive", "representation", "generalization", "reasoning", "embodied", "intelligence"]
            }

            # 检查当前类别的关键词
            if category in category_keywords:
                category_matches = sum(1 for kw in category_keywords[category] if kw in combined_text)
                if category_matches >= 2:
                    category_bonus = category_matches
                    relevance_score += category_bonus
                    relevance_reasons.append(f"与类别 {category} 高度相关 (+{category_bonus})")

            # 检查是否包含关键词组合（更强的相关性指标）
            keyword_combinations = [
                ['robot', 'motion', 'planning'],
                ['humanoid', 'control'],
                ['legged', 'locomotion'],
                ['robot', 'reinforcement', 'learning'],
                ['robot', 'perception'],
                ['robot', 'manipulation'],
                ['embodied', 'intelligence'],
                ['robot', 'simulation'],
                ['human', 'robot', 'interaction'],
                ['adaptive', 'motion', 'optimization'],
                ['dexterous', 'manipulation'],
                ['whole-body', 'control'],
                ['robot', 'vision', 'language'],
                ['robot', 'tamp'],
                ['robotics', 'foundation', 'model'],
                ['mobile', 'manipulation'],
                ['robot', 'arm', 'control'],
                ['robot', 'grasp', 'planning'],
                ['trajectory', 'optimization', 'robot'],
                ['robot', 'self-supervised', 'learning'],
                ['robot', 'affordance', 'learning'],
                ['robot', 'policy', 'adaptation'],
                ['legged', 'robot', 'control'],
                ['humanoid', 'robot', 'motion'],
                ['quadruped', 'robot', 'locomotion'],
                ['robot', 'task', 'planning'],
                ['robot', 'hierarchical', 'planning'],
                ['embodied', 'robot', 'learning']
            ]

            for combo in keyword_combinations:
                if all(kw in combined_text for kw in combo):
                    combo_score = len(combo) * 2
                    relevance_score += combo_score
                    relevance_reasons.append(f"包含关键词组合: {' + '.join(combo)} (+{combo_score})")

            # 如果仅包含潜在不相关的关键词，减少相关性
            if any(term in combined_text for term in potentially_irrelevant) and relevance_score < 5:
                relevance_score -= 2
                relevance_reasons.append("可能与机器人无关 (-2)")

            # 分析标题和摘要的上下文
            # 如果标题直接是关于机器人的
            if title_lower.startswith("robot") or "robot" in title_lower.split()[:3]:
                relevance_score += 3
                relevance_reasons.append("标题以'机器人'开头或前三个词包含'机器人' (+3)")

            # 检查特殊的关键句
            special_phrases = [
                "we present a robot", "we propose a robot", "control of robot",
                "robot control", "robot system", "embodied agent", "robot platform",
                "humanoid robot", "legged robot", "quadruped robot", "dexterous manipulation",
                "robot learning", "robot simulation", "robot benchmark", "robotic system",
                "robot perception", "robot navigation", "robot manipulation",
                "robotic arm", "robotic hand", "robotic locomotion", "robotic grasping",
                "autonomous robot", "intelligent robot", "humanoid control", "biped robot",
                "mobile manipulator", "multi-legged robot", "robot arm", "robot hand"
            ]

            for phrase in special_phrases:
                if phrase in combined_text:
                    relevance_score += 2
                    relevance_reasons.append(f"包含关键句: '{phrase}' (+2)")

            # 特殊论文类型加分
            special_paper_types = {
                "adaptive motion optimization": 8,
                "amo": 8,
                "human-to-humanoid": 8,
                "omnih2o": 8,
                "dexterous humanoid": 8,
                "hyper-dexterous": 8,
                "whole-body control": 6,
                "parkour robot": 6,
                "anymal": 4,
                "atlas": 4,
                "cassie": 4,
                "digit": 4,
                "go1": 4,
                "unitree": 4,
                "spot": 4,
                "tiago": 4,
                "baxter": 4,
                "pepper": 4,
                "nao": 4,
                "icub": 4,
                "asimo": 4,
                "romeo": 4,
                "valkyrie": 4
            }

            for special_type, score in special_paper_types.items():
                if special_type in combined_text:
                    relevance_score += score
                    relevance_reasons.append(f"特殊论文类型: {special_type} (+{score})")

            # 使用摘要中的特定句式进行判断
            abstract_lower = abstract.lower()
            robotics_indicators = [
                "in this paper, we propose a robot",
                "we present a robot",
                "we introduce a robot",
                "for robotic applications",
                "in robotics,",
                "for robot control",
                "for robotic control",
                "robot experiments show",
                "robotic experiments show",
                "we evaluate our approach on a robot",
                "we evaluate our approach on real robots",
                "our method is evaluated on a robot",
                "we demonstrate on a real robot",
                "experimental results on a real robot",
                "experimental results on real-world robots"
            ]

            for indicator in robotics_indicators:
                if indicator in abstract_lower:
                    relevance_score += 4
                    relevance_reasons.append(f"摘要包含明确的机器人研究指示: '{indicator}' (+4)")

            # 检测机器人相关邮箱和机构
            if "robotics" in abstract_lower or "robot" in abstract_lower:
                for org in ["robotics", "robot research", "autonomous systems", "intelligent systems"]:
                    if org in abstract_lower:
                        relevance_score += 2
                        relevance_reasons.append(f"作者来自机器人相关机构: '{org}' (+2)")

            # 判断论文是否足够相关
            is_relevant = relevance_score >= 8  # 设置一个较高的相关性阈值

            # 如果标题明确包含"robot"或"robotic"，即使分数低也视为相关
            if "robot" in title_lower or "robotic" in title_lower:
                is_relevant = True
                if relevance_score < 8:
                    relevance_score = 8
                    relevance_reasons.append("标题明确包含'robot'或'robotic'，确定为相关论文 (+8)")

            return {
                "score": relevance_score,
                "is_relevant": is_relevant,
                "reasons": relevance_reasons,
                "is_special_paper": any(special_type in combined_text for special_type in special_paper_types)
            }
        except Exception as e:
            logger.error(f"评估论文相关性时出错: {str(e)}")
            logger.error(traceback.format_exc())
            # 发生错误时返回安全的默认值
            return {
                "score": 0,
                "is_relevant": False,
                "reasons": ["评估过程中发生错误"],
                "is_special_paper": False
            }

if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='更新具身AI与机器人相关论文列表')
    parser.add_argument('--days', type=int, default=30, help='筛选最近多少天内发表的论文，默认30天')

    # 解析命令行参数
    args = parser.parse_args()

    # 使用命令行参数初始化PaperUpdater
    updater = PaperUpdater(days_filter=args.days)
    updater.run()