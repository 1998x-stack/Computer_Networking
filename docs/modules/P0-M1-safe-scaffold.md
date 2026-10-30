# P0-M1：无损目录生成与仓库保护

## 目标和边界

旧 main.py 的目录生成函数使用写入模式重建已有 Markdown、Python 骨架和 README，重复运行存在清空知识笔记的风险。本模块只改变“缺失文件的创建方式”和回归测试，不改写现有章节正文，也不承担 Markdown → HTML 的转换任务。

## 实际代码改动

- main.py：保留原有 structure 九章清单，改为薄 CLI 入口；默认根目录为 main.py 所在目录。
- scripts/scaffold.py：生成**预期文件清单**，只使用独占文件创建模式 x 新建缺失文件；已经存在的文件跳过。
- tests/test_scaffold.py：通过 tempfile 运行所有测试，不污染仓库。
- .github/workflows/scaffold.yml：每次相关提交跑 unittest，并检查仓库现有章节文件是否齐全。

## 使用方式

从仓库根目录执行：

~~~bash
python main.py --dry-run
python main.py --check
python main.py
python -m unittest discover -s tests -v
~~~

- --dry-run：只输出缺失数量和部分示例，不创建任何文件，成功退出码 0。
- --check：只检查存在性，不写入；若缺失任一必需文件返回退出码 1。
- 不带参数：仅补齐不存在的 Python / Markdown / README 文件；不会修改已存在文件内容。
- --root PATH：在指定目录中运行，建议在临时目录测试，而不是更改个人工作区。
- 默认输出路径与运行命令时的当前工作目录无关。

## 兼容性和约束

- 保留原结构的章节命名与 00_、01_ 等序号规则；预期总数：212 × 2 + README = 425 文件。
- 若 README 已存在，即使导航内容可能过时，也暂时保留原文；统一生成导航属于 P0-M3。
- 已有 HTML 文件不属于这一模块的生成范围。
- --check 只验证清单中文件是否存在，并不验证文章内容是否正确，也不检查 HTML 是否最新。
- 意外的路径冲突（原本应为文件的位置却是目录）会报错，不会删除覆盖。
- 遇到并发写入，同名文件被其他进程先创建时跳过，从而避免覆盖。

## 验收清单

- [x] 保留旧 structure 与章节路径格式
- [x] 安全生成器不覆盖已有文件
- [x] 默认运行、dry-run、check 有清晰的行为与退出码
- [x] 临时目录中验证首次生成、重复运行、保护笔记、缺失检查和 CLI 行为的测试代码
- [x] 增加 GitHub Actions 自动测试配置
- [ ] PR 的 CI 测试执行通过
- [ ] 人工审查并合并 PR

回滚方式：在 PR 未合并前只需关闭 PR 或删除功能分支；main 不受影响。合并后可 revert 对应提交，但不应重新启用旧式覆盖写入逻辑。
