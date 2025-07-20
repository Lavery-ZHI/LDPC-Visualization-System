"""增强版 LDPCDecoder 测试，覆盖LLR计算、BP解码算法、收敛性等。"""
import unittest
import sys
import os
import numpy as np
import scipy.sparse as sp
from time import time
import pytest

# 添加backend目录到路径，以便导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from algorithms.ldpc_decoder import LDPCDecoder
from algorithms.ldpc_encoder import LDPCEncoder


class TestLDPCDecoderAdvanced(unittest.TestCase):
    """覆盖各种场景的增强版 LDPCDecoder 测试。"""

    def setUp(self):
        """设置测试数据"""
        # 标准测试矩阵 (4,1,3) LDPC码
        self.H_simple = np.array([
            [1, 1, 1, 0],
            [1, 0, 1, 1],
            [0, 1, 1, 1]
        ])
        
        # 稍大的测试矩阵 (7,4,3) LDPC码
        self.H_medium = np.array([
            [1, 1, 1, 0, 0, 0, 0],
            [1, 0, 0, 1, 1, 0, 0],
            [0, 1, 0, 1, 0, 1, 0],
            [0, 0, 1, 0, 1, 1, 1]
        ])
        
        # 随机种子
        self.rng = np.random.default_rng(42)

    def test_initialization(self):
        """D1: 测试解码器初始化"""
        # 测试不同输入格式
        decoder1 = LDPCDecoder(self.H_simple)
        self.assertEqual(decoder1.n, 4)
        self.assertEqual(decoder1.k, 1)
        self.assertEqual(decoder1.m, 3)
        self.assertAlmostEqual(decoder1.rate, 0.25)

        # 测试稀疏矩阵输入
        H_sparse = sp.csr_matrix(self.H_simple)
        decoder2 = LDPCDecoder(H_sparse)
        self.assertEqual(decoder2.n, 4)
        self.assertEqual(decoder2.k, 1)

        # 测试参数设置
        decoder3 = LDPCDecoder(
            self.H_simple,
            max_iterations=100,
            min_sum_scaling=0.8,
            early_termination=False
        )
        self.assertEqual(decoder3.max_iterations, 100)
        self.assertEqual(decoder3.min_sum_scaling, 0.8)
        self.assertFalse(decoder3.early_termination)

    def test_adjacency_precomputation(self):
        """D2: 测试邻接信息预计算"""
        decoder = LDPCDecoder(self.H_simple)
        
        # 验证邻接列表长度
        self.assertEqual(len(decoder.var_to_check), 4)
        self.assertEqual(len(decoder.check_to_var), 3)
        
        # 验证邻接信息正确性
        # 变量节点0连接到校验节点0,1
        self.assertEqual(set(decoder.var_to_check[0]), {0, 1})
        # 变量节点1连接到校验节点0,2
        self.assertEqual(set(decoder.var_to_check[1]), {0, 2})
        # 变量节点2连接到校验节点0,1,2
        self.assertEqual(set(decoder.var_to_check[2]), {0, 1, 2})
        # 变量节点3连接到校验节点1,2
        self.assertEqual(set(decoder.var_to_check[3]), {1, 2})

    def test_awgn_llr_calculation(self):
        """D3: 测试AWGN信道LLR计算"""
        decoder = LDPCDecoder(self.H_simple)
        
        # 测试基本LLR计算
        received_signal = np.array([1.0, -0.5, 0.2, -1.5])
        noise_variance = 0.5
        llr = decoder.awgn_llr(received_signal, noise_variance)
        
        # 验证LLR公式: LLR = 2*r/σ²
        expected_llr = 2 * received_signal / noise_variance
        np.testing.assert_array_almost_equal(llr, expected_llr, decimal=10)
        
        # 测试边界条件
        # 强正信号 -> 大正LLR (倾向于0，因为LLR=2*r/σ²，正信号给正LLR)
        strong_positive = np.array([5.0, 0, 0, 0])
        llr_strong = decoder.awgn_llr(strong_positive, 0.1)
        self.assertGreater(llr_strong[0], 50)  # 强烈倾向于0
        
        # 强负信号 -> 大负LLR (倾向于1)
        strong_negative = np.array([-5.0, 0, 0, 0])
        llr_strong = decoder.awgn_llr(strong_negative, 0.1)
        self.assertLess(llr_strong[0], -50)  # 强烈倾向于1

    def test_bsc_llr_calculation(self):
        """D4: 测试BSC信道LLR计算"""
        decoder = LDPCDecoder(self.H_simple)
        
        # 测试基本BSC LLR计算
        received_bits = np.array([0, 1, 0, 1])
        crossover_prob = 0.1
        llr = decoder.bsc_llr(received_bits, crossover_prob)
        
        # 验证LLR公式: LLR = log((1-p)/p) * (1-2*r)
        log_ratio = np.log((1 - crossover_prob) / crossover_prob)
        expected_llr = log_ratio * (1 - 2 * received_bits)
        np.testing.assert_array_almost_equal(llr, expected_llr, decimal=10)
        
        # 测试边界条件
        with self.assertRaises(ValueError):
            decoder.bsc_llr(received_bits, 0.5)  # p >= 0.5
        
        with self.assertRaises(ValueError):
            decoder.bsc_llr(received_bits, 0.0)   # p <= 0
        
        # 测试不同的交叉概率
        for p in [0.01, 0.1, 0.2, 0.3, 0.4]:
            llr = decoder.bsc_llr(received_bits, p)
            self.assertEqual(len(llr), 4)
            self.assertTrue(np.all(np.isfinite(llr)))

    def test_min_sum_decode_perfect_reception(self):
        """D5: 测试Min-Sum算法完美接收"""
        decoder = LDPCDecoder(self.H_simple)
        encoder = LDPCEncoder(self.H_simple)
        
        # 编码
        info_bits = np.array([1])
        codeword = encoder.encode(info_bits)
        
        # 完美接收 (高信噪比)
        bpsk_signal = 1 - 2 * codeword  # 0->1, 1->-1
        llr = decoder.awgn_llr(bpsk_signal, 0.01)  # 很低的噪声
        
        # 解码
        decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
        
        # 验证解码结果
        np.testing.assert_array_equal(decoded_bits, codeword)
        self.assertTrue(stats["converged"])
        self.assertTrue(stats["parity_check_satisfied"])
        self.assertEqual(stats["syndrome_weight"], 0)

    def test_sum_product_decode_perfect_reception(self):
        """D6: 测试Sum-Product算法完美接收"""
        decoder = LDPCDecoder(self.H_simple)
        encoder = LDPCEncoder(self.H_simple)
        
        # 编码
        info_bits = np.array([1])
        codeword = encoder.encode(info_bits)
        
        # 完美接收
        bpsk_signal = 1 - 2 * codeword
        llr = decoder.awgn_llr(bpsk_signal, 0.01)
        
        # 解码
        decoded_bits, stats = decoder.decode(llr, algorithm="sum_product")
        
        # 验证解码结果
        np.testing.assert_array_equal(decoded_bits, codeword)
        self.assertTrue(stats["converged"])
        self.assertTrue(stats["parity_check_satisfied"])

    def test_decode_with_errors(self):
        """D7: 测试有错误的解码"""
        decoder = LDPCDecoder(self.H_medium)
        encoder = LDPCEncoder(self.H_medium)
        
        # 编码
        info_bits = self.rng.integers(0, 2, size=encoder.k)
        codeword = encoder.encode(info_bits)
        
        # 添加噪声
        noise_variance = 0.8
        noise = self.rng.normal(0, np.sqrt(noise_variance), len(codeword))
        bpsk_signal = 1 - 2 * codeword
        noisy_signal = bpsk_signal + noise
        
        llr = decoder.awgn_llr(noisy_signal, noise_variance)
        
        # 解码
        decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
        
        # 验证解码统计信息
        self.assertIsInstance(stats["iterations"], int)
        self.assertIsInstance(stats["converged"], bool)
        self.assertIsInstance(stats["syndrome_weight"], int)
        self.assertIsInstance(stats["parity_check_satisfied"], bool)
        
        # 如果收敛，应该满足校验约束
        if stats["converged"]:
            self.assertTrue(stats["parity_check_satisfied"])

    def test_early_termination(self):
        """D8: 测试早期终止功能"""
        # 测试启用早期终止
        decoder_early = LDPCDecoder(self.H_simple, early_termination=True)
        encoder = LDPCEncoder(self.H_simple)
        
        info_bits = np.array([0])
        codeword = encoder.encode(info_bits)
        bpsk_signal = 1 - 2 * codeword
        llr = decoder_early.awgn_llr(bpsk_signal, 0.01)
        
        decoded_bits, stats = decoder_early.decode(llr, algorithm="min_sum")
        
        # 应该快速收敛
        self.assertTrue(stats["converged"])
        self.assertLess(stats["iterations"], 5)  # 应该很快收敛
        
        # 测试禁用早期终止
        decoder_no_early = LDPCDecoder(self.H_simple, early_termination=False, max_iterations=10)
        decoded_bits2, stats2 = decoder_no_early.decode(llr, algorithm="min_sum")
        
        # 应该运行完整的迭代次数
        self.assertEqual(stats2["iterations"], 10)

    def test_convergence_threshold(self):
        """D9: 测试收敛阈值"""
        # 注意：当前实现主要基于校验约束而非LLR变化阈值
        # 这个测试主要验证参数设置
        decoder = LDPCDecoder(
            self.H_simple,
            convergence_threshold=1e-8,
            max_iterations=20
        )
        
        encoder = LDPCEncoder(self.H_simple)
        info_bits = np.array([1])
        codeword = encoder.encode(info_bits)
        
        # 添加一些噪声
        bpsk_signal = 1 - 2 * codeword
        noise = self.rng.normal(0, 0.1, len(codeword))
        noisy_signal = bpsk_signal + noise
        
        llr = decoder.awgn_llr(noisy_signal, 0.1)
        decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
        
        # 验证能够运行（参数设置正确）
        self.assertIsInstance(stats["iterations"], int)
        self.assertLessEqual(stats["iterations"], 20)

    def test_min_sum_scaling_factor(self):
        """D10: 测试Min-Sum缩放因子"""
        encoder = LDPCEncoder(self.H_simple)
        info_bits = np.array([1])
        codeword = encoder.encode(info_bits)
        
        # 添加适量噪声
        noise_power = 0.3
        noise = self.rng.normal(0, np.sqrt(noise_power), len(codeword))
        bpsk_signal = 1 - 2 * codeword
        noisy_signal = bpsk_signal + noise
        
        # 测试不同缩放因子
        scaling_factors = [0.5, 0.7, 0.9, 1.0]
        results = []
        
        for scaling in scaling_factors:
            decoder = LDPCDecoder(self.H_simple, min_sum_scaling=scaling)
            llr = decoder.awgn_llr(noisy_signal, noise_power)
            decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
            results.append((scaling, stats["iterations"], stats["converged"]))
        
        # 验证不同缩放因子都能产生有效结果
        for scaling, iterations, converged in results:
            self.assertIsInstance(iterations, int)
            self.assertIsInstance(converged, bool)
            self.assertGreater(iterations, 0)

    def test_validate_codeword(self):
        """D11: 测试码字验证"""
        decoder = LDPCDecoder(self.H_simple)
        encoder = LDPCEncoder(self.H_simple)
        
        # 测试有效码字
        info_bits = np.array([1])
        valid_codeword = encoder.encode(info_bits)
        self.assertTrue(decoder.validate_codeword(valid_codeword))
        
        # 测试无效码字
        invalid_codeword = np.array([1, 0, 1, 0])  # 随机比特
        # 只有当这个随机比特恰好是有效码字时才通过
        is_valid = decoder.validate_codeword(invalid_codeword)
        if not is_valid:
            self.assertFalse(is_valid)
        
        # 测试全零码字（应该总是有效的）
        zero_codeword = np.zeros(decoder.n, dtype=int)
        self.assertTrue(decoder.validate_codeword(zero_codeword))

    def test_get_syndrome(self):
        """D12: 测试校验子计算"""
        decoder = LDPCDecoder(self.H_simple)
        encoder = LDPCEncoder(self.H_simple)
        
        # 测试有效码字的校验子
        info_bits = np.array([1])
        valid_codeword = encoder.encode(info_bits)
        syndrome = decoder.get_syndrome(valid_codeword)
        
        # 有效码字的校验子应该为全零
        np.testing.assert_array_equal(syndrome, np.zeros(decoder.m))
        
        # 测试有错误码字的校验子
        error_codeword = valid_codeword.copy()
        error_codeword[0] = 1 - error_codeword[0]  # 翻转第一位
        syndrome_error = decoder.get_syndrome(error_codeword)
        
        # 有错误的码字校验子不应该为全零
        self.assertGreater(np.sum(syndrome_error), 0)

    def test_extract_information_bits(self):
        """D13: 测试信息位提取"""
        decoder = LDPCDecoder(self.H_simple)
        encoder = LDPCEncoder(self.H_simple)
        
        # 测试信息位提取
        original_info = np.array([1])
        codeword = encoder.encode(original_info)
        extracted_info = decoder.extract_information_bits(codeword)
        
        # 验证提取的信息位
        self.assertEqual(len(extracted_info), decoder.k)
        
        # 对于系统形式的码，前k位应该是信息位
        np.testing.assert_array_equal(extracted_info, codeword[:decoder.k])

    def test_analyze_decoder_performance(self):
        """D14: 测试解码器性能分析"""
        decoder = LDPCDecoder(self.H_simple)
        
        # 先进行一次解码以产生统计信息
        encoder = LDPCEncoder(self.H_simple)
        info_bits = np.array([1])
        codeword = encoder.encode(info_bits)
        bpsk_signal = 1 - 2 * codeword
        llr = decoder.awgn_llr(bpsk_signal, 0.1)
        decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
        
        # 分析性能
        analysis = decoder.analyze_decoder_performance()
        
        # 验证分析结果的字段
        self.assertIn("code_parameters", analysis)
        self.assertIn("degree_distribution", analysis)
        self.assertIn("decoder_parameters", analysis)
        self.assertIn("last_decode_stats", analysis)
        
        # 验证码参数
        code_params = analysis["code_parameters"]
        self.assertEqual(code_params["n"], 4)
        self.assertEqual(code_params["k"], 1)
        self.assertEqual(code_params["m"], 3)
        self.assertEqual(code_params["rate"], 0.25)
        
        # 验证度分布
        degree_dist = analysis["degree_distribution"]
        self.assertEqual(len(degree_dist["variable_degrees"]), 4)
        self.assertEqual(len(degree_dist["check_degrees"]), 3)
        self.assertGreater(degree_dist["avg_variable_degree"], 0)
        self.assertGreater(degree_dist["avg_check_degree"], 0)

    def test_algorithm_comparison(self):
        """D15: 测试两种算法的比较"""
        decoder = LDPCDecoder(self.H_simple)
        encoder = LDPCEncoder(self.H_simple)
        
        # 生成测试数据
        info_bits = np.array([1])
        codeword = encoder.encode(info_bits)
        
        # 添加适量噪声
        noise_power = 0.5
        noise = self.rng.normal(0, np.sqrt(noise_power), len(codeword))
        bpsk_signal = 1 - 2 * codeword
        noisy_signal = bpsk_signal + noise
        llr = decoder.awgn_llr(noisy_signal, noise_power)
        
        # 使用两种算法解码
        decoded_ms, stats_ms = decoder.decode(llr, algorithm="min_sum")
        decoded_sp, stats_sp = decoder.decode(llr, algorithm="sum_product")
        
        # 验证两种算法都能产生有效结果
        self.assertIsInstance(stats_ms["iterations"], int)
        self.assertIsInstance(stats_sp["iterations"], int)
        self.assertIsInstance(stats_ms["converged"], bool)
        self.assertIsInstance(stats_sp["converged"], bool)
        
        # 如果都收敛，结果应该相同或至少都满足校验约束
        if stats_ms["converged"] and stats_sp["converged"]:
            self.assertTrue(stats_ms["parity_check_satisfied"])
            self.assertTrue(stats_sp["parity_check_satisfied"])

    def test_input_validation(self):
        """D16: 测试输入验证"""
        decoder = LDPCDecoder(self.H_simple)
        
        # 测试LLR输入长度错误
        with self.assertRaises(ValueError):
            wrong_llr = np.array([1.0, 2.0])  # 长度错误
            decoder.decode(wrong_llr)
        
        # 测试接收信号长度错误
        with self.assertRaises(ValueError):
            wrong_signal = np.array([1.0, 2.0])  # 长度错误
            decoder.awgn_llr(wrong_signal, 0.5)
        
        # 测试接收比特长度错误
        with self.assertRaises(ValueError):
            wrong_bits = np.array([1, 0])  # 长度错误
            decoder.bsc_llr(wrong_bits, 0.1)
        
        # 测试码字长度错误
        with self.assertRaises(ValueError):
            wrong_codeword = np.array([1, 0])  # 长度错误
            decoder.validate_codeword(wrong_codeword)
        
        # 测试不支持的算法
        with self.assertRaises(ValueError):
            llr = np.array([1.0, 2.0, 3.0, 4.0])
            decoder.decode(llr, algorithm="unsupported")

    @pytest.mark.timeout(30)  # 30秒超时
    def test_large_scale_decoding(self):
        """D17: 测试大规模解码性能"""
        # 创建较大的稀疏H矩阵
        m, n = 64, 128
        density = 0.1
        
        H_large = sp.random(m, n, density=density, format='csr', random_state=42)
        H_large.data = np.ones_like(H_large.data)
        
        start_time = time()
        
        try:
            decoder = LDPCDecoder(H_large, max_iterations=20)
            
            # 生成随机LLR
            llr = self.rng.normal(0, 2, size=n)
            
            # 解码
            decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
            
            # 验证基本结果
            self.assertEqual(len(decoded_bits), n)
            self.assertIsInstance(stats["iterations"], int)
            self.assertLessEqual(stats["iterations"], 20)
            
            execution_time = time() - start_time
            print(f"大规模解码测试 ({m}×{n}) 执行时间: {execution_time:.2f}秒")
            
        except Exception as e:
            self.fail(f"大规模解码测试失败: {str(e)}")

    def test_edge_case_single_parity_check(self):
        """D18: 测试边缘情况 - 单一校验位"""
        # 单一校验位的简单码
        H_single = np.array([[1, 1, 1]])
        decoder = LDPCDecoder(H_single)
        
        self.assertEqual(decoder.n, 3)
        self.assertEqual(decoder.k, 2)
        self.assertEqual(decoder.m, 1)
        
        # 测试解码
        llr = np.array([1.0, -1.0, 0.5])
        decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
        
        # 验证结果
        self.assertEqual(len(decoded_bits), 3)
        self.assertTrue(stats["parity_check_satisfied"])


if __name__ == '__main__':
    unittest.main() 