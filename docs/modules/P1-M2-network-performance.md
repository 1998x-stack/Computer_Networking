# P1-M2：网络时延、排队、丢包与吞吐量

> 2026-10-30 · 第 1 章 1.4 节 · 基于 P1-M1 分支创建堆叠 PR。
> 范围是**教材笔记勘误与数学/离线实验**，不实现真实 TCP/IP 栈，也不测量公网实时指标。

## 范围与依赖

- 读取与修正 1.4.1–1.4.4 四篇原有 Markdown；保留教材按章节组织的结构。
- 将原笔记中的适用条件不完整之处直接更正，并在各文档中独立增加推导、可复算例题和权威来源。
- 提供 examples/network_performance.py、tests/test_network_performance.py，均只用 Python 标准库。
- 通过 P0-M3 的 scripts/build_docs.py 从 Markdown 重新生成**恰好四个**章节 HTML，随后使用既有 CI 进行全站一致性检测。
- 由于 P0-M3 的 PR #3 和 P1-M1 的 PR #4 仍未合并，P1-M2 以 P1-M1 分支为 PR base，避免向 main 导入未审查的上游改动。

## 来源原文与勘误矩阵

| 源文件 | 发现的问题 | 本次更正 |
| --- | --- | --- |
| 1.4.1 Overview of Delay | 把传播与发送时延写成没有前提的微秒/毫秒范围；校园链路传播延迟示例误导 | 明确 L/R 与 d/v 的量纲、节点时延四项、200 m 与 200 km 示例 |
| 1.4.2 Queuing Delay and Packet Loss | 原文把 aL/R ≤ 1 概括为排队很小，并在接近 1 时说已经“超过速率” | 说明 ρ<1 仍可突发排队；ρ→1 时等待可增大；区分无限缓存和有限队列损失 |
| 1.4.3 End-to-End Delay | N 台路由器却只乘 N 条链路发送/传播延迟；traceroute 的 RTT 被误当每一跳时延 | N 个中间路由器对应 N+1 链路；异质链路公式；traceroute 的往返探测局限 |
| 1.4.4 Throughput | 十条下载流直接得 500 kbps，未说明共享容量 R；宣称核心拥塞罕见 | 说明 R=5 Mbps、公平等份、源/目标接入瓶颈与应用 goodput 统计口径 |

上述矩阵依据**本仓库原有笔记**。新增部分使用第 1 章原有理论框架加独立推导，不把通用公式误当所有网络都适用。

## 可复算的 4 类离线实验

1. **发送与传播**：一个 12,000-bit 数据包以 1 Mbps 发送需 12 ms，假设传播速度 2×10^8 m/s、链路 200 km 时传播 1 ms；只计这两项合计 13 ms。
2. **跨三链路、两路由器**：发送 36 ms、传播 3 ms、路由处理 4 ms、排队 6 ms，共 49 ms。
3. **有限缓冲 FIFO**：每包 1000 bit、速率 1000 bps；0、0、0、1、1 秒到达，等待容量 1 包（另有 1 包发送中），接受 3、丢弃 2，丢包率 40%。假定同时间完成事件先于新到达。
4. **等份共享**：10 个持续活跃的流分享 5 Mbps，假设无额外瓶颈且公平等分，每流容量上界 500 kbps；实际应用 goodput 不一定达到该值。

另加入 **M/D/1 稳态参考公式**：泊松到达、固定包长、单服务器、无限缓冲且 ρ < 1 时，E[Wq] = ρ(L/R) / [2(1−ρ)]。在 ρ=0.8、L/R=0.01 秒时为 20 ms，在 ρ=0.95 时为 95 ms。它不是对 FIFO 仿真的统计结果，也不适用于任意真实网络或 ρ≥1。

## 验收

~~~bash
python -m pip install -r requirements-docs.txt
python -m unittest discover -s tests -v
python scripts/build_docs.py --check
python scripts/migrate_html_security.py --check
python main.py --check
node --test tests/test_markdown.cjs

python examples/network_performance.py delay --bits 12000 --rates 1000000 1000000 --propagation 0.001 0.001
python examples/network_performance.py queue --bits 1000 --rate 1000 --arrivals 0 0 0 1 1 --capacity 1
python examples/network_performance.py share --source 10000000 --destination 10000000 --shared 5000000 --flows 10
~~~

检查内容：数学边界与单位、路由器数和链路数、同时间戳 FIFO 事件顺序、零等待容量、异常输入、吞吐量上界、CLI、先前模块回归、Markdown→HTML 确定性。

- [x] 四篇 Markdown 直接勘误与教学补充。
- [x] Python 性能模型与单元测试提交。
- [ ] 四个 HTML 与 Markdown 同步构建并通过全部 CI。
- [ ] 人工浏览器公式与排版验证。
- [ ] 堆叠 PR 经过审核并按顺序合并。

## 标准与边界

- [RFC 7567](https://www.rfc-editor.org/rfc/rfc7567) — IETF 关于主动队列管理（AQM）的建议；用于说明队列管理、延迟与拥塞标记，**并非规定本项目 FIFO 仿真**。
- [RFC 5837](https://www.rfc-editor.org/rfc/rfc5837) — ICMP 中接口与下一跳信息扩展，用于解释 traceroute 响应中的识别限制。
- Kurose–Ross, Computer Networking: A Top-Down Approach, 第 1 章 1.4 节 — 章节范围和基本网络性能框架。该教材 PDF 的公开再分发授权仍属独立待处理事项。

**后续模块 P1-M3**：分层体系、封装解封装、网络安全与历史内容的交叉核验；保持独立原文勘误及实验。
