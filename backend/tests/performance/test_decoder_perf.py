"""
LDPC解码器性能测试
测试大尺寸矩阵的解码性能指标，确保符合实时解码要求

运行：
    # 从backend目录运行：
    cd Code/backend && pytest tests/performance/test_decoder_perf.py -v -s
    
    # 或者运行特定测试：
    cd Code/backend && pytest tests/performance/test_decoder_perf.py::TestLDPCDecoderPerformance::test_decode_performance -v -s
"""
import time
import sys
import os
import numpy as np
import scipy.sparse as sp
import pytest
from typing import Dict, Any, Tuple

# 添加backend目录到路径，以便导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from algorithms.ldpc_decoder import LDPCDecoder
from algorithms.ldpc_encoder import LDPCEncoder


class TestLDPCDecoderPerformance:
    """LDPC解码器性能测试"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.performance_results = {}
        self.rng = np.random.default_rng(42)
    
    def _create_sparse_matrix(self, m: int, n: int, density: float = 0.05, seed: int = 42):
        """创建稀疏随机矩阵，确保满秩"""
        np.random.seed(seed)
        
        # 创建稀疏矩阵，确保满秩
        attempts = 0
        while attempts < 10:
            H_sparse = sp.random(m, n, density=density, format='csr', random_state=seed + attempts)
            H_sparse.data = np.ones_like(H_sparse.data)  # 确保所有非零元素为1
            H_dense = H_sparse.toarray()
            
            # 检查是否满秩
            rank = np.linalg.matrix_rank(H_dense % 2)
            if rank == m:
                return H_sparse
            attempts += 1
        
        # 如果随机生成失败，使用确定性方法
        return self._create_deterministic_matrix(m, n, density)
    
    def _create_deterministic_matrix(self, m: int, n: int, density: float):
        """创建确定性的满秩稀疏矩阵"""
        # 先创建单位矩阵确保满秩
        H = np.eye(m, n, dtype=int)
        
        # 添加随机稀疏元素
        num_additional = int(m * n * density) - m
        if num_additional > 0:
            for _ in range(num_additional):
                i, j = np.random.randint(0, m), np.random.randint(0, n)
                H[i, j] = 1 - H[i, j]  # 翻转位
        
        return sp.csr_matrix(H % 2)
    
    def _measure_performance(self, func, *args, **kwargs):
        """测量函数执行时间"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    def _generate_test_data(self, encoder: LDPCEncoder, decoder: LDPCDecoder, 
                          noise_var: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
        """生成测试用的编码数据和LLR"""
        # 生成随机信息位
        info_bits = self.rng.integers(0, 2, size=encoder.k)
        
        # 编码
        codeword = encoder.encode(info_bits)
        
        # 添加AWGN噪声
        bpsk_signal = 1 - 2 * codeword  # 0->1, 1->-1
        noise = self.rng.normal(0, np.sqrt(noise_var), len(codeword))
        noisy_signal = bpsk_signal + noise
        
        # 计算LLR
        llr = decoder.awgn_llr(noisy_signal, noise_var)
        
        return llr, codeword
    
    @pytest.mark.parametrize("m,n,expected_max_time", [
        (32, 64, 2.0),    # 小规模：< 2s
        (64, 128, 3.0),   # 中规模：< 3s  
        (96, 192, 5.0),   # 大规模：< 5s
        (128, 256, 8.0),  # 超大规模：< 8s
    ])
    def test_decode_performance(self, m, n, expected_max_time):
        """测试decode方法的性能"""
        print(f"\n=== 测试 decode 性能 ({m}×{n}) ===")
        
        # 创建测试矩阵
        H = self._create_sparse_matrix(m, n)
        encoder = LDPCEncoder(H)
        decoder = LDPCDecoder(H, max_iterations=50)
        
        # 生成测试数据
        llr, original_codeword = self._generate_test_data(encoder, decoder, noise_var=0.2)
        
        # 测量解码性能
        (decoded_bits, stats), exec_time = self._measure_performance(
            decoder.decode, llr, algorithm="min_sum"
        )
        
        # 记录结果
        self.performance_results[f"decode_min_sum_{m}x{n}"] = {
            "time": exec_time,
            "iterations": stats["iterations"],
            "converged": stats["converged"]
        }
        
        # 验证结果正确性
        assert len(decoded_bits) == n, f"解码结果长度错误：{len(decoded_bits)} != {n}"
        
        # 性能断言
        print(f"Min-Sum解码执行时间: {exec_time:.4f}s")
        print(f"解码迭代次数: {stats['iterations']}")
        print(f"是否收敛: {stats['converged']}")
        
        assert exec_time < expected_max_time, f"解码性能不达标：{exec_time:.4f}s > {expected_max_time}s"
    
    @pytest.mark.parametrize("m,n", [
        (32, 64),
        (64, 128),
        (96, 192),
    ])
    def test_algorithm_performance_comparison(self, m, n):
        """测试Min-Sum和Sum-Product算法的性能比较"""
        print(f"\n=== 测试算法性能比较 ({m}×{n}) ===")
        
        # 创建测试矩阵
        H = self._create_sparse_matrix(m, n)
        encoder = LDPCEncoder(H)
        decoder = LDPCDecoder(H, max_iterations=30)
        
        # 生成测试数据
        llr, original_codeword = self._generate_test_data(encoder, decoder, noise_var=0.15)
        
        # 测试Min-Sum算法
        (decoded_ms, stats_ms), time_ms = self._measure_performance(
            decoder.decode, llr, algorithm="min_sum"
        )
        
        # 测试Sum-Product算法
        (decoded_sp, stats_sp), time_sp = self._measure_performance(
            decoder.decode, llr, algorithm="sum_product"
        )
        
        # 记录结果
        self.performance_results[f"algorithm_comparison_{m}x{n}"] = {
            "min_sum_time": time_ms,
            "sum_product_time": time_sp,
            "min_sum_iterations": stats_ms["iterations"],
            "sum_product_iterations": stats_sp["iterations"],
            "speedup_ratio": time_sp / time_ms if time_ms > 0 else float('inf')
        }
        
        # 输出比较结果
        print(f"Min-Sum:      时间={time_ms:.4f}s, 迭代={stats_ms['iterations']}, 收敛={stats_ms['converged']}")
        print(f"Sum-Product:  时间={time_sp:.4f}s, 迭代={stats_sp['iterations']}, 收敛={stats_sp['converged']}")
        print(f"Min-Sum加速比: {time_sp/time_ms:.2f}x")
        
        # Min-Sum应该更快
        assert time_ms <= time_sp, "Min-Sum算法应该比Sum-Product算法更快"
    
    @pytest.mark.parametrize("noise_var", [0.05, 0.1, 0.2, 0.4])
    def test_decode_performance_vs_noise(self, noise_var):
        """测试不同噪声水平下的解码性能"""
        print(f"\n=== 测试噪声水平 σ²={noise_var} 下的解码性能 ===")
        
        m, n = 64, 128
        H = self._create_sparse_matrix(m, n)
        encoder = LDPCEncoder(H)
        decoder = LDPCDecoder(H, max_iterations=50)
        
        # 生成测试数据
        llr, original_codeword = self._generate_test_data(encoder, decoder, noise_var=noise_var)
        
        # 测量解码性能
        (decoded_bits, stats), exec_time = self._measure_performance(
            decoder.decode, llr, algorithm="min_sum"
        )
        
        # 记录结果
        self.performance_results[f"noise_level_{noise_var}"] = {
            "time": exec_time,
            "iterations": stats["iterations"],
            "converged": stats["converged"],
            "noise_variance": noise_var
        }
        
        print(f"噪声方差={noise_var}: 时间={exec_time:.4f}s, 迭代={stats['iterations']}, 收敛={stats['converged']}")
        
        # 性能应该在合理范围内
        assert exec_time < 5.0, f"解码时间过长：{exec_time:.4f}s"
    
    def test_llr_calculation_performance(self):
        """测试LLR计算的性能"""
        print(f"\n=== 测试 LLR计算 性能 ===")
        
        m, n = 128, 256
        H = self._create_sparse_matrix(m, n)
        decoder = LDPCDecoder(H)
        
        # 生成测试数据
        received_signal = self.rng.normal(0, 1, n)
        received_bits = self.rng.integers(0, 2, n)
        
        # 测试AWGN LLR计算
        _, awgn_time = self._measure_performance(
            decoder.awgn_llr, received_signal, 0.5
        )
        
        # 测试BSC LLR计算
        _, bsc_time = self._measure_performance(
            decoder.bsc_llr, received_bits, 0.1
        )
        
        # 记录结果
        self.performance_results["llr_calculation"] = {
            "awgn_time": awgn_time,
            "bsc_time": bsc_time
        }
        
        print(f"AWGN LLR计算时间: {awgn_time:.6f}s")
        print(f"BSC LLR计算时间: {bsc_time:.6f}s")
        
        # LLR计算应该很快
        assert awgn_time < 0.01, f"AWGN LLR计算过慢：{awgn_time:.6f}s"
        assert bsc_time < 0.01, f"BSC LLR计算过慢：{bsc_time:.6f}s"
    
    def test_batch_decode_performance(self):
        """测试批量解码性能"""
        print(f"\n=== 测试批量解码性能 ===")
        
        m, n = 64, 128
        batch_size = 10
        
        H = self._create_sparse_matrix(m, n)
        encoder = LDPCEncoder(H)
        decoder = LDPCDecoder(H, max_iterations=30)
        
        # 生成批量测试数据
        llr_batch = []
        for _ in range(batch_size):
            llr, _ = self._generate_test_data(encoder, decoder, noise_var=0.2)
            llr_batch.append(llr)
        
        # 测量批量解码性能
        start_time = time.time()
        results = []
        for llr in llr_batch:
            decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
            results.append((decoded_bits, stats))
        total_time = time.time() - start_time
        
        # 计算统计信息
        avg_time_per_decode = total_time / batch_size
        total_iterations = sum(stats["iterations"] for _, stats in results)
        avg_iterations = total_iterations / batch_size
        convergence_rate = sum(1 for _, stats in results if stats["converged"]) / batch_size
        
        # 记录结果
        self.performance_results["batch_decode"] = {
            "total_time": total_time,
            "avg_time_per_decode": avg_time_per_decode,
            "avg_iterations": avg_iterations,
            "convergence_rate": convergence_rate,
            "batch_size": batch_size
        }
        
        print(f"批量解码总时间: {total_time:.4f}s")
        print(f"平均每次解码时间: {avg_time_per_decode:.4f}s")
        print(f"平均迭代次数: {avg_iterations:.1f}")
        print(f"收敛率: {convergence_rate:.1%}")
        
        # 性能断言
        assert avg_time_per_decode < 1.0, f"单次解码时间过长：{avg_time_per_decode:.4f}s"
        assert convergence_rate > 0.5, f"收敛率过低：{convergence_rate:.1%}"
    
    def test_early_termination_performance(self):
        """测试早期终止对性能的影响"""
        print(f"\n=== 测试早期终止性能影响 ===")
        
        m, n = 64, 128
        H = self._create_sparse_matrix(m, n)
        encoder = LDPCEncoder(H)
        
        # 创建启用和禁用早期终止的解码器
        decoder_early = LDPCDecoder(H, max_iterations=50, early_termination=True)
        decoder_no_early = LDPCDecoder(H, max_iterations=50, early_termination=False)
        
        # 生成高质量测试数据（容易收敛）
        llr, _ = self._generate_test_data(encoder, decoder_early, noise_var=0.05)
        
        # 测试启用早期终止
        (_, stats_early), time_early = self._measure_performance(
            decoder_early.decode, llr, algorithm="min_sum"
        )
        
        # 测试禁用早期终止
        (_, stats_no_early), time_no_early = self._measure_performance(
            decoder_no_early.decode, llr, algorithm="min_sum"
        )
        
        # 记录结果
        self.performance_results["early_termination"] = {
            "early_time": time_early,
            "no_early_time": time_no_early,
            "early_iterations": stats_early["iterations"],
            "no_early_iterations": stats_no_early["iterations"],
            "speedup": time_no_early / time_early if time_early > 0 else float('inf')
        }
        
        print(f"启用早期终止: 时间={time_early:.4f}s, 迭代={stats_early['iterations']}")
        print(f"禁用早期终止: 时间={time_no_early:.4f}s, 迭代={stats_no_early['iterations']}")
        print(f"早期终止加速比: {time_no_early/time_early:.2f}x")
        
        # 早期终止应该减少迭代次数和时间
        assert stats_early["iterations"] <= stats_no_early["iterations"], "早期终止应该减少迭代次数"
        assert time_early <= time_no_early, "早期终止应该减少解码时间"
    
    def test_scaling_factor_performance(self):
        """测试不同Min-Sum缩放因子对性能的影响"""
        print(f"\n=== 测试Min-Sum缩放因子性能影响 ===")
        
        m, n = 64, 128
        H = self._create_sparse_matrix(m, n)
        encoder = LDPCEncoder(H)
        
        scaling_factors = [0.5, 0.7, 0.9, 1.0]
        results = {}
        
        # 生成测试数据
        llr, _ = self._generate_test_data(encoder, LDPCDecoder(H), noise_var=0.2)
        
        for scaling in scaling_factors:
            decoder = LDPCDecoder(H, max_iterations=30, min_sum_scaling=scaling)
            
            # 测量性能
            (_, stats), exec_time = self._measure_performance(
                decoder.decode, llr, algorithm="min_sum"
            )
            
            results[scaling] = {
                "time": exec_time,
                "iterations": stats["iterations"],
                "converged": stats["converged"]
            }
            
            print(f"缩放因子={scaling}: 时间={exec_time:.4f}s, 迭代={stats['iterations']}, 收敛={stats['converged']}")
        
        # 记录结果
        self.performance_results["scaling_factors"] = results
        
        # 验证所有缩放因子都能在合理时间内完成
        for scaling, result in results.items():
            assert result["time"] < 3.0, f"缩放因子{scaling}解码时间过长：{result['time']:.4f}s"
    
    def test_memory_efficiency(self):
        """测试解码器内存效率"""
        print(f"\n=== 测试解码器内存效率 ===")
        
        m, n = 96, 192
        H = self._create_sparse_matrix(m, n)
        
        import psutil
        process = psutil.Process()
        
        # 测量初始内存
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 创建解码器
        decoder = LDPCDecoder(H, max_iterations=30)
        encoder = LDPCEncoder(H)
        
        # 测量解码器创建后内存
        after_creation_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行多次解码
        for _ in range(5):
            llr, _ = self._generate_test_data(encoder, decoder, noise_var=0.2)
            decoder.decode(llr, algorithm="min_sum")
        
        # 测量解码后内存
        after_decode_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_overhead = after_creation_memory - initial_memory
        memory_growth = after_decode_memory - after_creation_memory
        
        # 记录结果
        self.performance_results["memory_efficiency"] = {
            "initial_memory_mb": initial_memory,
            "creation_overhead_mb": memory_overhead,
            "decode_growth_mb": memory_growth,
            "total_memory_mb": after_decode_memory
        }
        
        print(f"初始内存: {initial_memory:.1f} MB")
        print(f"创建解码器开销: {memory_overhead:.1f} MB")
        print(f"解码过程增长: {memory_growth:.1f} MB")
        print(f"总内存使用: {after_decode_memory:.1f} MB")
        
        # 内存使用应该在合理范围内
        assert memory_overhead < 100, f"解码器内存开销过大：{memory_overhead:.1f} MB"
        assert memory_growth < 50, f"解码过程内存增长过大：{memory_growth:.1f} MB"
    
    def test_comprehensive_performance_profile(self):
        """综合性能测试报告"""
        print(f"\n=== 综合性能测试报告 ===")
        
        m, n = 64, 128
        H = self._create_sparse_matrix(m, n)
        encoder = LDPCEncoder(H)
        decoder = LDPCDecoder(H, max_iterations=50)
        
        # 测试各种场景
        test_scenarios = [
            ("低噪声", 0.05),
            ("中等噪声", 0.2),
            ("高噪声", 0.5),
        ]
        
        profile_results = {}
        
        for scenario_name, noise_var in test_scenarios:
            # 生成测试数据
            llr, original_codeword = self._generate_test_data(encoder, decoder, noise_var)
            
            # 测试Min-Sum
            start_time = time.time()
            decoded_bits, stats = decoder.decode(llr, algorithm="min_sum")
            decode_time = time.time() - start_time
            
            # 验证解码质量
            if stats["converged"] and stats["parity_check_satisfied"]:
                recovered_info = decoder.extract_information_bits(decoded_bits)
                original_info = encoder.extract_information_bits(original_codeword) if hasattr(encoder, 'extract_information_bits') else original_codeword[:encoder.k]
                bit_errors = np.sum(recovered_info != original_info) if len(recovered_info) == len(original_info) else -1
            else:
                bit_errors = -1
            
            profile_results[scenario_name] = {
                "noise_variance": noise_var,
                "decode_time": decode_time,
                "iterations": stats["iterations"],
                "converged": stats["converged"],
                "bit_errors": bit_errors,
                "throughput_mbps": (n / decode_time) / 1e6 if decode_time > 0 else 0
            }
            
            print(f"{scenario_name} (σ²={noise_var}):")
            print(f"  解码时间: {decode_time:.4f}s")
            print(f"  迭代次数: {stats['iterations']}")
            print(f"  收敛状态: {stats['converged']}")
            print(f"  比特错误: {bit_errors}")
            print(f"  吞吐量: {profile_results[scenario_name]['throughput_mbps']:.2f} Mbps")
        
        # 记录综合结果
        self.performance_results["comprehensive_profile"] = profile_results
        
        # 验证关键性能指标
        for scenario, result in profile_results.items():
            assert result["decode_time"] < 5.0, f"{scenario}场景解码时间过长"
            assert result["throughput_mbps"] > 0.01, f"{scenario}场景吞吐量过低"
    
    def teardown_method(self):
        """测试后清理和性能总结"""
        if self.performance_results:
            print(f"\n{'='*60}")
            print("解码器性能测试总结")
            print(f"{'='*60}")
            
            for test_name, results in self.performance_results.items():
                if isinstance(results, dict) and "time" in results:
                    print(f"{test_name}: {results['time']:.4f}s")
                elif isinstance(results, dict):
                    print(f"{test_name}: {results}")
                else:
                    print(f"{test_name}: {results}")
            
            print(f"{'='*60}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 