"""
进阶集成测试：/api/v1/encode
运行：
    # 从backend目录运行：
    cd Code/backend && pytest -m integration -q
    # 或者运行所有测试：
    cd Code/backend && pytest -q
"""
from __future__ import annotations
import asyncio
import sys
import os
from typing import List

import numpy as np
import pytest
from fastapi.testclient import TestClient

# 尝试导入hypothesis，如果没有安装则跳过相关测试
try:
    from hypothesis import given, settings, strategies as st
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False

# 添加backend目录到路径，以便导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from main import app

client = TestClient(app, raise_server_exceptions=False)

# ---------- 公用 ---------- #

pytestmark = pytest.mark.integration

def orthogonal(H: List[List[int]], G: List[List[int]]) -> bool:
    """验证H和G是否满足正交条件：H·G^T = 0"""
    Hn = np.asarray(H, dtype=int) % 2
    Gn = np.asarray(G, dtype=int) % 2
    return bool(np.all((Hn @ Gn.T) % 2 == 0))


def codeword_valid(H, cw) -> bool:
    """验证码字是否满足校验方程：H·cw = 0"""
    Hn = np.asarray(H, dtype=int) % 2
    cw = np.asarray(cw, dtype=int) % 2
    return bool(np.all((Hn @ cw) % 2 == 0))


# ---------- 1. 最小合法图 ---------- #

def test_encode_minimal_graph():
    """测试最小合法图形的编码"""
    req = {
        "nodes": [
            {"id": "V0", "type": "variable"},
            {"id": "V1", "type": "variable"},
            {"id": "C0", "type": "check"},
        ],
        "edges": [
            {"fromId": "V0", "toId": "C0"},
            {"fromId": "V1", "toId": "C0"},
        ]
    }
    r = client.post("/api/v1/encode", json=req)
    assert r.status_code == 200, r.text
    d = r.json()

    # 基本字段
    for f in ("h_matrix", "g_matrix", "k", "n", "m", "code_rate"):
        assert f in d, f"缺少字段 {f}"

    # 正交 & 码字检查
    assert orthogonal(d["h_matrix"], d["g_matrix"])
    assert pytest.approx(d["code_rate"]) == d["k"] / d["n"]

    # 生成随机信息位进行编码测试
    info_bits = np.random.randint(0, 2, size=d["k"]).tolist()
    r2 = client.post("/api/v1/encode", json={**req, "info_bits": info_bits})
    assert r2.status_code == 200
    d2 = r2.json()

    # 验证码字是否正确
    assert "codeword" in d2, "返回数据缺少码字"
    assert codeword_valid(d2["h_matrix"], d2["codeword"]), "码字不满足校验方程"


# ---------- 2. 随机图（Hypothesis 100 个） ---------- #

def _random_tanner_graph(m: int, n: int, rng=None):
    """生成 rank=m 的随机 H，并转 Tanner 图"""
    if rng is None:
        rng = np.random.default_rng(42)

    H = rng.integers(0, 2, size=(m, n))
    while np.linalg.matrix_rank(H % 2) < m:
        H = rng.integers(0, 2, size=(m, n))
    nodes = ([{"id": f"V{i}", "type": "variable"} for i in range(n)] +
             [{"id": f"C{j}", "type": "check"} for j in range(m)])
    edges = [{"fromId": f"V{i}", "toId": f"C{j}"}
             for j in range(m) for i in range(n) if H[j, i] == 1]
    return nodes, edges, H

if HYPOTHESIS_AVAILABLE:
    @pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="Hypothesis not installed")
    @settings(max_examples=100, deadline=None)        # deadline=None 免超时终止
    @given(m=st.integers(min_value=3, max_value=6),
           n=st.integers(min_value=6, max_value=12))
    def test_encode_random_graph_hypothesis(m, n):
        """使用hypothesis进行随机图测试"""
        if n <= m:
            pytest.skip("需要 n > m 的条件")

        nodes, edges, H_ref = _random_tanner_graph(m, n)
        resp = client.post("/api/v1/encode", json={"nodes": nodes, "edges": edges})
        assert resp.status_code == 200
        out = resp.json()

        assert orthogonal(out["h_matrix"], out["g_matrix"])

        # 使用随机信息位测试编码
        info_bits = np.random.randint(0, 2, size=out["k"]).tolist()
        resp2 = client.post("/api/v1/encode", json={
            "nodes": nodes,
            "edges": edges,
            "info_bits": info_bits
        })
        assert resp2.status_code == 200
        out2 = resp2.json()
        assert codeword_valid(out2["h_matrix"], out2["codeword"])
