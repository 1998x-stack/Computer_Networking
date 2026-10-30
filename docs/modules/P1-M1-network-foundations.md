# P1-M1：互联网体系结构与分组交换勘误

> 2026-10-30；依赖 P0-M3（feat/p0-m3-deterministic-docs），在其基础上建立本模块分支。
> 这是**原笔记的校订与额外解释**，不是声称已完成 TCP/IP 协议栈实现。

## 目标和范围

逐篇检查第一章 1.1–1.3 的 8 个知识条目：互联网定义与服务、协议、接入网、物理介质、分组交换、电路交换和 ISP 互联。保留现有教材章节结构，修正描述中的普遍化、绝对化与历史事实混淆；增补可复算例子、跨层职责和可直接运行的**离线模型**。

本批次**不改**第 1 章 1.4–1.8 或其他八章；这些内容留给 P1-M2/M3 或后续主题。

## 具体勘误追踪表

| 文件 | 原有笔记中的问题 | 本次处理及外部依据 |
| --- | --- | --- |
| 1.1.1 A Nuts-and-Bolts Description | IP 全局唯一、TCP 保证永不丢包、IP 自己执行选路、路由与转发混淆、流量控制/拥塞控制混同 | 更正私有地址与 NAT、路由和转发角色，区分 OSPF 与 BGP（RFC 1918/3022/2328/4271/4632） |
| 1.1.2 A Services Description | TCP 绝对保证成功；UDP 简化为只适合不敏感应用；RFC 数量过时 | 补充字节流边界与出错语义，区分 TCP/UDP（RFC 9293、768） |
| 1.1.3 What Is a Protocol | 将 HTTP 请求与底层连接建立全部混为 HTTP 的职责 | 分离 HTTP 语义与 TCP/TLS/QUIC 传输（RFC 9110、768） |
| 1.2.1 Access Networks | 历史速率描述缺少年代语境；LTE 描述过简 | 标出历史示例和接入速率与端到端吞吐量的不同 |
| 1.2.2 Physical Media | 把可达距离当固定指标；卫星传播时延缺乏路径假设 | 补充距离/传播速度与发送时延模型，并使用带假设的 GEO 算例 |
| 1.3.1 Packet Switching | 2L/R 未说明等速/无其他开销条件；成本论断绝对化 | 增补异速链路、存储转发与流水线示例，明确排队边界条件 |
| 1.3.2 Circuit Switching | 预留资源被描述为绝对无抖动；链路跳数不影响总时延的结论缺条件 | 标明简化 TDM 模型与 10.5s 的成立假设 |
| 1.3.3 A Network of Networks | 把商业关系简化成一律免费对等互联；教材数量当成现状 | 增补 IXP/transit/peering/AS/BGP，明确技术与政策多因素（RFC 4271、4632） |

## 可运行的离线模型

代码：examples/network_foundations.py；回归测试：tests/test_network_foundations.py。

~~~bash
# 两跳存储转发：12,000 bit，两个 1 Mbps 链路 → 0.024000 seconds
python examples/network_foundations.py packet --bits 12000 --rates 1000000 1000000

# 非等速链路：1 Mbps 与 2 Mbps → 0.018000 seconds
python examples/network_foundations.py packet --bits 12000 --rates 1000000 2000000

# TDM：640,000 bit，1.536 Mbps / 24 时隙，0.5 s 建链 → 10.500000 seconds
python examples/network_foundations.py circuit --bits 640000 --rate 1536000 --slots 24 --setup 0.5

# 最长前缀匹配：192.0.2.145 落在 /25，因此输出 C
python examples/network_foundations.py forward --address 192.0.2.145 --route 0.0.0.0/0 A --route 192.0.2.0/24 B --route 192.0.2.128/25 C

# 标准库回归测试
python -m unittest tests.test_network_foundations -v
~~~

上述时间计算为**理想模型**，不含排队、链路/协议头部开销、处理、重传或未明确列出的传播时延；它们不能预测实际公网网络性能。最长前缀匹配仅演示 FIB 查找，不计算 OSPF/BGP 路径，也不实现 ECMP。

## 信息来源与校订边界

仓库已有内容：按教材第 7 版章节结构组织的原有中文笔记。原文中哪些论述不准确已在上表列出；**新增补充**包含独立的公式推导、局部示例和以下公开协议规范，而非源文件已经支持的结论。

- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918)：IPv4 私有地址空间。
- [RFC 3022](https://www.rfc-editor.org/rfc/rfc3022)：传统 NAT 与 NAPT。
- [RFC 2328](https://www.rfc-editor.org/rfc/rfc2328)：OSPFv2 链路状态和最短路径树。
- [RFC 4271](https://www.rfc-editor.org/rfc/rfc4271)：BGP-4 AS 间可达性及策略。
- [RFC 4632](https://www.rfc-editor.org/rfc/rfc4632)：CIDR、最长前缀匹配。
- [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293)：TCP 字节流与可靠传输。
- [RFC 768](https://www.rfc-editor.org/rfc/rfc768)：UDP 数据报。
- [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110)：HTTP 语义。
- [Kurose–Ross 作者第 1 章资源](https://gaia.cs.umass.edu/kurose_ross/videos/1/)：本章主题范围和教学组织。

## 完成定义

- [x] 8 篇 1.1–1.3 原文完成定点校订与新增补充
- [x] 可运行的存储转发、TDM、RFC1918 与最长前缀匹配离线案例已提交
- [x] 新增针对模型边界、错误输入及 CLI 的单元测试
- [x] P0-M3 的 Markdown → HTML 构建器同步生成 8 个章节页，并通过完整单元测试和一致性检查（GitHub Actions）
- [ ] PR 人工审查、浏览器公式渲染抽查与合并
- [ ] 1.4 性能内容及其他章节的系统性勘误（后续模块）

P0-M3 尚未合并时，本模块 PR 以 P0-M3 分支为合并目标；等其合并到 main，再将该 PR 调整为以 main 为目标并重新验收。
