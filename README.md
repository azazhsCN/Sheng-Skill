# Sheng-Skill

为 AI 编程 Agent 打造的技能集合。用户无需手动操作，Agent 自动下载安装。

[English](README_en.md)

---

## Skills

### vision-helper — 图像内容分析

通过 OpenAI 兼容接口调用具备视觉能力的模型（如 Gemini、GPT-4o 等），让没有视觉能力的语言模型也能"看见"图像——将图片内容转化为文字描述供 Agent 理解和使用。

```
Agent 安装指令：
下载 https://github.com/azazhsCN/Sheng-Skill/tree/main/skills/vision-helper 目录下的所有文件到本地 skills/vision-helper/，
将该目录的绝对路径加入你的 skills 配置，
安装依赖 pip install -r skills/vision-helper/scripts/requirements.txt，
并将 .env.example 复制为 .env 提示用户填入 API Key。
```

---

## 独立 Agent

### 电商选品智能体

一个专注于电商选品的自动化评估与风险分析 Agent，支持风险检测、消费者偏好匹配、市场对比和 A-D 评级。

- **仓库：** [github.com/azazhsCN/xuanpin](https://github.com/azazhsCN/xuanpin)

---

## License

MIT