else:
    def test_random_graphs_simple():
        """非hypothesis下的随机图测试"""
        # 测试10个不同大小的随机图
        for m, n in [(3, 6), (4, 8), (5, 10)]:
            nodes, edges, H_ref = _random_tanner_graph(m, n)
            resp = client.post("/api/v1/encode", json={"nodes": nodes, "edges": edges})
            assert resp.status_code == 200
            out = resp.json()
            assert orthogonal(out["h_matrix"], out["g_matrix"])


# ---------- 3. H + info_bits 直接模式 ---------- #

def test_encode_h_direct():
    """测试直接提供H矩阵和信息位的模式"""
    H = np.array([[1, 0, 1, 1],
                  [0, 1, 1, 0]], dtype=int).tolist()
    info_bits = [1, 0]          # k = n - m = 2

    r = client.post("/api/v1/encode", json={
        "h_matrix": H,
        "info_bits": info_bits
    })
    assert r.status_code == 200
    d = r.json()

    assert orthogonal(H, d["g_matrix"])
    assert codeword_valid(H, d["codeword"])


# ---------- 4. 并发一致性 ---------- #

@pytest.mark.integration
def test_encode_concurrent_threadpool():
    """20 并发请求返回内容都应满足正交性"""
    from concurrent.futures import ThreadPoolExecutor

    def do_call(i):
        H = [[1, 1, i & 1], [0, 1, (i >> 1) & 1]]  # 不同小矩阵
        resp = client.post("/api/v1/encode", json={
            "h_matrix": H,
            "info_bits": [1] * (len(H[0]) - len(H))
        })
        assert resp.status_code == 200
        d = resp.json()
        assert orthogonal(H, d["g_matrix"])
        assert "codeword" in d
        return d["codeword"]

    # 使用ThreadPoolExecutor替代asyncio
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(do_call, range(20)))

    # 所有 codeword 长度一致
    ln = len(results[0])
    assert all(len(cw) == ln for cw in results)


# ---------- 5. 性能 / 大矩阵（慢测） ---------- #

@pytest.mark.slow
@pytest.mark.timeout(20)
def test_encode_large_sparse():
    """测试大规模稀疏矩阵性能"""
    m, n, density = 64, 128, 0.04
    H_sparse = np.random.binomial(1, density, size=(m, n)).tolist()
    info_bits = np.random.randint(0, 2, size=n - m).tolist()

    r = client.post("/api/v1/encode", json={
        "h_matrix": H_sparse,
        "info_bits": info_bits
    })
    assert r.status_code == 200
    d = r.json()
    assert orthogonal(d["h_matrix"], d["g_matrix"])   # 仍通过


# ---------- 6. 错误分支 ---------- #

@pytest.mark.parametrize("payload, should_pass", [
    ({}, False),                                 # 空
    ({"nodes": [], "edges": []}, False),         # 缺变量
    ({"h_matrix": [[1, 0], [0, 1]]}, True),     # 只有H是允许的
    ({"h_matrix": [[1, 0]], "info_bits": [1, 0]}, False),  # info_bits 太长
])
def test_encode_bad_request(payload, should_pass):
    """测试错误请求处理"""
    r = client.post("/api/v1/encode", json=payload)
    if should_pass:
        assert r.status_code == 200, f"应该通过但错误: {r.text}"
    else:
        assert r.status_code in (400, 422), f"应该失败但通过了: {r.text}"


def test_encode_invalid_info_bits():
    """测试信息位长度无效的情况"""
    # 构造一个H矩阵，k=2
    H = [[1, 0, 0, 1], [0, 1, 1, 0]]

    # 发送长度为3的信息位（应该是2）
    r = client.post("/api/v1/encode", json={
        "h_matrix": H,
        "info_bits": [1, 0, 1]  # 长度错误
    })
    assert r.status_code == 400
    assert "信息位长度" in r.json()["detail"]


if __name__ == "__main__":
    # 可以直接运行该文件进行测试
    pytest.main(["-xvs", __file__])
