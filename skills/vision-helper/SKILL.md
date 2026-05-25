---
name: vision-helper
description: |
  图像内容分析工具。当用户提供了一张或多张实际图片（本地文件路径或网络URL），需要你"看"懂图片内容、
  提取文字、描述场景、解读图表/截图/UI/架构图时，使用此技能。技能会调用外部视觉API将图片转为文字描述。
  Use this skill when the user has an actual image file or URL they want you to visually analyze —
  read text from, describe contents, interpret charts/diagrams/screenshots/UI mockups, or answer
  questions about what's shown in the image. The user typically provides a file path like "C:\\photo.jpg"
  or a URL like "https://example.com/image.png", along with phrases like "看看这张图", "帮我分析",
  "描述一下", "what's in this image", "analyze this screenshot".
  Do NOT trigger for: writing image processing code, recommending tools, explaining concepts,
  generating images, converting file formats, or troubleshooting image loading issues.
  Trigger keywords: 看看这张图, 分析图片, 描述图片, 图片里有什么, 截图内容, 读取图片文字,
  what's in this image, analyze this screenshot, describe this photo, OCR, 提取文字, 看一下.
---

# Vision Helper

让没有视觉能力的语言模型也能"看见"图像。通过调用支持视觉的外部 API（如 Gemini Flash），
将图像内容转化为详细的文字描述，供当前模型理解和使用。

## 工作流程

1. 接收用户的图片（本地路径或URL）和可选的问题
2. 调用视觉分析脚本处理图片
3. 将分析结果返回给当前模型，作为图像理解的上下文

## 使用方式

### 命令行调用

```bash
# 单张图片 — 全面描述
python scripts/analyze.py /path/to/image.jpg

# 单张图片 + 具体问题
python scripts/analyze.py /path/to/image.jpg -q "这张截图里的错误信息是什么？"

# 多张图片
python scripts/analyze.py img1.jpg img2.png img3.webp

# 多张图片 + 对比问题
python scripts/analyze.py before.png after.png -q "这两张图有什么区别？"

# 网络图片
python scripts/analyze.py https://example.com/photo.jpg

# JSON格式输出
python scripts/analyze.py image.jpg --output-json
```

### 在技能中使用

当用户需要分析图像时，按以下步骤操作：

1. **确认图片位置**：检查用户提供的路径是否存在，或URL是否可访问
2. **确定问题**：用户是否有具体问题？没有则使用默认全面描述模式
3. **调用脚本**：使用 `python <skill-path>/scripts/analyze.py` 处理图片
4. **返回结果**：将脚本输出直接展示给用户，或融入你的回答中

## 配置说明

脚本从 `.env` 文件读取 API 配置。首次使用前：

1. 复制 `.env.example` 为 `.env`
2. 确认 API Key 和端点正确

`.env` 文件中的变量名：
- `VISION_API_BASE` — API 端点地址
- `VISION_API_KEY` — API 密钥
- `VISION_MODEL` — 模型名称

也可以通过命令行参数 `--api-base`、`--api-key`、`--model` 覆盖。

## 依赖

运行前确保已安装 requests：

```bash
pip install requests
```

## 支持的图片格式

- 本地文件：`.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`
- 网络图片：任何可通过 HTTP/HTTPS 访问的图片 URL

## 注意事项

- 单张图片大小不超过 20MB，超时设为 120 秒
- 多张图片会在一次请求中发送，如果图片过多可能导致 token 超限
- 建议单次请求不超过5张图片
- API Key 包含在 .env 文件中，注意不要将其提交到公开仓库
