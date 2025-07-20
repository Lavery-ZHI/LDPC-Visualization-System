"""
LDPC编码器性能测试
测试大尺寸矩阵的性能指标，确保符合<1s的要求

运行：
    # 从backend目录运行：
    cd Code/backend && pytest tests/performance/test_encoder_perf.py -v -s
    
    # 或者从Code目录运行：
    cd Code && python -m pytest backend/tests/performance/test_encoder_perf.py -v -s
"""
import time
import sys
import os
import numpy as np
import scipy.sparse as sp
import pytest

# 添加backend目录到路径，以便导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from algorithms.ldpc_encoder import LDPCEncoder


class TestLDPCEncoderPerformance:
    """LDPC编码器性能测试"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.performance_results = {}
    
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
        print(f"随机生成失败，使用确定性方法生成 {m}×{n} 矩阵")
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
    
    @pytest.mark.parametrize("m,n,expected_max_time", [
        (50, 100, 1.0),   # 小规模：< 1s
        (100, 200, 1.0),  # 中规模：< 1s  
        (150, 300, 1.0),  # 大规模：< 1s
    ])
    def test_generate_g_matrix_performance(self, m, n, expected_max_time):
        """测试generate_g_matrix的性能"""
        print(f"\n=== 测试 generate_g_matrix 性能 ({m}×{n}) ===")
        
        # 创建测试矩阵
        H = self._create_sparse_matrix(m, n)
        encoder = LDPCEncoder(H)
        
        # 测量性能
        G, exec_time = self._measure_performance(encoder.generate_g_matrix)
        
        # 记录结果
        self.performance_results[f"generate_g_matrix_{m}x{n}"] = exec_time
        
        # 验证结果正确性
        assert G.shape == (encoder.k, n), f"G矩阵形状错误：{G.shape} != {(encoder.k, n)}"
        
        # 验证正交性
        H_dense = H.toarray()
        orthogonality = (H_dense @ G.T) % 2
        assert np.all(orthogonality == 0), "正交性检查失败"
        
        # 性能断言
        print(f"generate_g_matrix 执行时间: {exec_time:.4f}s")
        assert exec_time < expected_max_time, f"性能不达标：{exec_time:.4f}s > {expected_max_time}s"
    
    @pytest.mark.parametrize("m,n,expected_max_time", [
        (50, 100, 0.1),   # 编码应该很快
        (100, 200, 0.1),  
        (150, 300, 0.1),
    ])
    def test_encode_performance(self, m, n, expected_max_time):
        """测试encode方法的性能"""
        print(f"\n=== 测试 encode 性能 ({m}×{n}) ===")
        
        # 创建测试矩阵和编码器
        H = self._create_sparse_matrix(m, n)
        encoder = LDPCEncoder(H)
        
        # 预先生成G矩阵（不计入编码时间）
        encoder.generate_g_matrix()
        
        # 生成随机信息位
        info_bits = np.random.randint(0, 2, size=encoder.k)
        
        # 测量编码性能
        codeword, exec_time = self._measure_performance(encoder.encode, info_bits)
        
        # 记录结果
        self.performance_results[f"encode_{m}x{n}"] = exec_time
        
        # 验证结果正确性
        assert len(codeword) == n, f"码字长度错误：{len(codeword)} != {n}"
        
        # 验证码字满足校验方程
        H_dense = H.toarray()
        assert np.all((H_dense @ codeword) % 2 == 0), "编码结果校验失败"
        
        # 性能断言
        print(f"encode 执行时间: {exec_time:.4f}s")
        assert exec_time < expected_max_time, f"编码性能不达标：{exec_time:.4f}s > {expected_max_time}s"
    
    def test_validate_code_structure_performance(self):
        """测试validate_code_structure的性能"""
        print(f"\n=== 测试 validate_code_structure 性能 ===")
        
        m, n = 100, 200
        H = self._create_sparse_matrix(m, n)
        encoder = LDPCEncoder(H)
        
        # 测量性能
        validation_result, exec_time = self._measure_performance(encoder.validate_code_structure)
        
        # 记录结果
        self.performance_results["validate_code_structure"] = exec_time
        
        # 验证结果正确性
        assert validation_result["is_orthogonal"], "结构验证失败"
        assert validation_result["k"] == encoder.k, "k值不一致"
        assert validation_result["n"] == encoder.n, "n值不一致"
        
        # 性能断言（验证应该在合理时间内完成）
        print(f"validate_code_structure 执行时间: {exec_time:.4f}s")
        assert exec_time < 2.0, f"结构验证性能不达标：{exec_time:.4f}s > 2.0s"
    
    def test_comprehensive_workflow_performance(self):
        """测试完整工作流程的性能"""
        print(f"\n=== 测试完整工作流程性能 ===")
        
        m, n = 100, 200
        H = self._create_sparse_matrix(m, n)
        
        # 测量整个工作流程
        start_time = time.time()
        
        # 1. 初始化编码器
        encoder = LDPCEncoder(H)
        
        # 2. 生成G矩阵
        G = encoder.generate_g_matrix()
        
        # 3. 编码多个信息位
        num_encodings = 10
        for i in range(num_encodings):
            info_bits = np.random.randint(0, 2, size=encoder.k)
            codeword = encoder.encode(info_bits)
        
        # 4. 验证结构
        validation = encoder.validate_code_structure()
        
        total_time = time.time() - start_time
        
        # 记录结果
        self.performance_results["comprehensive_workflow"] = total_time
        
        print(f"完整工作流程执行时间: {total_time:.4f}s")
        print(f"平均每次编码时间: {total_time/num_encodings:.4f}s")
        
        # 性能断言
        assert total_time < 5.0, f"完整工作流程性能不达标：{total_time:.4f}s > 5.0s"
        
        # 验证正确性
        assert validation["is_orthogonal"], "工作流程验证失败"
    
    def test_memory_efficiency(self):
        """测试大矩阵的内存效率"""
        print(f"\n=== 测试内存效率 ===")
        
        # 使用较大的稀疏矩阵
        m, n = 200, 400
        density = 0.02  # 降低密度以测试稀疏矩阵处理
        
        H = self._create_sparse_matrix(m, n, density)
        
        # 验证矩阵确实是稀疏的
        sparsity = 1.0 - (H.nnz / (m * n))
        print(f"矩阵稀疏度: {sparsity:.2%}")
        assert sparsity > 0.9, "矩阵不够稀疏"
        
        # 测试编码器能否处理大型稀疏矩阵
        start_time = time.time()
        encoder = LDPCEncoder(H)
        G = encoder.generate_g_matrix()
        
        # 进行多次编码
        for _ in range(5):
            info_bits = np.random.randint(0, 2, size=encoder.k)
            codeword = encoder.encode(info_bits)
        
        exec_time = time.time() - start_time
        
        print(f"大型稀疏矩阵处理时间: {exec_time:.4f}s")
        assert exec_time < 3.0, f"大型稀疏矩阵处理性能不达标：{exec_time:.4f}s > 3.0s"
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        if hasattr(self, 'performance_results') and self.performance_results:
            print("\n=== 性能测试结果汇总 ===")
            for test_name, exec_time in self.performance_results.items():
                print(f"{test_name}: {exec_time:.4f}s")


if __name__ == "__main__":
    # 直接运行性能测试
    test_instance = TestLDPCEncoderPerformance()
    
    # 运行主要性能测试
    test_instance.setup_method()
    test_instance.test_generate_g_matrix_performance(100, 200, 1.0)
    test_instance.test_encode_performance(100, 200, 0.1)
    test_instance.test_validate_code_structure_performance()
    test_instance.test_comprehensive_workflow_performance()
    test_instance.test_memory_efficiency()
    test_instance.teardown_method()
    
    print("\n✅ 所有性能测试通过！") 