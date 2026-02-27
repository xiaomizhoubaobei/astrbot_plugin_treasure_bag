# Treasure Bag Plugin

[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fxiaomizhoubaobei%2Fastrbot_plugin_treasure_bag.svg?type=shield&issueType=security)](https://app.fossa.com/projects/git%2Bgithub.com%2Fxiaomizhoubaobei%2Fastrbot_plugin_treasure_bag?ref=badge_shield&issueType=security)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fxiaomizhoubaobei%2Fastrbot_plugin_treasure_bag.svg?type=small)](https://app.fossa.com/projects/git%2Bgithub.com%2Fxiaomizhoubaobei%2Fastrbot_plugin_treasure_bag?ref=badge_small)
![GitHub Repo stars](https://img.shields.io/github/stars/xiaomizhoubaobei/astrbot_plugin_treasure_bag)
![GitHub forks](https://img.shields.io/github/forks/xiaomizhoubaobei/astrbot_plugin_treasure_bag)
![GitHub watchers](https://img.shields.io/github/watchers/xiaomizhoubaobei/astrbot_plugin_treasure_bag)
[![GitHub issues](https://img.shields.io/github/issues/xiaomizhoubaobei/astrbot_plugin_treasure_bag)](https://github.com/xiaomizhoubaobei/astrbot_plugin_treasure_bag/issues)
[![GitHub license](https://img.shields.io/github/license/xiaomizhoubaobei/astrbot_plugin_treasure_bag)](https://github.com/xiaomizhoubaobei/astrbot_plugin_treasure_bag/blob/main/LICENSE)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/xiaomizhoubaobei/astrbot_plugin_treasure_bag)](https://github.com/xiaomizhoubaobei/astrbot_plugin_treasure_bag/releases)
[![Commit Activity](https://img.shields.io/github/commit-activity/w/xiaomizhoubaobei/astrbot_plugin_treasure_bag)](https://github.com/xiaomizhoubaobei/astrbot_plugin_treasure_bag)
![GitHub last commit](https://img.shields.io/github/last-commit/xiaomizhoubaobei/astrbot_plugin_treasure_bag)
![GitHub contributors](https://img.shields.io/github/contributors/xiaomizhoubaobei/astrbot_plugin_treasure_bag)
![Python Version](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)
![Code Review](https://img.shields.io/badge/code_review-100%25-brightgreen.svg)
![Repo Size](https://img.shields.io/github/repo-size/xiaomizhoubaobei/astrbot_plugin_treasure_bag.svg)

一个为AstrBot设计的多功能插件，包含多种实用和娱乐功能。

## 目录结构

```
百宝袋插件目录结构:
├── main.py               # 插件主入口点 (在根目录!)
├── metadata.yaml         # 插件元数据
├── requirements.txt      # 依赖项
├── README.md            # 说明文档
├── __init__.py          # 包入口
├── handlers/            # 功能处理器模块
│   ├── __init__.py
│   ├── hitokoto_handler.py      # 一言功能
│   ├── beauty_img_handler.py    # 美女图片功能
│   ├── handwrite_handler.py     # 手写体功能
│   ├── sad_word_handler.py      # 伤感语录功能
│   ├── wangzhe_handler.py       # 王者荣耀功能
│   ├── xingzuo_handler.py       # 星座运势功能
│   └── weather_handler.py       # 天气功能
├── baidu/               # 百度API相关
│   ├── __init__.py
│   ├── baidu_auth.py            # 百度认证管理
│   └── beauty_handler.py        # 颜值评分功能
├── utils/               # 工具函数
│   ├── __init__.py
│   └── command_utils.py         # 命令处理工具
└── config/              # 配置相关
    └── __init__.py
```

## 功能详情
- 获取随机一言语录：从精选一言库中随机返回一条语录 (保留功能)
- 通过图片分析颜值评分：基于百度AI开放平台的人脸识别API，分析人像照片并给出颜值评分 (保留功能)
- 查询王者荣耀英雄资料：根据英雄名称查询相关资料 (保留功能)
- 生成手写样式的图片：根据输入内容生成手写风格的图片 (保留功能)
- 获取随机美女图片：随机返回一张美女图片

## 依赖要求
- Python 3.8+
- AstrBot框架
- 百度AI开放平台API Key（用于颜值评分功能）

## 命令列表
1. /hitokoto - 获取一条一言
2. /测颜值 - 发送人像图片获取颜值评分
3. /王者 [英雄名称] - 查询王者荣耀英雄资料
4. /handwrite [内容] - 生成手写样式的图片
5. /beauty-img (或 /美女图片, /今日美女, /随机美女图片) - 获取一张随机美女图片
6. /treasurebag-help - 显示帮助信息

## 安装
1. 将插件文件夹放入AstrBot的plugins目录
2. 重启AstrBot

## 配置
1. 百度API配置（颜值评分功能需要）
   - 前往[百度AI开放平台](https://ai.baidu.com/)申请API Key
   - 在插件配置文件中添加：
     ```
     [baidu]
     api_key = "your_api_key"
     secret_key = "your_secret_key"
     ```
2. 依赖安装
   - 运行 `pip install -r requirements.txt` 安装所需依赖

## 使用示例
```
/hitokoto
> 获取一条随机一言

/测颜值 [图片]
> 分析图片并返回颜值评分

/王者 亚瑟
> 查询英雄“亚瑟”的资料

/handwrite 你好世界
> 生成手写样式的图片

/beauty-img
> 获取一张随机美女图片

/treasurebag-help
> 显示插件帮助信息
```

## 支持
如有问题，请参考[官方文档](https://astrbot.app)或联系开发者。

## 更新日志
完整的历史版本记录请查看 [CHANGELOG.md](./CHANGELOG.md)

## 审计
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fxiaomizhoubaobei%2Fastrbot_plugin_treasure_bag.svg?type=large&issueType=license)](https://app.fossa.com/projects/git%2Bgithub.com%2Fxiaomizhoubaobei%2Fastrbot_plugin_treasure_bag?ref=badge_large&issueType=license)