"""增强版 LDPCEncoder 测试，覆盖边缘情况和特殊用例。"""
import unittest
import sys
import os
import numpy as np
import scipy.sparse as sp
from time import time
import pytest

# 添加backend目录到路径，以便导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from algorithms.ldpc_encoder import LDPCEncoder


class TestLDPCEncoderAdvanced(unittest.TestCase):
    """覆盖边缘情况的增强版 LDPCEncoder 测试。"""

    def test_sparse_matrix_input(self):
        """A1: 测试稀疏矩阵输入。"""
        # 创建稀疏的校验矩阵 (CSR 格式)
        m, n = 6, 12
        density = 0.3  # 稀疏度
        rng = np.random.default_rng(42)
        data = rng.integers(0, 2, size=int(m * n * density))
        H_sparse = sp.random(m, n, density=density, format='csr', dtype=int, random_state=42)
        H_sparse.data = np.ones_like(H_sparse.data)  # 确保所有非零元素为1

        try:
            # 测试能否成功初始化
            enc = LDPCEncoder(H_sparse)
            # 测试能否生成G矩阵
            G = enc.generate_g_matrix()
            # 确保H·G^T = 0
            H_dense = H_sparse.toarray()
            self.assertTrue(np.all((H_dense @ G.T) % 2 == 0), "稀疏矩阵输入后正交性检查失败")

            # 测试编码功能
            info_bits = rng.integers(0, 2, size=enc.k)
            codeword = enc.encode(info_bits)
            # 验证码字满足校验方程
            self.assertTrue(np.all((H_dense @ codeword) % 2 == 0), "稀疏矩阵编码后校验失败")

            # 测试结构验证功能
            props = enc.validate_code_structure()
            self.assertTrue(props["is_orthogonal"], "稀疏矩阵结构验证失败")
        except Exception as e:
            self.fail(f"稀疏矩阵测试失败：{str(e)}")

    def test_rank_deficient_matrix(self):
        """A2: 测试秩不足矩阵。"""
        m, n = 6, 12
        rng = np.random.default_rng(123)

        # 生成秩为 m-1 的矩阵
        H_base = rng.integers(0, 2, size=(m-1, n))
        while np.linalg.matrix_rank(H_base % 2) < m-1:  # 保证 H_base 本身满秩
            H_base = rng.integers(0, 2, size=(m-1, n))

        # ★ 复制一行 → 一定线性相关
        last_row = H_base[0].copy()
        H = np.vstack([H_base, last_row])

        # 验证矩阵确实秩不足
        rank = np.linalg.matrix_rank(H % 2)
        self.assertEqual(rank, m-1, "测试矩阵秩不是预期值")

        # 测试编码器处理
        enc = LDPCEncoder(H)

        # 检查k值计算是否正确
        expected_k = n - rank
        self.assertEqual(enc.k, expected_k, f"秩不足矩阵k值错误，应为{expected_k}，得到{enc.k}")

        # 验证能否正确生成G矩阵和编码
        G = enc.generate_g_matrix()
        info_bits = rng.integers(0, 2, size=enc.k)
        codeword = enc.encode(info_bits)

        # 验证编码结果
        self.assertTrue(np.all((H @ codeword) % 2 == 0), "秩不足矩阵编码校验失败")

    def test_encode_before_generate_g(self):
        """A3: 测试在显式生成G之前调用encode。"""
        m, n = 4, 8
        rng = np.random.default_rng(42)
        H = rng.integers(0, 2, size=(m, n))
        while np.linalg.matrix_rank(H % 2) < m:
            H = rng.integers(0, 2, size=(m, n))

        enc = LDPCEncoder(H)
        # 直接调用encode，不提前调用generate_g_matrix
        info_bits = rng.integers(0, 2, size=enc.k)
        codeword = enc.encode(info_bits)

        # 验证编码结果
        self.assertTrue(np.all((H @ codeword) % 2 == 0), "前置调用encode校验失败")

        # 确保G矩阵已经被延迟计算
        self.assertIsNotNone(enc._G, "encode后G矩阵未被计算")

    def test_multiple_encode_consistency(self):
        """A4: 测试多次调用encode和generate的一致性。"""
        m, n = 4, 10
        rng = np.random.default_rng(42)
        H = rng.integers(0, 2, size=(m, n))
        while np.linalg.matrix_rank(H % 2) < m:
            H = rng.integers(0, 2, size=(m, n))

        enc = LDPCEncoder(H)

        # 首次生成G矩阵
        G1 = enc.generate_g_matrix()

        # 编码一批数据
        info1 = rng.integers(0, 2, size=enc.k)
        code1 = enc.encode(info1)

        # 再次调用generate_g_matrix
        G2 = enc.generate_g_matrix()

        # 验证两次获取的G矩阵相同
        np.testing.assert_array_equal(G1, G2, "多次生成的G矩阵不一致")

        # 再次编码并验证一致性
        info2 = rng.integers(0, 2, size=enc.k)
        code2 = enc.encode(info2)

        # 手动用第一次的G矩阵计算验证
        expected_code2 = (info2 @ G1) % 2
        np.testing.assert_array_equal(code2, expected_code2, "多次编码结果不一致")

    def test_different_input_types(self):
        """A5: 测试不同的输入数据类型。"""
        # 创建一个简单的H矩阵
        H = np.array([
            [1, 0, 1, 1],
            [0, 1, 1, 0],
        ], dtype=int)

        enc = LDPCEncoder(H)
        enc.generate_g_matrix()  # 确保k已确定

        # 测试不同类型的info_bits
        # 1. Python列表
        info_list = [1, 0] if enc.k == 2 else [1] * enc.k
        code1 = enc.encode(info_list)

        # 2. NumPy布尔数组
        info_bool = np.array(info_list, dtype=bool)
        code2 = enc.encode(info_bool)

        # 3. NumPy整数数组
        info_int = np.array(info_list, dtype=int)
        code3 = enc.encode(info_int)

        # 比较结果
        np.testing.assert_array_equal(code1, code2, "布尔数组和列表编码结果不一致")
        np.testing.assert_array_equal(code1, code3, "整数数组和列表编码结果不一致")

        # 验证所有结果都满足校验
        for code in [code1, code2, code3]:
            self.assertTrue(np.all((H @ code) % 2 == 0), "不同类型输入的编码结果校验失败")

    @pytest.mark.timeout(10)  # 10秒超时
    def test_large_scale_matrix(self):
        """A6: 测试大规模矩阵的性能。"""
        # 这里可以根据机器性能调整大小
        m, n = 128, 256
        density = 0.05  # 使用稀疏矩阵以提高性能

        # 创建稀疏随机矩阵
        H_sparse = sp.random(m, n, density=density, format='csr', random_state=42)
        H_sparse.data = np.ones_like(H_sparse.data)

        start_time = time()

        # 尝试编码
        try:
            enc = LDPCEncoder(H_sparse)
            G = enc.generate_g_matrix()
            # 生成随机信息位
            info_bits = np.random.randint(0, 2, size=enc.k)
            code = enc.encode(info_bits)

            # 验证结果
            H_dense = H_sparse.toarray()
            self.assertTrue(np.all((H_dense @ code) % 2 == 0), "大规模矩阵编码校验失败")

            # 记录执行时间
            execution_time = time() - start_time
            print(f"大规模矩阵测试 ({m}×{n}) 执行时间: {execution_time:.2f}秒")
        except Exception as e:
            self.fail(f"大规模矩阵测试失败: {str(e)}")

    def test_validate_code_structure_fields(self):
        """A7: 测试validate_code_structure返回的字段。"""
        # 创建一个已知特征的H矩阵
        H = np.array([
            [1, 1, 1, 0, 0],
            [1, 0, 0, 1, 1],
            [0, 1, 0, 1, 0],
        ], dtype=int)

        enc = LDPCEncoder(H)
        props = enc.validate_code_structure()

        # 必须包含的字段
        required_fields = [
            "is_orthogonal", "k", "n", "code_rate", "code_length",
            "message_length", "variable_node_degree", "check_node_degree",
            "has_4cycle"
        ]

        for field in required_fields:
            self.assertIn(field, props, f"结构验证缺少字段 {field}")

        # 验证基本参数
        self.assertEqual(props["k"], enc.k)
        self.assertEqual(props["n"], enc.n)
        self.assertEqual(props["code_length"], enc.n)
        self.assertEqual(props["message_length"], enc.k)
        self.assertAlmostEqual(props["code_rate"], enc.k / enc.n)

        # 验证度分布
        # 变量节点度 (列和)
        var_degrees = np.sum(H, axis=0)
        check_degrees = np.sum(H, axis=1)

        if isinstance(props["variable_node_degree"], list):
            self.assertEqual(len(props["variable_node_degree"]), len(var_degrees))

        if isinstance(props["check_node_degree"], list):
            self.assertEqual(len(props["check_node_degree"]), len(check_degrees))

    def test_illegal_element_values(self):
        """A8: 测试非法元素值（>1或负）。"""
        # 创建含有>1和负数的H矩阵
        H_illegal = np.array([
            [1, 2, 1, 0],
            [0, 1, -1, 1],
        ])

        # 预期编码器会自动修正为mod 2
        enc = LDPCEncoder(H_illegal)
        G = enc.generate_g_matrix()

        # 预期的mod 2修正结果
        H_expected = np.array([
            [1, 0, 1, 0],
            [0, 1, 1, 1],
        ])

        # 验证正交性 (使用修正后的H)
        self.assertTrue(np.all((H_expected @ G.T) % 2 == 0), "修正后的H矩阵与G不正交")

        # 编码并验证
        info_bits = np.random.randint(0, 2, size=enc.k)
        code = enc.encode(info_bits)
        self.assertTrue(np.all((H_expected @ code) % 2 == 0), "非法元素值编码后校验失败")


