#!/usr/bin/env python3
"""
将当前目录下的 .md 文件转换为 PDF。
支持：中文、图片（相对路径）、LaTeX 数学公式（$...$ 和 $$...$$）、代码块。

使用方法：
  1. 确保已安装: python3, markdown 库 (pip install markdown)
  2. 在 Claude Code 中运行: python3 md2pdf.py
  3. 脚本会生成 .html 文件，然后通过 Playwright 渲染为 PDF

依赖：
  - Python 3 + markdown 库
  - Playwright（由 Claude Code 的 MCP 工具提供）
  - 网络连接（加载 MathJax CDN）
"""

import re
import sys
import markdown
from pathlib import Path


def protect_math(text):
    """把 LaTeX 数学公式提取为占位符，防止被 markdown 引擎破坏。"""
    placeholders = {}

    # display math: $$...$$
    def save_display(m):
        key = f"MATHDISPLAY{len(placeholders)}END"
        placeholders[key] = m.group(1)
        return key

    text = re.sub(r'\$\$\s*(.*?)\s*\$\$', save_display, text, flags=re.DOTALL)

    # inline math: $...$
    def save_inline(m):
        key = f"MATHINLINE{len(placeholders)}END"
        placeholders[key] = m.group(1)
        return key

    text = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', save_inline, text)

    return text, placeholders


def restore_math(html, placeholders):
    """将占位符还原为 MathJax 可识别的标签。"""
    for key, expr in placeholders.items():
        if key.startswith("MATHDISPLAY"):
            html = html.replace(
                key,
                f'<div style="text-align:center;margin:1em 0;">$${expr}$$</div>',
            )
        elif key.startswith("MATHINLINE"):
            html = html.replace(key, f"${expr}$")
    return html


def md_to_html(md_text):
    """把 Markdown 转为完整 HTML 页面，图片保持相对路径。"""
    protected, placeholders = protect_math(md_text)

    extensions = ["fenced_code", "tables", "nl2br", "sane_lists"]
    body = markdown.markdown(protected, extensions=extensions)

    body = restore_math(body, placeholders)

    # 给 <img> 添加样式（不改变 src，保持相对路径供 HTTP 服务器提供）
    body = re.sub(
        r'<img\s+alt="([^"]*)"\s+src="([^"]*)"',
        r'<img alt="\1" src="\2" style="max-width:85%;display:block;margin:1em auto;"',
        body,
    )

    return HTML_TEMPLATE.replace("{{BODY}}", body)


# ── HTML 模板 ──────────────────────────────────────────────
HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  @page { size: A4; margin: 20mm 18mm; }
  body {
    font-family: "PingFang SC","Hiragino Sans GB","Microsoft YaHei",
                 "Noto Sans CJK SC","WenQuanYi Micro Hei",sans-serif;
    font-size: 13px; line-height: 1.8; color: #222;
  }
  h1,h2,h3,h4 { color:#1a1a1a; margin-top:1.2em; margin-bottom:0.6em;
                 page-break-after:avoid; }
  h1 { font-size:22px; text-align:center; }
  h2 { font-size:18px; border-bottom:1px solid #ddd; padding-bottom:4px; }
  h3 { font-size:15px; }
  p  { margin:0.6em 0; }
  img { display:block; margin:1em auto; max-width:85%;
        page-break-inside:avoid; }
  code {
    font-family:"SF Mono","Menlo","Monaco","Consolas",monospace;
    background:#f4f4f4; padding:2px 5px; border-radius:3px;
    font-size:0.9em;
  }
  pre {
    background:#f8f8f8; border:1px solid #e0e0e0; border-radius:5px;
    padding:12px 16px; overflow-x:auto; font-size:12px; line-height:1.5;
    page-break-inside:avoid;
  }
  pre code { background:none; padding:0; }
  hr { border:none; border-top:1px solid #ccc; margin:1.5em 0; }
  table { border-collapse:collapse; margin:1em 0; width:100%; }
  th,td { border:1px solid #ccc; padding:6px 10px; text-align:left; }
  th { background:#f0f0f0; }
</style>
<script>
window.MathJax = {
  tex: { inlineMath:[['$','$']], displayMath:[['$$','$$']],
         processEscapes:true },
  svg: { fontCache:'global' },
  startup: {
    pageReady: () => MathJax.startup.defaultPageReady().then(
      () => { window.__MATHJAX_DONE = true; }
    )
  }
};
</script>
<script async
  src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js">
</script>
</head>
<body>
{{BODY}}
</body>
</html>
"""


def main():
    script_dir = Path(__file__).resolve().parent
    md_files = list(script_dir.glob("*.md"))

    if not md_files:
        print("当前目录下未找到 .md 文件")
        sys.exit(1)

    for md_file in md_files:
        print(f"[1/2] 读取 {md_file.name} ...")
        html = md_to_html(md_file.read_text(encoding="utf-8"))

        html_path = md_file.with_suffix(".html")
        html_path.write_text(html, encoding="utf-8")
        print(f"[2/2] 生成 {html_path.name}")

    print()
    print("下一步: 在 Claude Code 中用 Playwright 将 HTML 转为 PDF:")
    print("  1. python3 -m http.server 8899  (后台运行)")
    print("  2. browser_navigate -> http://localhost:8899/xxx.html")
    print("  3. 等待 ~10s 让 MathJax 渲染")
    print("  4. browser_run_code -> page.pdf({ path: 'xxx.pdf', ... })")


if __name__ == "__main__":
    main()
