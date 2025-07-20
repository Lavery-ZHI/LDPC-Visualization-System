"""
解码器API集成测试：/api/v1/decode
运行：
    # 从backend目录运行：
    cd Code/backend && pytest tests/integration/test_decoder_api.py -v -s
"""
import sys
import os
import numpy as np
import pytest
from fastapi.testclient import TestClient

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from main import app
from algorithms.ldpc_encoder import LDPCEncoder
from algorithms.ldpc_decoder import LDPCDecoder

client = TestClient(app, raise_server_exceptions=False)
pytestmark = pytest.mark.integration


class TestLDPCDecoderAPI:
    """LDPC解码器API集成测试"""
    
    def setup_method(self):
        """设置测试数据"""
        # 简单的LDPC码 (4,1,3)
        self.H_simple = [
            [1, 1, 1, 0],
            [1, 0, 1, 1],
            [0, 1, 1, 1]
        ]
        
        # 中等规模的LDPC码 (7,3,4)
        self.H_medium = [
            [1, 1, 1, 0, 0, 0, 0],
            [1, 0, 0, 1, 1, 0, 0],
            [0, 1, 0, 1, 0, 1, 0],
            [0, 0, 1, 0, 1, 1, 1]
        ]
        
        self.rng = np.random.default_rng(42)

    def test_decode_with_direct_llr(self):
        """测试直接提供LLR的解码"""
        # 生成测试LLR
        llr = [2.0, -1.5, 0.8, -2.2]  # 对应码字 [0, 1, 0, 1]
        
        request = {
            "llr": llr,
            "h_matrix": self.H_simple,
            "algorithm": "min_sum",
            "max_iterations": 50
        }
        
        response = client.post("/api/v1/decode", json=request)
        assert response.status_code == 200, response.text
        
        data = response.json()
        
        # 验证响应字段
        required_fields = ["decoded_bits", "information_bits", "statistics", 
                         "h_matrix", "code_parameters", "message"]
        for field in required_fields:
            assert field in data, f"缺少字段: {field}"
        
        # 验证解码结果
        assert len(data["decoded_bits"]) == 4, "解码结果长度错误"
        assert len(data["information_bits"]) == 1, "信息位长度错误"
        
        # 验证码参数
        code_params = data["code_parameters"]
        assert code_params["n"] == 4
        assert code_params["k"] == 1
        assert code_params["m"] == 3
        assert code_params["rate"] == 0.25
        
        # 验证统计信息
        stats = data["statistics"]
        assert "iterations" in stats
        assert "converged" in stats
        assert "parity_check_satisfied" in stats
        assert stats["iterations"] > 0

    def test_decode_with_awgn_signal(self):
        """测试AWGN信道接收信号的解码"""
        # 生成BPSK信号 (1->1, 0->-1) + 噪声
        received_signal = [0.8, -0.5, 0.2, -1.2]
        noise_variance = 0.5
        
        request = {
            "received_signal": received_signal,
            "noise_variance": noise_variance,
            "h_matrix": self.H_simple,
            "channel_type": "awgn",
            "algorithm": "min_sum"
        }
        
        response = client.post("/api/v1/decode", json=request)
        assert response.status_code == 200, response.text
        
        data = response.json()
        
        # 验证解码成功
        assert len(data["decoded_bits"]) == 4
        assert len(data["information_bits"]) == 1
        assert data["statistics"]["iterations"] > 0

    def test_decode_with_bsc_bits(self):
        """测试BSC信道接收比特的解码"""
        received_bits = [1, 0, 1, 0]
        crossover_prob = 0.1
        
        request = {
            "received_bits": received_bits,
            "crossover_probability": crossover_prob,
            "h_matrix": self.H_simple,
            "channel_type": "bsc",
            "algorithm": "min_sum"
        }
        
        response = client.post("/api/v1/decode", json=request)
        assert response.status_code == 200, response.text
        
        data = response.json()
        
        # 验证解码成功
        assert len(data["decoded_bits"]) == 4
        assert len(data["information_bits"]) == 1

    def test_decode_algorithm_comparison(self):
        """测试不同解码算法"""
        llr = [1.5, -2.0, 0.5, -1.0]
        
        for algorithm in ["min_sum", "sum_product"]:
            request = {
                "llr": llr,
                "h_matrix": self.H_simple,
                "algorithm": algorithm,
                "max_iterations": 30
            }
            
            response = client.post("/api/v1/decode", json=request)
            assert response.status_code == 200, f"{algorithm}算法解码失败: {response.text}"
            
            data = response.json()
            assert len(data["decoded_bits"]) == 4
            assert data["statistics"]["iterations"] > 0

    def test_decode_parameters_validation(self):
        """测试解码参数验证"""
        base_request = {
            "llr": [1.0, -1.0, 0.5, -0.5],
            "h_matrix": self.H_simple
        }
        
        # 测试不同参数组合
        test_cases = [
            # 有效参数
            {**base_request, "max_iterations": 20, "early_termination": True},
            {**base_request, "min_sum_scaling": 0.8, "algorithm": "min_sum"},
            {**base_request, "algorithm": "sum_product"},
            
            # 边界参数
            {**base_request, "max_iterations": 1},
            {**base_request, "max_iterations": 200},
            {**base_request, "min_sum_scaling": 0.1},
        ]
        
        for i, request in enumerate(test_cases):
            response = client.post("/api/v1/decode", json=request)
            assert response.status_code == 200, f"测试案例{i}失败: {response.text}"

    def test_medium_scale_decode(self):
        """测试中等规模解码"""
        # 生成测试LLR
        llr = self.rng.normal(0, 1, 7).tolist()
        
        request = {
            "llr": llr,
            "h_matrix": self.H_medium,
            "algorithm": "min_sum",
            "max_iterations": 50
        }
        
        response = client.post("/api/v1/decode", json=request)
        assert response.status_code == 200, response.text
        
        data = response.json()
        
        # 验证中等规模解码
        assert len(data["decoded_bits"]) == 7
        assert len(data["information_bits"]) == 3
        assert data["code_parameters"]["n"] == 7
        assert data["code_parameters"]["k"] == 3

    def test_encode_decode_roundtrip(self):
        """测试编码-解码往返"""
        # 先编码
        encode_request = {
            "h_matrix": self.H_simple,
            "info_bits": [1]
        }
        
        encode_response = client.post("/api/v1/encode", json=encode_request)
        assert encode_response.status_code == 200
        
        encode_data = encode_response.json()
        codeword = encode_data["codeword"]
        
        # 模拟BPSK + AWGN
        bpsk_signal = [1 - 2*bit for bit in codeword]  # 0->1, 1->-1
        noise = self.rng.normal(0, 0.1, len(codeword)).tolist()
        noisy_signal = [s + n for s, n in zip(bpsk_signal, noise)]
        
        # 解码
        decode_request = {
            "received_signal": noisy_signal,
            "noise_variance": 0.01,
            "h_matrix": self.H_simple,
            "channel_type": "awgn",
            "algorithm": "min_sum"
        }
        
        decode_response = client.post("/api/v1/decode", json=decode_request)
        assert decode_response.status_code == 200
        
        decode_data = decode_response.json()
        
        # 验证往返一致性
        assert decode_data["information_bits"] == [1], "信息位恢复错误"
        assert decode_data["statistics"]["converged"], "解码应该收敛"

    def test_invalid_input_validation(self):
        """测试无效输入验证"""
        # 测试各种无效输入
        invalid_cases = [
            # 缺少必需字段
            {"llr": [1, 2, 3, 4]},  # 缺少h_matrix
            
            # 无效的算法
            {
                "llr": [1, 2, 3, 4],
                "h_matrix": self.H_simple,
                "algorithm": "invalid_algorithm"
            },
            
            # 无效的信道类型
            {
                "received_signal": [1, 2, 3, 4],
                "h_matrix": self.H_simple,
                "channel_type": "invalid_channel"
            },
            
            # LLR长度错误
            {
                "llr": [1, 2, 3],  # 应该是4个元素
                "h_matrix": self.H_simple
            },
            
            # AWGN信道使用received_bits
            {
                "received_bits": [1, 0, 1, 0],
                "h_matrix": self.H_simple,
                "channel_type": "awgn"
            },
            
            # BSC信道使用received_signal
            {
                "received_signal": [1.0, 2.0, 3.0, 4.0],
                "h_matrix": self.H_simple,
                "channel_type": "bsc"
            },
            
            # 无效的参数范围
            {
                "llr": [1, 2, 3, 4],
                "h_matrix": self.H_simple,
                "max_iterations": 0  # 应该 >= 1
            },
            
            {
                "llr": [1, 2, 3, 4],
                "h_matrix": self.H_simple,
                "min_sum_scaling": 1.5  # 应该 <= 1.0
            }
        ]
        
        for i, invalid_request in enumerate(invalid_cases):
            response = client.post("/api/v1/decode", json=invalid_request)
            assert response.status_code == 422 or response.status_code == 400, \
                f"无效案例{i}应该返回错误状态码，实际返回: {response.status_code}"

    def test_missing_input_validation(self):
        """测试缺少输入的验证"""
        # 既不提供LLR，也不提供接收信号/比特
        request = {
            "h_matrix": self.H_simple,
            "algorithm": "min_sum"
        }
        
        response = client.post("/api/v1/decode", json=request)
        assert response.status_code == 422 or response.status_code == 400

    def test_multiple_input_validation(self):
        """测试提供多种输入的验证"""
        # 同时提供LLR和接收信号
        request = {
            "llr": [1, 2, 3, 4],
            "received_signal": [1, 2, 3, 4],
            "h_matrix": self.H_simple
        }
        
        response = client.post("/api/v1/decode", json=request)
        assert response.status_code == 422 or response.status_code == 400

    def test_concurrent_decode_requests(self):
        """测试并发解码请求"""
        import concurrent.futures
        
        def make_decode_request(i):
            llr = [1.0 + i*0.1, -1.0 - i*0.1, 0.5 + i*0.05, -0.5 - i*0.05]
            request = {
                "llr": llr,
                "h_matrix": self.H_simple,
                "algorithm": "min_sum",
                "max_iterations": 30
            }
            
            response = client.post("/api/v1/decode", json=request)
            assert response.status_code == 200
            return response.json()
        
        # 并发执行10个解码请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_decode_request, i) for i in range(10)]
            results = [future.result() for future in futures]
        
        # 验证所有请求都成功
        assert len(results) == 10
        for result in results:
            assert len(result["decoded_bits"]) == 4
            assert len(result["information_bits"]) == 1

    def test_performance_large_matrix(self):
        """测试大矩阵性能"""
        # 创建较大的H矩阵
        m, n = 32, 64
        H_large = np.random.binomial(1, 0.1, size=(m, n))
        # 确保满秩
        while np.linalg.matrix_rank(H_large % 2) < m:
            H_large = np.random.binomial(1, 0.1, size=(m, n))
        
        # 生成随机LLR
        llr = self.rng.normal(0, 1, n).tolist()
        
        request = {
            "llr": llr,
            "h_matrix": H_large.tolist(),
            "algorithm": "min_sum",
            "max_iterations": 20
        }
        
        import time
        start_time = time.time()
        response = client.post("/api/v1/decode", json=request)
        end_time = time.time()
        
        assert response.status_code == 200
        
        data = response.json()
        execution_time = end_time - start_time
        
        # 验证性能
        assert len(data["decoded_bits"]) == n
        assert execution_time < 10.0, f"大矩阵解码时间过长: {execution_time:.2f}s"
        
        print(f"大矩阵({m}×{n})解码时间: {execution_time:.4f}s")
        print(f"迭代次数: {data['statistics']['iterations']}")

    def test_api_error_handling(self):
        """测试API错误处理"""
        # 测试格式错误的H矩阵
        request = {
            "llr": [1, 2, 3, 4],
            "h_matrix": [[1, 1], [0]]  # 不规则矩阵
        }
        
        response = client.post("/api/v1/decode", json=request)
        assert response.status_code == 400 or response.status_code == 422
        
        # 测试空矩阵
        request = {
            "llr": [],
            "h_matrix": []
        }
        
        response = client.post("/api/v1/decode", json=request)
        assert response.status_code == 400 or response.status_code == 422

    def test_statistics_completeness(self):
        """测试统计信息完整性"""
        request = {
            "llr": [2.0, -1.5, 0.8, -2.2],
            "h_matrix": self.H_simple,
            "algorithm": "min_sum"
        }
        
        response = client.post("/api/v1/decode", json=request)
        assert response.status_code == 200
        
        data = response.json()
        stats = data["statistics"]
        
        # 验证统计信息包含所有必要字段
        required_stats = ["iterations", "converged", "syndrome_weight", 
                         "final_llr", "parity_check_satisfied"]
        for stat in required_stats:
            assert stat in stats, f"缺少统计信息: {stat}"
        
        # 验证统计信息类型
        assert isinstance(stats["iterations"], int)
        assert isinstance(stats["converged"], bool)
        assert isinstance(stats["syndrome_weight"], int)
        assert isinstance(stats["final_llr"], list)
        assert isinstance(stats["parity_check_satisfied"], bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 