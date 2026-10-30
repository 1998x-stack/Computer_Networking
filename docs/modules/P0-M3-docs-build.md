# P0-M3：可重复的文档构建与内容校验

## 交付范围

- 以九章内 **212 份章节 Markdown** 和仓库根目录的 README.md 为唯一文本来源，读取对应章节 .py 文件作为示例附录。
- 通过 scripts/build_docs.py 生成 **212 个章节 HTML + README.html + index.html = 214 页**。
- 使用固定版本 mistune 3.2.1、Python 3.11 和标准库进行可重复渲染，支持标题、表格、代码块、列表及 LaTeX/MathJax。
- 内建本地链接、图像及脚本路径验证，拒绝越过仓库根目录的相对路径及未列入清单的远程脚本主机。
- 在现有 HTML 安全迁移的基础上使用相同的延迟脚本加载方案；不引入 polyfill.io。
- 所有源 Markdown、Python、PDF 与外部许可文件保持原样。

## 安装与命令

~~~bash
python -m pip install -r requirements-docs.txt
python scripts/build_docs.py --check
python scripts/build_docs.py --write
python scripts/build_docs.py --check
python -m unittest discover -s tests -v
python main.py --check
~~~

- 默认运行（无参数）与 --check 都是只读检查，发现任何生成页不存在或与源码不同则退出码 1。
- --write **只更新发生变化的已生成 HTML 文件**（章节页面、README.html、index.html），不触碰笔记和 Python 骨架；安全起见拒绝覆盖 HTML 符号链接。
- 输出由已排序的章节路径、固定模板及固定版本的 Markdown 渲染器决定；重复执行 --write 结果不发生变化。
- 本地内部 Markdown 导航链接转为指向相应 HTML；章节页正文由其 .md 驱动，Python 文件作为下方附录。
- 可使用 --root 指向隔离的测试仓库。

## 代码设计

| 文件 | 职责 |
| --- | --- |
| scripts/build_docs.py | 收集 Markdown/Python、规范化元信息、HTML 渲染、索引生成、内部链接审计、构建/检查 |
| requirements-docs.txt | 锁定 Markdown 渲染器 |
| tests/test_build_docs.py | 只读、幂等、渲染、安全转义、缺失文件、损坏链接的回归测试 |
| .github/workflows/docs.yml | 每次相关改动执行全量一致性、安全迁移、P0-M1 和 P0-M2 回归测试 |
| style.css | 为自动生成的目录页面增加响应式覆盖规则 |

## 验收与安全边界

- [x] 214 个 HTML 页面由源码重新生成。
- [x] 脚本在 CI 中完成 --write 再 --check 验证。
- [x] 旧版安全迁移器 --check 验证通过。
- [x] 使用新建的单元测试验证确定性、链接检测、源文件保护和 HTML 转义。
- [x] 永久 CI 配置已提交。
- [ ] 人工审核合并 PR。
- [ ] 全量浏览器视觉回归、MathJax/Highlight 网络环境测试。

**限制：**
- 安全 HTML 渲染会转义 Markdown 中的原始 HTML 片段；确实需要嵌入自定义组件时，需要在未来设计受控扩展而非直接允许脚本执行。
- 这里验证的是 **相对路径是否存在** 以及远程脚本来源是否位于允许列表；不验证外部网站当前可访问性，也不验证 Markdown 文章的知识正确性或锚点 ID。
- 页面仍加载经限制版本的第三方 CDN 字体、代码高亮和 MathJax。此模块**没有实现完全离线资源打包、CSP 或 SRI**，应在后续安全强化任务中处理。
- PDF 版权审核仍处于 PENDING；构建流程不引用、分发或改写这份 PDF。

## CI 验收

- python main.py --check 检查 425 个章节源结构必需文件（包括 README）。
- python scripts/build_docs.py --check 检查 214 个生成 HTML 是否与源文件完全一致。
- python scripts/migrate_html_security.py --check 防止旧版不安全外部脚本重新出现。
- python -m unittest discover -s tests -v 运行历史和新增的回归测试。
- node --test tests/test_markdown.cjs 检验文章导出。

## 后续模块

P1-M1 从互联网基础知识纠错开始：明确 IP 地址作用、分组交换原理、路由与转发职责；每一处改动对应来源及验证例题。
