import os
import re
import json
import requests
import arxiv
from datetime import datetime
from bs4 import BeautifulSoup
from tqdm import tqdm
import string

class PaperUpdater:
    def __init__(self):
        self.base_url = "https://arxiv.paperswithcode.com/api/v0/papers/"
        # 定义目录和对应的检索关键词
        self.categories = {
            "Motion-Planning": "motion planning OR trajectory optimization OR path planning OR collision avoidance OR whole-body motion OR dynamic motion OR real-time planning OR humanoid control OR robot control OR locomotion planning",
            "Task-Planning": "task planning OR task decomposition OR task scheduling OR hierarchical planning OR TAMP OR task and motion planning OR learning-based planning OR multi-agent planning OR long-horizon planning OR semantic planning",
            "Simulation-Platforms": "physics engine OR robot simulation OR simulation environment OR digital twin OR synthetic data OR benchmark platform OR physics simulator OR virtual environment OR robot environment OR learning environment",
            "Robot-Learning-and-Reinforcement-Learning": "reinforcement learning OR RL OR policy learning OR robot learning OR legged robot OR quadruped OR biped OR locomotion OR motor skill OR imitation learning OR policy gradient OR PPO OR SAC OR DDPG OR sim2real OR transfer learning OR multi-task learning OR hierarchical RL OR meta-learning OR offline RL",
            "Multimodal-Interaction": "multimodal OR multi-modal OR cross-modal OR human-robot interaction OR vision language OR visual language OR gesture recognition OR speech interaction OR tactile interaction OR social robotics OR natural language for robots OR robot reasoning OR embodied interaction OR embodied communication",
            "Environment-Perception": "environment perception OR scene understanding OR object detection OR visual perception OR terrain understanding OR SLAM OR mapping OR sensor fusion OR 3D perception OR semantic segmentation OR depth estimation OR point cloud processing OR visual navigation OR visual localization",
            "Fundamental-Theory": "embodied AI OR embodied intelligence OR embodied learning OR cognitive science OR control theory OR embodied cognition OR computational models OR learning theory OR evaluation methods OR embodied representation OR embodied generalization OR embodied reasoning OR embodied memory OR embodied adaptation"
        }

        # 初始化手动添加的论文字典
        self.manually_added_papers = {}

        # 定义各主题的标签和关键词
        self.tags = {
            # 强化学习标签
            "Robot-Learning-and-Reinforcement-Learning": {
                "Foundational": ["foundational", "fundamental", "core", "basic", "essential", "pioneering", "seminal"],
                "Imitation": ["imitation", "demonstration", "expert", "teacher", "learning from demonstration", "behavioral cloning", "apprenticeship learning"],
                "Milestone": ["milestone", "breakthrough", "significant", "important", "key", "landmark", "pivotal"],
                "Biped": ["biped", "bipedal", "humanoid", "two-legged", "walking", "running", "jumping"],
                "Quadruped": ["quadruped", "four-legged", "dog", "animal", "canine", "feline", "mammal"],
                "AMP": ["AMP", "adversarial", "motion prior", "style", "character", "motion style", "motion imitation"],
                "Adaptation": ["adaptation", "transfer", "generalization", "robust", "resilient", "domain adaptation", "zero-shot", "few-shot"],
                "Policy": ["policy", "actor-critic", "PPO", "SAC", "DDPG", "TRPO", "policy optimization", "policy gradient", "value function"],
                "Sim2Real": ["sim2real", "sim-to-real", "transfer", "domain", "reality gap", "simulation transfer", "simulation adaptation", "reality gap"],
                "Hierarchical": ["hierarchical", "HRL", "option", "skill", "subgoal", "hierarchical RL", "option discovery", "skill discovery"],
                "Multi-Task": ["multi-task", "multi-task learning", "generalist", "versatile", "multi-task RL", "task generalization", "task transfer"],
                "Offline": ["offline", "batch", "off-policy", "data-driven", "offline RL", "batch RL", "conservative RL", "data-efficient"],
                "Meta": ["meta", "meta-learning", "few-shot", "adaptation", "meta-RL", "model-agnostic meta-learning", "reptile", "maml"],
                "Multi-Agent": ["multi-agent", "collaboration", "cooperation", "interaction", "multi-agent RL", "team learning", "collective intelligence"]
            },
            # 运动规划标签
            "Motion-Planning": {
                "Trajectory": ["trajectory", "path", "motion", "planning", "optimization", "trajectory optimization", "path planning", "motion planning", "trajectory generation"],
                "Collision": ["collision", "avoidance", "safety", "obstacle", "collision avoidance", "obstacle avoidance", "safety constraints", "collision-free"],
                "Real-time": ["real-time", "realtime", "fast", "efficient", "computational", "real-time planning", "fast planning", "efficient planning", "computational efficiency"],
                "Learning": ["learning", "learned", "neural", "deep", "ML", "learning-based planning", "neural planning", "deep planning", "ML-based planning"],
                "Dynamic": ["dynamic", "dynamics", "kinematic", "kinematics", "dynamic planning", "dynamics-aware", "kinematic planning", "dynamic constraints"],
                "Uncertainty": ["uncertainty", "robust", "stochastic", "probabilistic", "uncertainty-aware", "robust planning", "stochastic planning", "probabilistic planning"],
                "Multi-robot": ["multi-robot", "swarm", "collaborative", "coordination", "multi-robot planning", "swarm planning", "collaborative planning", "coordinated planning"],
                "Reactive": ["reactive", "reaction", "responsive", "adaptive", "reactive planning", "reactive control", "responsive planning", "adaptive planning"],
                "Whole-body": ["whole-body", "full-body", "whole-body planning", "full-body planning", "whole-body motion", "full-body motion", "whole-body control"],
                "Humanoid": ["humanoid", "humanoid planning", "humanoid control", "humanoid motion", "humanoid locomotion", "humanoid walking", "humanoid running"]
            },
            # 任务规划标签
            "Task-Planning": {
                "Hierarchical": ["hierarchical", "hierarchy", "decomposition", "subtask", "hierarchical planning", "task decomposition", "subtask planning", "hierarchical task"],
                "Temporal": ["temporal", "temporal logic", "sequence", "ordering", "temporal planning", "sequence planning", "temporal constraints", "temporal reasoning"],
                "Learning": ["learning", "learned", "neural", "deep", "ML", "learning-based planning", "neural planning", "deep planning", "ML-based planning"],
                "Semantic": ["semantic", "language", "instruction", "command", "semantic planning", "language-based planning", "instruction-based planning", "command-based planning"],
                "Multi-agent": ["multi-agent", "collaboration", "cooperation", "interaction", "multi-agent planning", "collaborative planning", "cooperative planning", "team planning"],
                "Uncertainty": ["uncertainty", "robust", "stochastic", "probabilistic", "uncertainty-aware", "robust planning", "stochastic planning", "probabilistic planning"],
                "Interactive": ["interactive", "human", "user", "feedback", "interactive planning", "human-in-the-loop", "user feedback", "interactive learning"],
                "Long-horizon": ["long-horizon", "long-term", "complex", "sequential", "long-horizon planning", "long-term planning", "complex task", "sequential task"],
                "TAMP": ["TAMP", "task and motion planning", "integrated planning", "combined planning", "task-motion", "task-motion integration", "task-motion coordination"],
                "Reasoning": ["reasoning", "logical", "symbolic", "abstract", "task reasoning", "logical planning", "symbolic planning", "abstract reasoning"]
            },
            # 仿真平台标签
            "Simulation-Platforms": {
                "Physics": ["physics", "engine", "simulation", "dynamics", "physics engine", "physics simulator", "dynamics simulation", "physical simulation"],
                "Visual": ["visual", "rendering", "graphics", "3D", "visualization", "renderer", "visual simulation", "3D rendering", "graphics engine"],
                "Realistic": ["realistic", "realism", "photo-realistic", "high-fidelity", "realistic simulation", "photo-realism", "high-fidelity simulation", "realistic rendering"],
                "Benchmark": ["benchmark", "evaluation", "test", "challenge", "benchmarking platform", "evaluation framework", "testing framework", "challenge platform"],
                "Multi-domain": ["multi-domain", "multi-task", "versatile", "general", "multi-robot", "multi-domain simulation", "multi-task environment", "versatile platform"],
                "Open-source": ["open-source", "open source", "community", "collaborative", "public", "open-source platform", "community-driven", "collaborative development"],
                "Scalable": ["scalable", "parallel", "distributed", "efficient", "high-performance", "scalable simulation", "parallel simulation", "distributed simulation"],
                "Interactive": ["interactive", "user", "human", "interface", "interaction", "interactive simulation", "user interface", "human interaction", "interactive environment"],
                "Digital Twin": ["digital twin", "virtual world", "virtual environment", "synthetic environment", "digital representation", "virtual representation", "synthetic world"],
                "Robot Environment": ["robot environment", "robot simulation", "robot simulator", "robot platform", "robot testbed", "robot testing", "robot evaluation", "robot development"],
                "Learning Environment": ["learning environment", "training environment", "simulation environment", "testbed", "learning platform", "training platform", "simulation testbed", "learning testbed"]
            },
            # 多模态交互标签
            "Multimodal-Interaction": {
                "Vision-Language": ["vision-language", "visual language", "image-text", "multimodal", "vision-language model", "visual language model", "image-text model", "multimodal model"],
                "Human-Robot": ["human-robot", "human robot", "interaction", "collaboration", "human-robot interaction", "human-robot collaboration", "human-robot communication", "human-robot cooperation"],
                "Gesture": ["gesture", "motion", "body", "sign", "gesture recognition", "body language", "sign language", "motion understanding", "gesture understanding"],
                "Speech": ["speech", "audio", "voice", "sound", "speech recognition", "audio processing", "voice interaction", "sound understanding", "speech understanding"],
                "Tactile": ["tactile", "touch", "haptic", "force", "tactile sensing", "touch sensing", "haptic feedback", "force sensing", "tactile interaction"],
                "Learning": ["learning", "learned", "neural", "deep", "ML", "multimodal learning", "cross-modal learning", "fusion learning", "joint learning"],
                "Real-time": ["real-time", "realtime", "fast", "efficient", "real-time interaction", "fast response", "efficient processing", "real-time processing"],
                "Social": ["social", "emotional", "cognitive", "mental", "social robotics", "emotional intelligence", "cognitive interaction", "mental model", "social understanding"],
                "Natural Language": ["natural language", "language understanding", "language generation", "language model", "NLP", "language processing", "language interaction", "language communication"],
                "Embodied": ["embodied", "embodiment", "physical", "corporeal", "embodied interaction", "physical interaction", "corporeal communication", "embodied communication"]
            },
            # 环境感知标签
            "Environment-Perception": {
                "Object": ["object", "detection", "recognition", "tracking", "object detection", "object recognition", "object tracking", "object understanding", "object localization"],
                "Scene": ["scene", "understanding", "parsing", "segmentation", "scene understanding", "scene parsing", "scene segmentation", "scene recognition", "scene analysis"],
                "3D": ["3D", "point cloud", "depth", "stereo", "3D perception", "point cloud processing", "depth estimation", "stereo vision", "3D reconstruction"],
                "Semantic": ["semantic", "meaning", "interpretation", "reasoning", "semantic understanding", "semantic interpretation", "semantic reasoning", "semantic analysis", "semantic mapping"],
                "Learning": ["learning", "learned", "neural", "deep", "ML", "perception learning", "visual learning", "sensor learning", "environment learning"],
                "Real-time": ["real-time", "realtime", "fast", "efficient", "real-time perception", "fast perception", "efficient perception", "real-time processing"],
                "Robust": ["robust", "robustness", "adversarial", "attack", "robust perception", "adversarial robustness", "attack resistance", "robust recognition"],
                "Multi-modal": ["multi-modal", "multimodal", "fusion", "integration", "multi-modal perception", "sensor fusion", "modality integration", "cross-modal perception"],
                "SLAM": ["SLAM", "mapping", "localization", "navigation", "simultaneous localization and mapping", "environment mapping", "robot localization", "visual navigation"],
                "Terrain": ["terrain", "ground", "surface", "environment", "terrain understanding", "ground perception", "surface analysis", "environment analysis"]
            },
            # 基础理论标签
            "Fundamental-Theory": {
                "Cognitive": ["cognitive", "cognition", "mental", "brain", "cognitive science", "cognitive model", "mental representation", "brain-inspired", "cognitive architecture"],
                "Control": ["control", "controller", "stability", "dynamics", "control theory", "controller design", "stability analysis", "dynamics modeling", "control architecture"],
                "Learning": ["learning", "learned", "neural", "deep", "ML", "learning theory", "neural learning", "deep learning", "machine learning", "representation learning"],
                "Representation": ["representation", "embedding", "feature", "latent", "representation learning", "embedding space", "feature learning", "latent space", "concept learning"],
                "Generalization": ["generalization", "transfer", "adaptation", "robust", "generalization theory", "transfer learning", "adaptation mechanism", "robust learning", "domain generalization"],
                "Theory": ["theory", "theoretical", "analysis", "proof", "theoretical framework", "theoretical analysis", "mathematical proof", "theoretical model", "theoretical foundation"],
                "Survey": ["survey", "review", "overview", "tutorial", "literature survey", "research review", "field overview", "comprehensive tutorial", "state-of-the-art review"],
                "Benchmark": ["benchmark", "evaluation", "test", "challenge", "benchmarking framework", "evaluation methodology", "testing framework", "challenge design", "performance metrics"],
                "Embodied": ["embodied", "embodiment", "physical", "corporeal", "embodied intelligence", "embodied cognition", "physical intelligence", "corporeal learning", "embodied learning"],
                "Reasoning": ["reasoning", "inference", "logic", "abstract", "reasoning mechanism", "inference engine", "logical reasoning", "abstract thinking", "reasoning model"]
            }
        }

        self.existing_papers = self.load_existing_papers()
        self.keywords = self.extract_keywords_from_existing_papers()

    def ensure_directory_exists(self, directory):
        """确保目录存在，如果不存在则创建"""
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"创建目录: {directory}")

    def load_existing_papers(self):
        """加载现有论文信息"""
        existing_papers = {}
        for category in self.categories.keys():
            existing_papers[category] = []
            en_file = f"{category}/README.md"
            cn_file = f"{category}/README_CN.md"

            # 确保目录存在
            self.ensure_directory_exists(category)

            if os.path.exists(en_file):
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

                            existing_papers[category].append({
                                "date": date.strip(),
                                "title": clean_title,
                                "pdf_url": pdf_url,
                                "code_url": code_url,
                                "rating": rating.strip(),
                                "manual": False  # 标记为自动更新
                            })

        return existing_papers

    def extract_keywords_from_existing_papers(self):
        """从现有论文标题中提取关键词"""
        keywords = {}
        for category, papers in self.existing_papers.items():
            if not papers:
                keywords[category] = self.categories[category]
                continue

            # 收集所有标题
            titles = [paper["title"] for paper in papers]

            # 简单分词并提取关键词
            all_words = []
            for title in titles:
                # 简单的分词方法，按空格和标点符号分割
                words = re.findall(r'\b\w+\b', title.lower())
                # 过滤掉太短的词
                words = [word for word in words if len(word) > 3]
                all_words.extend(words)

            # 统计词频
            word_freq = {}
            for word in all_words:
                if word in word_freq:
                    word_freq[word] += 1
                else:
                    word_freq[word] = 1

            # 选择最常见的词作为关键词
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            keyword_query = " OR ".join([word for word, _ in top_words])

            # 结合原始查询和提取的关键词
            keywords[category] = f"({self.categories[category]}) AND ({keyword_query})"

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
        except:
            return None

    def identify_tag(self, category, title, abstract):
        """识别论文的标签"""
        # 不再使用标签，返回空字符串
        return ""

    def get_daily_papers(self, category, query, max_results=50):
        """获取每日论文"""
        papers = []
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )

        for result in tqdm(search.results(), desc=f"获取{category}论文"):
            paper_id = result.get_short_id()

            # 检查是否已存在
            if any(paper["title"] == result.title for paper in self.existing_papers[category]):
                continue

            code_url = self.get_paper_info(paper_id)

            # 尝试识别标签
            title = result.title
            tag = self.identify_tag(category, title, result.summary)

            # 如果标题中有冒号，尝试提取标签
            if not tag and ":" in title:
                tag = title.split(":")[0].strip()
                title = title.split(":")[1].strip()

            paper_info = {
                "date": str(result.published.date()),
                "title": title,
                "tag": tag,
                "authors": [author.name for author in result.authors],
                "abstract": result.summary,
                "pdf_url": result.entry_id,
                "code_url": code_url if code_url else "⚠️",
                "rating": "⭐️⭐️⭐️",  # 默认评分
                "has_code": code_url is not None,
                "manual": False  # 标记为自动更新
            }
            papers.append(paper_info)

        return papers

    def update_category_readme(self, category, new_papers):
        """更新分类目录的README文件"""
        # 确保目录存在
        self.ensure_directory_exists(category)

        # 获取现有的手动添加论文
        existing_manual_papers = self.manually_added_papers.get(category, [])

        # 过滤掉已经存在于手动添加论文中的新论文
        filtered_new_papers = []
        for paper in new_papers:
            if not any(p['title'] == paper['title'] for p in existing_manual_papers):
                filtered_new_papers.append(paper)

        # 合并所有自动更新的论文
        all_auto_papers = filtered_new_papers

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
                code_name = code_url.split("/")[-1].replace(")", "")
                # 返回标准的 Markdown 链接格式
                return f"[{code_name}]({code_url})"

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
                    for content in category_contents[category]['en']:
                        en_content += f"- {content}\n"
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
                            code_link = format_code_link(paper['code_url'])
                            en_content += f"|{paper['date']}|{paper['title']}|[[pdf]]({paper['pdf_url']})|{code_link}|{paper['rating']}|\n"
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
                    for content in category_contents[category]['cn']:
                        cn_content += f"- {content}\n"
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
                            code_link = format_code_link(paper['code_url'])
                            cn_content += f"|{paper['date']}|{paper['title']}|[[pdf]]({paper['pdf_url']})|{code_link}|{paper['rating']}|\n"
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

        # 更新现有论文列表
        self.existing_papers[category] = existing_manual_papers + all_auto_papers

    def update_root_readme(self):
        """更新根目录的README文件"""
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

    def run(self):
        """运行更新程序"""
        print("开始更新论文列表...")

        for category, query in self.keywords.items():
            print(f"\n处理分类: {category}")
            print(f"使用查询: {query}")
            papers = self.get_daily_papers(category, query)
            if papers:
                print(f"找到 {len(papers)} 篇新论文")
                self.update_category_readme(category, papers)
            else:
                print("没有找到新论文")

        self.update_root_readme()
        print("\n更新完成！")

if __name__ == "__main__":
    updater = PaperUpdater()
    updater.run()