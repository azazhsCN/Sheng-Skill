#!/usr/bin/env python3
"""Vision analysis script — calls an OpenAI-compatible multimodal API to describe images."""

import argparse
import base64
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

VERSION = "1.1.0"

# Fix Windows console encoding for Chinese output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library not found. Install it with: pip install requests", file=sys.stderr)
    sys.exit(1)

# Allowed local file extensions and their MIME types
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".tiff", ".tif"}

MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".svg": "image/svg+xml",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}

# Derived from MIME_MAP — keep in sync by using it as the single source of truth
IMAGE_CONTENT_TYPES = set(MIME_MAP.values())

MAX_IMAGES = 5
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


def load_env() -> dict:
    """Search upward from the script directory for a .env file (max 3 levels)."""
    env_vars = {}

    search_dir = Path(__file__).resolve().parent.parent
    for depth, parent in enumerate([search_dir] + list(search_dir.parents)):
        if depth > 3:
            break
        env_file = parent / ".env"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        env_vars[key] = value
            break

    return env_vars


def is_url(path: str) -> bool:
    """Check if a string is a URL."""
    parsed = urlparse(path)
    return parsed.scheme in ("http", "https")


def detect_lang(text: str) -> str:
    """Heuristic: detect if text contains Chinese characters."""
    for ch in text:
        if "一" <= ch <= "鿿":
            return "zh"
    return "en"


SYSTEM_PROMPTS = {
    "zh": (
        "你是一个专业的图像分析助手。请用中文详细描述用户提供的图片内容，"
        "力求准确、全面、有条理。如果图片中包含文字，请完整提取。"
        "如果是UI截图，请描述布局和交互元素。"
    ),
    "en": (
        "You are a professional image analysis assistant. Please describe the contents of the image "
        "in detail, accurately, comprehensively, and in an organized manner. "
        "If the image contains text, extract it completely. "
        "If it is a UI screenshot, describe the layout and interactive elements."
    ),
}

DEFAULT_PROMPTS = {
    "zh": "请详细描述这张图片的内容。包括：主体对象、场景环境、颜色风格、文字信息（如有）、布局结构等所有可见细节。",
    "en": "Please describe this image in detail, including: main subject, scene/environment, colors and style, any visible text, layout and structure, and all other visible details.",
}


def encode_image_base64(image_path: str) -> str:
    """Read a local image file and return its base64 encoding."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"Image file too large: {file_size / (1024 * 1024):.1f} MB "
            f"(max {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB)"
        )

    suffix = path.suffix.lower()
    mime_type = MIME_MAP.get(suffix, "image/jpeg")

    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


def build_image_content(image_input: str) -> dict:
    """Build the image content block for the API message."""
    if is_url(image_input):
        return {
            "type": "image_url",
            "image_url": {"url": image_input}
        }
    else:
        data_uri = encode_image_base64(image_input)
        return {
            "type": "image_url",
            "image_url": {"url": data_uri}
        }


def validate_url_is_image(url: str) -> bool:
    """Best-effort check: does a URL likely point to an image?"""
    # Check path extension first
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    ext = Path(path_lower).suffix.lower()
    if ext in SUPPORTED_EXTENSIONS:
        return True

    # HEAD request to check content-type
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        content_type = resp.headers.get("content-type", "")
        for img_ct in IMAGE_CONTENT_TYPES:
            if img_ct in content_type:
                return True
    except Exception:
        pass

    return False


def analyze_images(
    image_paths: list[str],
    question: str | None = None,
    api_base: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    """Send images to the vision API and return the analysis text.

    Raises:
        ValueError: if configuration is invalid.
        RuntimeError: if the API call fails.
    """

    # Load config from .env, then override with explicit args
    env = load_env()

    api_base = api_base or env.get("VISION_API_BASE")
    api_key = api_key or env.get("VISION_API_KEY")
    model = model or env.get("VISION_MODEL") or "gemini-3.1-flash-lite-preview"

    if not api_base:
        raise ValueError("No API endpoint configured. Set VISION_API_BASE in .env or pass --api-base.")
    if not api_key:
        raise ValueError("No API key configured. Set VISION_API_KEY in .env or pass --api-key.")

    # Ensure the endpoint ends correctly
    if not api_base.endswith("/chat/completions"):
        api_base = api_base.rstrip("/") + "/chat/completions"

    # Detect language from the question (or default prompt)
    lang = detect_lang(question or DEFAULT_PROMPTS["zh"])
    system_prompt = SYSTEM_PROMPTS[lang]

    # Build the prompt
    if question:
        user_text = question
    else:
        user_text = DEFAULT_PROMPTS[lang]

    # Build message content
    content = []
    for img_path in image_paths:
        content.append(build_image_content(img_path))
    content.append({"type": "text", "text": user_text})

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]

    # Call the API
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 65536,
    }

    try:
        response = requests.post(api_base, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError("API request timed out (120s). The image may be too large or the server is slow.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"API returned HTTP {e.response.status_code}: {e.response.text[:500]}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Could not connect to API at {api_base}. Check your network and the endpoint URL.")

    # Parse response with defensive checks
    try:
        result = response.json()
    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(f"API response is not valid JSON: {e}. Raw response: {response.text[:300]}")

    if not isinstance(result.get("choices"), list) or not result["choices"]:
        raise RuntimeError(f"API response has no 'choices' array. Response: {json.dumps(result, ensure_ascii=False)[:500]}")

    first = result["choices"][0]
    if not isinstance(first.get("message"), dict):
        raise RuntimeError(f"API choice[0] has no 'message' field. Choice: {json.dumps(first, ensure_ascii=False)[:500]}")

    text = first["message"].get("content")
    if text is None:
        raise RuntimeError(
            f"API message has no 'content' field (may be a tool_call response). "
            f"Message: {json.dumps(first['message'], ensure_ascii=False)[:500]}"
        )

    return text


def main():
    parser = argparse.ArgumentParser(description="Analyze images using a vision API")
    parser.add_argument("images", nargs="+", help="Image file paths or URLs")
    parser.add_argument("-q", "--question", default=None, help="Optional question about the images")
    parser.add_argument("--api-base", default=None, help="API endpoint URL")
    parser.add_argument("--api-key", default=None, help="API key")
    parser.add_argument("--model", default=None, help="Model name")
    parser.add_argument("--output-json", action="store_true", help="Output result as JSON")
    parser.add_argument("--version", action="version", version=f"vision-helper {VERSION}")

    args = parser.parse_args()

    # Validate local files exist and are within size limits before calling the API
    for img in args.images:
        if not is_url(img):
            if not Path(img).exists():
                print(f"ERROR: File not found: {img}", file=sys.stderr)
                sys.exit(1)
            ext = Path(img).suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                print(f"WARNING: Unsupported file format '{ext}', will try anyway: {img}", file=sys.stderr)
            file_size = Path(img).stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                print(
                    f"ERROR: Image file too large: {file_size / (1024 * 1024):.1f} MB "
                    f"(max {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB): {img}",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            # Best-effort URL validation (non-fatal)
            if not validate_url_is_image(img):
                print(f"WARNING: URL does not appear to point to an image, proceeding anyway: {img}", file=sys.stderr)

    if len(args.images) > MAX_IMAGES:
        print(f"WARNING: {len(args.images)} images provided (recommended max {MAX_IMAGES}). "
              "This may exceed token limits.", file=sys.stderr)

    try:
        result = analyze_images(
            image_paths=args.images,
            question=args.question,
            api_base=args.api_base,
            api_key=args.api_key,
            model=args.model,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output_json:
        print(json.dumps({"analysis": result}, ensure_ascii=False, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main()
