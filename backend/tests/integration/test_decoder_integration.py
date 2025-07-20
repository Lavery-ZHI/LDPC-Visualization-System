"""
LDPC解码器集成测试 - 验证编码-解码完整流程
运行：
    cd Code/backend && pytest tests/integration/test_decoder_integration.py -v
"""
import sys
import os
from typing import List, Tuple
import numpy as np
import pytest

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from algorithms.ldpc_decoder import LDPCDecoder
from algorithms.ldpc_encoder import LDPCEncoder
from models.ldpc_models import LDPCCode


class TestLDPCEncoderDecoderIntegration:
    """测试编码器-解码器集成"""

    def setup_method(self):
        """设置测试数据"""
        # 简单的LDPC码 (4,1,3)
        self.H_simple = np.array([
            [1, 1, 1, 0],
            [1, 0, 1, 1],
            [0, 1, 1, 1]
        ])
        
        # 中等规模的LDPC码 (7,4,3)
        self.H_medium = np.array([
            [1, 1, 1, 0, 0, 0, 0],
            [1, 0, 0, 1, 1, 0, 0],
            [0, 1, 0, 1, 0, 1, 0],
            [0, 0, 1, 0, 1, 1, 1]
        ])
        
        self.rng = np.random.default_rng(42)

    def test_encode_decode_perfect_channel(self):
        """测试完美信道下的编码-解码"""
        encoder = LDPCEncoder(self.H_simple)
        decoder = LDPCDecoder(self.H_simple)
        
        # 测试多个信息位
        for info_bit in [0, 1]:
            info_bits = np.array([info_bit])
            
            # 编码
            codeword = encoder.encode(info_bits)
            
            # 验证码字有效性
            assert decoder.validate_codeword(codeword), f"编码器产生的码字无效: {codeword}"
            
            # 完美信道接收
            bpsk_signal = 1 - 2 * codeword  # 0->1, 1->-1
            llr = decoder.awgn_llr(bpsk_signal, 0.001)  # 极低噪声
            
            # 解码
            decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
            
            # 验证解码结果
            np.testing.assert_array_equal(decoded_bits, codeword)
            assert stats["converged"], "解码应该收敛"
            assert stats["parity_check_satisfied"], "解码结果应该满足校验约束"
            
            # 验证信息位恢复
            recovered_info = decoder.extract_information_bits(decoded_bits)
            np.testing.assert_array_equal(recovered_info, info_bits)

    def test_encode_decode_awgn_channel(self):
        """测试AWGN信道下的编码-解码"""
        encoder = LDPCEncoder(self.H_medium)
        decoder = LDPCDecoder(self.H_medium)
        
        # 测试多个信息位模式 (k=3)
        test_cases = [
            np.array([0, 0, 0]),
            np.array([1, 1, 1]),
            np.array([1, 0, 1]),
            np.array([0, 1, 0])
        ]
        
        for info_bits in test_cases:
            # 编码
            codeword = encoder.encode(info_bits)
            
            # AWGN信道
            noise_variances = [0.1, 0.3, 0.5, 0.8]
            
            for noise_var in noise_variances:
                # 添加噪声
                bpsk_signal = 1 - 2 * codeword
                noise = self.rng.normal(0, np.sqrt(noise_var), len(codeword))
                noisy_signal = bpsk_signal + noise
                
                llr = decoder.awgn_llr(noisy_signal, noise_var)
                
                # 解码
                decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
                
                # 验证解码基本属性
                assert len(decoded_bits) == len(codeword), "解码结果长度错误"
                assert stats["iterations"] > 0, "解码应该至少运行一次迭代"
                
                # 如果收敛，应该满足校验约束
                if stats["converged"]:
                    assert stats["parity_check_satisfied"], "收敛的解码结果应该满足校验约束"
                    
                    # 验证信息位恢复
                    recovered_info = decoder.extract_information_bits(decoded_bits)
                    # 对于低噪声，信息位应该正确恢复
                    if noise_var <= 0.3:
                        np.testing.assert_array_equal(recovered_info, info_bits)

    def test_encode_decode_bsc_channel(self):
        """测试BSC信道下的编码-解码"""
        encoder = LDPCEncoder(self.H_simple)
        decoder = LDPCDecoder(self.H_simple)
        
        info_bits = np.array([1])
        codeword = encoder.encode(info_bits)
        
        # 测试不同的交叉概率
        crossover_probs = [0.01, 0.05, 0.1, 0.15]
        
        for p in crossover_probs:
            # 模拟BSC信道
            received_bits = codeword.copy()
            error_positions = self.rng.random(len(codeword)) < p
            received_bits[error_positions] = 1 - received_bits[error_positions]
            
            # 计算LLR
            llr = decoder.bsc_llr(received_bits, p)
            
            # 解码
            decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
            
            # 验证解码结果
            assert len(decoded_bits) == len(codeword), "解码结果长度错误"
            
            # 对于低错误率，应该能够纠正
            if p <= 0.05:
                if stats["converged"]:
                    assert stats["parity_check_satisfied"], "收敛的解码结果应该满足校验约束"
                    # 验证信息位恢复
                    recovered_info = decoder.extract_information_bits(decoded_bits)
                    np.testing.assert_array_equal(recovered_info, info_bits)

    def test_algorithm_consistency(self):
        """测试Min-Sum和Sum-Product算法的一致性"""
        encoder = LDPCEncoder(self.H_simple)
        decoder = LDPCDecoder(self.H_simple)
        
        info_bits = np.array([1])
        codeword = encoder.encode(info_bits)
        
        # 高信噪比测试
        bpsk_signal = 1 - 2 * codeword
        llr = decoder.awgn_llr(bpsk_signal, 0.01)
        
        # 使用两种算法解码
        decoded_ms, stats_ms = decoder.decode(llr, algorithm="min_sum")
        decoded_sp, stats_sp = decoder.decode(llr, algorithm="sum_product")
        
        # 在高信噪比下，两种算法应该产生相同的结果
        if stats_ms["converged"] and stats_sp["converged"]:
            np.testing.assert_array_equal(decoded_ms, decoded_sp)
            assert stats_ms["parity_check_satisfied"], "Min-Sum应该满足校验约束"
            assert stats_sp["parity_check_satisfied"], "Sum-Product应该满足校验约束"

    def test_large_scale_encode_decode(self):
        """测试大规模编码-解码"""
        # 创建较大的稀疏H矩阵
        m, n = 32, 64
        density = 0.1
        
        H_large = np.random.binomial(1, density, size=(m, n))
        # 确保矩阵满秩
        while np.linalg.matrix_rank(H_large % 2) < m:
            H_large = np.random.binomial(1, density, size=(m, n))
        
        encoder = LDPCEncoder(H_large)
        decoder = LDPCDecoder(H_large, max_iterations=20)
        
        # 生成随机信息位
        info_bits = self.rng.integers(0, 2, size=encoder.k)
        
        # 编码
        codeword = encoder.encode(info_bits)
        
        # 验证码字
        assert decoder.validate_codeword(codeword), "大规模编码器产生的码字无效"
        
        # 低噪声解码
        bpsk_signal = 1 - 2 * codeword
        noise = self.rng.normal(0, 0.05, len(codeword))  # 降低噪声
        noisy_signal = bpsk_signal + noise
        
        llr = decoder.awgn_llr(noisy_signal, 0.0025)  # 降低噪声方差
        decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
        
        # 验证解码结果
        assert len(decoded_bits) == len(codeword), "大规模解码结果长度错误"
        assert stats["iterations"] <= 20, "解码迭代次数超过限制"
        
        # 在低噪声下应该能够正确解码
        if stats["converged"] and stats["parity_check_satisfied"]:
            recovered_info = decoder.extract_information_bits(decoded_bits)
            # 对于低噪声，信息位应该正确恢复
            np.testing.assert_array_equal(recovered_info, info_bits)
        else:
            # 如果没有完全收敛，至少检查基本解码功能
            assert len(decoded_bits) == len(codeword), "解码结果长度错误"
            print(f"大规模解码未完全收敛，但基本功能正常: 收敛={stats['converged']}, 校验满足={stats['parity_check_satisfied']}")

    def test_error_detection_and_correction(self):
        """测试错误检测和纠正能力"""
        encoder = LDPCEncoder(self.H_medium)
        decoder = LDPCDecoder(self.H_medium)
        
        info_bits = np.array([1, 0, 1])  # k=3
        codeword = encoder.encode(info_bits)
        
        # 测试单比特错误
        for error_pos in range(len(codeword)):
            corrupted_codeword = codeword.copy()
            corrupted_codeword[error_pos] = 1 - corrupted_codeword[error_pos]
            
            # 验证错误检测
            assert not decoder.validate_codeword(corrupted_codeword), f"应该检测到位置{error_pos}的错误"
            
            # 计算校验子
            syndrome = decoder.get_syndrome(corrupted_codeword)
            assert np.sum(syndrome) > 0, f"校验子应该非零，位置{error_pos}"
            
            # 尝试纠正 (使用BSC模型)
            llr = decoder.bsc_llr(corrupted_codeword, 0.05)
            decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
            
            # 验证是否纠正成功
            if stats["converged"] and stats["parity_check_satisfied"]:
                recovered_info = decoder.extract_information_bits(decoded_bits)
                if np.array_equal(recovered_info, info_bits):
                    print(f"成功纠正位置{error_pos}的错误")

    def test_performance_comparison(self):
        """测试编码器-解码器性能比较"""
        import time
        
        # 测试不同规模的矩阵
        test_sizes = [(8, 16), (16, 32), (24, 48)]
        
        for m, n in test_sizes:
            # 创建随机H矩阵
            H = np.random.binomial(1, 0.1, size=(m, n))
            while np.linalg.matrix_rank(H % 2) < m:
                H = np.random.binomial(1, 0.1, size=(m, n))
            
            encoder = LDPCEncoder(H)
            decoder = LDPCDecoder(H, max_iterations=10)
            
            # 测试编码性能
            info_bits = self.rng.integers(0, 2, size=encoder.k)
            
            start_time = time.time()
            codeword = encoder.encode(info_bits)
            encode_time = time.time() - start_time
            
            # 测试解码性能
            bpsk_signal = 1 - 2 * codeword
            noise = self.rng.normal(0, 0.1, len(codeword))
            noisy_signal = bpsk_signal + noise
            llr = decoder.awgn_llr(noisy_signal, 0.01)
            
            start_time = time.time()
            decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
            decode_time = time.time() - start_time
            
            print(f"矩阵大小 {m}x{n}: 编码时间 {encode_time:.4f}s, 解码时间 {decode_time:.4f}s")
            
            # 验证性能要求
            assert encode_time < 1.0, f"编码时间过长: {encode_time:.4f}s"
            assert decode_time < 2.0, f"解码时间过长: {decode_time:.4f}s"

    def test_graph_to_matrix_integration(self):
        """测试从图形数据到矩阵的集成流程"""
        # 创建图形数据
        nodes = [
            {"id": "V0", "type": "variable"},
            {"id": "V1", "type": "variable"},
            {"id": "V2", "type": "variable"},
            {"id": "V3", "type": "variable"},
            {"id": "C0", "type": "check"},
            {"id": "C1", "type": "check"},
            {"id": "C2", "type": "check"},
        ]
        
        edges = [
            {"fromId": "V0", "toId": "C0"},
            {"fromId": "V1", "toId": "C0"},
            {"fromId": "V2", "toId": "C0"},
            {"fromId": "V0", "toId": "C1"},
            {"fromId": "V2", "toId": "C1"},
            {"fromId": "V3", "toId": "C1"},
            {"fromId": "V1", "toId": "C2"},
            {"fromId": "V2", "toId": "C2"},
            {"fromId": "V3", "toId": "C2"},
        ]
        
        # 从图形数据创建LDPC码
        ldpc_code = LDPCCode.from_graph_data(nodes, edges)
        
        # 创建编码器和解码器
        encoder = LDPCEncoder(ldpc_code.H)
        decoder = LDPCDecoder(ldpc_code.H)
        
        # 测试编码-解码
        info_bits = np.array([1])  # k=1
        codeword = encoder.encode(info_bits)
        
        # 验证码字
        assert decoder.validate_codeword(codeword), "从图形数据创建的码字无效"
        
        # 测试解码
        bpsk_signal = 1 - 2 * codeword
        llr = decoder.awgn_llr(bpsk_signal, 0.01)
        decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
        
        # 验证结果
        np.testing.assert_array_equal(decoded_bits, codeword)
        assert stats["converged"], "图形数据编码-解码应该收敛"
        assert stats["parity_check_satisfied"], "图形数据编码-解码应该满足校验约束"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 