# 以下测试需要额外的包支持，可以根据需要启用

"""
# 需要安装 hypothesis: pip install hypothesis
from hypothesis import given, settings, strategies as st

class TestLDPCEncoderHypothesis(unittest.TestCase):
    @settings(max_examples=100)
    @given(
        m=st.integers(min_value=2, max_value=6),
        n=st.integers(min_value=4, max_value=12)
    )
    def test_ldpc_property_based(self, m, n):
        "A9: 基于属性的测试。"
        if n <= m:
            return  # 跳过无效组合
            
        # 生成随机H矩阵
        rng = np.random.default_rng()
        H = rng.integers(0, 2, size=(m, n))
        
        # 尝试获取满秩矩阵 (但不强制)
        for _ in range(5):  # 尝试最多5次
            if np.linalg.matrix_rank(H % 2) == min(m, n):
                break
            H = rng.integers(0, 2, size=(m, n))
        
        # 即使不满秩，编码器也应该正常工作
        try:
            enc = LDPCEncoder(H)
            if enc.k > 0:  # 确保有信息位可编码
                info = rng.integers(0, 2, size=enc.k)
                code = enc.encode(info)
                # 验证码字满足校验方程
                assert np.all((H @ code) % 2 == 0), "属性测试编码校验失败"
        except Exception as e:
            if "矩阵秩不足" not in str(e):  # 如果是其他错误则失败
                self.fail(f"属性测试异常: {str(e)}")
"""

"""
# 需要安装 pytest-timeout: pip install pytest-timeout
import concurrent.futures

class TestLDPCEncoderConcurrent(unittest.TestCase):
    def test_concurrent_encode_consistency(self):
        "A10: 测试并发编码的一致性。"
        H = np.random.randint(0, 2, size=(4, 10))
        while np.linalg.matrix_rank(H % 2) < 4:
            H = np.random.randint(0, 2, size=(4, 10))
            
        enc = LDPCEncoder(H)
        # 生成多组信息位
        rng = np.random.default_rng(42)
        infos = [rng.integers(0, 2, size=enc.k) for _ in range(20)]
        
        # 串行编码结果作为参考
        serial_codes = [enc.encode(info) for info in infos]
        
        # 并行编码
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            parallel_codes = list(pool.map(enc.encode, infos))
        
        # 比较结果
        for serial, parallel in zip(serial_codes, parallel_codes):
            np.testing.assert_array_equal(serial, parallel, "并发编码结果不一致")
"""


if __name__ == "__main__":
    unittest.main()
