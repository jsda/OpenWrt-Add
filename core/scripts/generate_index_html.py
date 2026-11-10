
#!/usr/bin/env python3
"""Generate root and per-architecture HTML indexes for an OpenWrt APK feed."""

from __future__ import annotations
import html
import os
import pathlib
import sys
import urllib.parse
from datetime import datetime

DEFAULT_GITHUB_REPOSITORY = "QiuSimons/OpenWrt-Add"
RELEASE_TAG = "latest-packages"


def github_repository() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if "/" in repo:
        return repo
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "").strip()
    return f"{owner}/OpenWrt-Add" if owner else DEFAULT_GITHUB_REPOSITORY


def render_root(arches: list[str], repository: str) -> str:
    cards = "\n".join(
        f'<div class="arch-item"><a href="{urllib.parse.quote(a, safe="")}/"><strong>{html.escape(a)}</strong></a>'
        f'<small><a href="{urllib.parse.quote(a, safe="")}/packages.adb">packages.adb</a></small></div>'
        for a in arches
    )
    release = (
        f"https://github.com/{urllib.parse.quote(repository, safe='/')}"
        f"/releases/tag/{urllib.parse.quote(RELEASE_TAG, safe='')}"
    )
    return f'''<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="OpenWrt-Add 第三方 APK 软件源与 LuCI 插件二进制包。">
<title>OpenWrt-Add APK Feed</title>
<style>
*{{box-sizing:border-box}} body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.65;max-width:900px;margin:36px auto;padding:0 18px;color:#24292f;background:#f6f8fa}}
.card{{background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:26px;margin-bottom:22px;box-shadow:0 1px 3px #1f23280d}}
h1,h2{{color:#1f2328;border-bottom:1px solid #d0d7de;padding-bottom:8px}} h1{{font-size:1.6rem}} h2{{font-size:1.2rem;margin-top:28px}}
a{{color:#0969da;text-decoration:none}}a:hover{{text-decoration:underline}}
pre{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:7px;padding:16px;overflow-x:auto}}
code{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.9em}}
.arch-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;margin-top:12px}}
.arch-item{{background:#f6f8fa;border:1px solid #d0d7de;border-radius:7px;padding:12px;text-align:center;overflow-wrap:anywhere}}
.arch-item small{{display:block;margin-top:3px}} .muted{{color:#656d76;font-size:.9rem}}
button{{padding:8px 12px;border:1px solid #d0d7de;border-radius:6px;background:#f6f8fa;cursor:pointer}}
@media(max-width:520px){{.card{{padding:18px}}}}
</style></head><body><main class="card">
<h1>OpenWrt-Add APK 软件源</h1>
<p>自用 OpenWrt 第三方软件包与 LuCI 插件二进制源，适配 OpenWrt apk 包管理器。</p>
<h2>路由器在线配置命令</h2>
<p class="muted">软件源及公钥地址根据当前页面 URL 自动生成，适用于 GitHub Pages 项目页和自定义域名。</p>
<pre><code id="commands">正在生成配置命令……</code></pre><button id="copy" type="button">复制配置命令</button>
<h2>支持的硬件架构</h2><div class="arch-grid">{cards}</div>
<h2>离线资源与公钥</h2><ul>
<li>公钥文件：<a href="./keys/custom-feed.rsa.pub">keys/custom-feed.rsa.pub</a></li>
<li>ImageBuilder 离线包：<a href="{html.escape(release, quote=True)}">GitHub Releases：openwrt-add-apks-bundle.tar.gz</a></li>
</ul></main>
<script>
(() => {{
  const base = new URL("./", location.href).href.replace(/\\/$/, "");
  const key = new URL("keys/custom-feed.rsa.pub", base + "/").href;
  const cmd = [
    "# 1. 导入软件源公钥",
    `wget -qO /etc/apk/keys/custom-feed.rsa.pub "${{key}}"`,
    "",
    "# 2. 添加当前设备架构对应的软件源",
    `echo "${{base}}/$(apk --print-arch)" > /etc/apk/repositories.d/custom-feed.list`,
    "",
    "# 3. 更新并安装",
    "apk update",
    "apk add <包名>"
  ].join("\\n");
  document.getElementById("commands").textContent = cmd;
  document.getElementById("copy").addEventListener("click", async () => {{
    const btn = document.getElementById("copy");
    try {{ await navigator.clipboard.writeText(cmd); btn.textContent = "已复制"; }}
    catch (_) {{ btn.textContent = "请手动复制上方命令"; }}
  }});
}})();
</script></body></html>'''


