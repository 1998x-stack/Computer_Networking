# P0-M2：网页安全与依赖治理

## 改造范围

- 迁移所有静态知识页面的旧式第三方脚本引用；保持正文、链接、公式和章节命名不变。
- 重构文章评论编辑与导出逻辑，让编辑后的内容能够以 HTML 文件形式保存。
- 加入 Python + Node.js 回归测试和 GitHub Actions。
- 记录第三方教材与 CDN 授权/供应链的尚未解决风险，不把记录等同于授权。

## 安全迁移

- 2026-10-30 基线包含 214 个 HTML 文件，其中 212 个章节页面与 README.html 共 213 个包含旧模板；index.html 未包含旧模板。
- 所有 213 个旧模板页面移除了 polyfill.io/v3/polyfill.min.js?features=es6 远程执行引用。
- highlight.js 11.4.0 保留原 CDN 与版本，但脚本改为 defer；不再在 DOM 解析完成前调用 highlightAll()。
- markdown.js 通过 defer 在 MathJax 之前加载，提前初始化配置；MathJax 固定为 3.2.2 并使用 defer，避免之前 async 加载导致的顺序竞争。MathJax 本身自动进行初次公式排版。
- scripts/migrate_html_security.py 是可重复运行的迁移器；运行 --check 只读检查，不会覆盖笔记或网页。
- 页面仍引用外部的 cdnjs、jsDelivr、Google Fonts；**这次没有实现资源自托管或 SRI**。剩余依赖审计和离线构建纳入 P0-M3。

## 评论交互和导出

- 输入采用 textContent，防止评论被当作 HTML 执行。
- 回车、失去焦点仅提交一次，Escape 取消评论；不修改现有文档源文件。
- 导出时克隆整篇 .container 文章，保留代码、列表、表格、公式 DOM、图片、原有评论及顺序。
- 去除正在编辑的输入框及 script 标签；不再重复追加已包含在文章 DOM 内的评论。
- 保存为完整 HTML 文档，并内嵌基本排版 CSS，包含标题、字符集等。
- 将相对图片路径和导航链接转换为以原页面为基准的绝对 URL；**导出的外部图片、链接和部分动态渲染公式资源仍可能需要联网**，并非完全离线快照。离线资源内联不在本模块范围。

## 第三方教材 PDF 的版权状态

仓库根目录包含 Computer Networking _ A Top Down Approach, 7th, converted.pdf。

- 作者：James F. Kurose、Keith W. Ross；出版社：Pearson。
- 检查结果：**没有在本次审查材料中发现授予该仓库公开再分发整本教材的许可证明**。这不等同于断定用户没有授权，但不能假定仓库 MIT License 对第三方教材有效。
- 当前动作：**没有删除、移动或修改 PDF**，仅记录许可审查为 **PENDING / 未核实**。
- 待仓库所有者确认合法授权。如果不能确认，建议从公开仓库删除 PDF 并提供出版社合法出版页面；对于已公开的 Git 历史还需单独评估处理方式。
- 在状态明确前，不应将该仓库的教材 PDF 声明为开放许可资源或对外重新分发。

参考出版社第 7 版页面：
https://www.pearson.com/se/Nordics-Higher-Education/subject-catalogue/computer-science/ross-computer-networking-a-top-to-down-approach-ge.html

## 本模块验收命令

~~~bash
python scripts/migrate_html_security.py --check
python -m unittest discover -s tests -v
node --test tests/test_markdown.cjs
python main.py --check
~~~

预期：HTML 迁移器报告 stale=0、Python/Node 回归测试通过、原 425 个章节 Python/Markdown/README 文件完整。

## 交付与剩余问题

- [x] 全部旧模板 HTML 已迁移；index.html 原样保留。
- [x] markdown.js 修复输入与导出逻辑。
- [x] 增加迁移器、Python/Node 回归测试及 CI。
- [x] 记录 PDF 授权状态与下一步决策路径。
- [ ] 人工审查并合并 PR。
- [ ] PDF 再分发许可最终确认或后续下架处理（需要所有者提供授权依据或批准后续处理）。
- [ ] 真实浏览器多端视觉检查（自动测试目前主要覆盖 DOM 与导出逻辑）。

后续：P0-M3 使用单一的 Markdown → HTML 构建流程，并将外部资源与发布安全纳入持续校验。
