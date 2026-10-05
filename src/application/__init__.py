# SPDX-License-Identifier: Apache-2.0
"""application 包 —— Facade 层（稳定对外入口）。

分层约定（写操作）：
  router  →  application.*  →  domain service
  - router：鉴权、酒店作用域、参数解析、``ok()`` / HTTP 映射
  - application：编排、事务边界（``commit``/``rollback``）、跨 service 调用
  - domain service：单域业务规则；生命周期 ``emit`` 可在此发出

读列表可暂时直调 service；**新写路径禁止绕开 application**。

部分子模块由生成器产出透传包装；文件末尾 ``# --- orchestrated ---`` 段为手写编排，
重新生成时勿覆盖该段。
"""