def file_mtime(path: pathlib.Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().strftime(
        "%Y-%m-%d %H:%M:%S %Z"
    )


def render_arch(arch: str, directory: pathlib.Path) -> str:
    files = sorted(
        (p for p in directory.glob("*.apk") if p.is_file()),
        key=lambda p: p.name.casefold(),
    )
    rows = []
    for apk in files:
        name = html.escape(apk.name)
        href = urllib.parse.quote(apk.name, safe="")
        modified = html.escape(file_mtime(apk))
        rows.append(
            f'<tr><td class="filename"><a href="{href}">{name}</a></td>'
            f'<td class="mtime">{modified}</td></tr>'
        )
    if not rows:
        rows.append('<tr><td colspan="2" class="empty">当前架构目录暂无 APK 文件。</td></tr>')

    return f'''<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{html.escape(arch)} 架构的 OpenWrt-Add APK 软件包列表。">
<title>{html.escape(arch)} - OpenWrt-Add APK Feed</title>
<style>
*{{box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.6;max-width:1000px;margin:36px auto;padding:0 18px;color:#24292f;background:#f6f8fa}}
.card{{background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:24px;box-shadow:0 1px 3px #1f23280d}}
h1{{border-bottom:1px solid #d0d7de;padding-bottom:9px;overflow-wrap:anywhere}}a{{color:#0969da;text-decoration:none}}a:hover{{text-decoration:underline}}
.back{{display:inline-block;margin-bottom:14px}}.meta{{color:#656d76;font-size:.9rem}}
input{{width:100%;padding:10px 13px;font-size:14px;border:1px solid #d0d7de;border-radius:6px;margin:12px 0 16px}}
table{{width:100%;border-collapse:collapse;table-layout:fixed}}th,td{{padding:9px 10px;border-bottom:1px solid #eaeef2;text-align:left}}
th{{background:#f6f8fa}}tbody tr:nth-child(even){{background:#fcfcfc}}
.filename{{overflow-wrap:anywhere;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:13px}}
.mtime{{width:245px;color:#656d76;font-size:12px}}.empty{{text-align:center;color:#656d76;padding:24px}}
@media(max-width:620px){{.card{{padding:16px}}.mtime{{width:145px}}th,td{{padding:8px 6px}}}}
</style></head><body><main class="card">
<a href="../" class="back">← 返回软件源首页</a>
<h1>架构目录：{html.escape(arch)}（{len(files)} 个包）</h1>
<p class="meta">索引文件：<a href="packages.adb"><strong>packages.adb</strong></a></p>
<input type="search" id="filter" placeholder="搜索软件包名称（如 sing-box、mosdns）..." aria-label="搜索软件包">
<table><thead><tr><th>软件包</th><th class="mtime">文件更新时间（构建环境本地时区）</th></tr></thead>
<tbody id="pkg-list">{''.join(rows)}</tbody></table>
</main><script>
document.getElementById("filter").addEventListener("input", function () {{
  const q = this.value.trim().toLocaleLowerCase();
  document.querySelectorAll("#pkg-list tr").forEach(row => {{
    row.hidden = !row.textContent.toLocaleLowerCase().includes(q);
  }});
}});
</script></body></html>'''


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: generate_index_html.py <public_dir>", file=sys.stderr)
        return 1
    public_dir = pathlib.Path(sys.argv[1]).resolve()
    if not public_dir.is_dir():
        print(f"Error: {public_dir} is not a directory", file=sys.stderr)
        return 1

    arches = sorted(
        (p.name for p in public_dir.iterdir()
         if p.is_dir() and p.name != "keys" and not p.name.startswith(".")),
        key=str.casefold,
    )
    repo = github_repository()
    (public_dir / "index.html").write_text(render_root(arches, repo), encoding="utf-8")
    for arch in arches:
        directory = public_dir / arch
        (directory / "index.html").write_text(
            render_arch(arch, directory), encoding="utf-8"
        )
    print(f"[INFO] Generated root index and {len(arches)} architecture indexes (repository: {repo}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
