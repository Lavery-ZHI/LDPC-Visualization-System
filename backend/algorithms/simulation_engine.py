"""LDPC 仿真引擎模块 - 集成编码器和解码器进行 BER 性能仿真。"""
from __future__ import annotations

import numpy as np
import time
from typing import Dict, List, Tuple, Callable, Optional, Any
from dataclasses import dataclass

from .ldpc_encoder import LDPCEncoder
from .ldpc_decoder import LDPCDecoder

__all__ = ["SimulationEngine", "SimulationResults", "SimulationConfig"]


@dataclass
class SimulationConfig:
    """仿真配置参数。"""
    snr_range: List[float]  # SNR 范围 (dB)
    frame_count: int = 1000  # 每个 SNR 点的帧数
    max_errors: int = 100  # 最大错误帧数（早期停止条件）
    min_frames: int = 100  # 最小仿真帧数
    channel_type: str = "awgn"  # 信道类型: "awgn", "bsc"
    decoder_algorithm: str = "min_sum"  # 解码算法
    max_iterations: int = 50  # 解码最大迭代次数
    min_sum_scaling: float = 0.9  # Min-Sum 缩放因子
    early_termination: bool = True  # 解码早期终止
    progress_interval: int = 10  # 进度回调间隔（帧数）


@dataclass
class SimulationResults:
    """仿真结果数据。"""
    snr_db: List[float]  # SNR 点 (dB)
    ber: List[float]  # 误比特率
    fer: List[float]  # 误帧率
    total_frames: List[int]  # 每个 SNR 点的总帧数
    error_frames: List[int]  # 每个 SNR 点的错误帧数
    avg_iterations: List[float]  # 平均迭代次数
    simulation_time: float  # 总仿真时间 (秒)
    config: SimulationConfig  # 仿真配置


class SimulationEngine:
    """LDPC 仿真引擎 - 执行 BER/FER 性能仿真。"""

    def __init__(self, h_matrix: np.ndarray):
        """
        初始化仿真引擎。

        参数:
            h_matrix: LDPC 奇偶校验矩阵
        """
        self.h_matrix = np.asarray(h_matrix, dtype=int)
        
        # 初始化编码器和解码器
        self.encoder = LDPCEncoder(h_matrix)
        self.decoder = LDPCDecoder(h_matrix)
        
        # 码参数
        self.n = self.decoder.n  # 码长
        self.k = self.decoder.k  # 信息位长度
        self.rate = self.decoder.rate  # 码率
        
        # 仿真状态
        self.is_running = False
        self.should_stop = False

    def run_ber_simulation(
        self,
        config: SimulationConfig,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> SimulationResults:
        """
        运行 BER/FER 性能仿真。

        参数:
            config: 仿真配置
            progress_callback: 进度回调函数

        返回:
            仿真结果
        """
        self.is_running = True
        self.should_stop = False
        start_time = time.time()

        # 更新解码器参数
        self.decoder.max_iterations = config.max_iterations
        self.decoder.min_sum_scaling = config.min_sum_scaling
        self.decoder.early_termination = config.early_termination

        # 结果存储
        snr_results = []
        ber_results = []
        fer_results = []
        total_frames_results = []
        error_frames_results = []
        avg_iterations_results = []

        total_snr_points = len(config.snr_range)

        for snr_idx, snr_db in enumerate(config.snr_range):
            if self.should_stop:
                break

            # 单个 SNR 点仿真
            snr_result = self._simulate_snr_point(
                snr_db, config, snr_idx, total_snr_points, progress_callback
            )

            snr_results.append(snr_db)
            ber_results.append(snr_result['ber'])
            fer_results.append(snr_result['fer'])
            total_frames_results.append(snr_result['total_frames'])
            error_frames_results.append(snr_result['error_frames'])
            avg_iterations_results.append(snr_result['avg_iterations'])

        simulation_time = time.time() - start_time
        self.is_running = False

        return SimulationResults(
            snr_db=snr_results,
            ber=ber_results,
            fer=fer_results,
            total_frames=total_frames_results,
            error_frames=error_frames_results,
            avg_iterations=avg_iterations_results,
            simulation_time=simulation_time,
            config=config
        )

    def _simulate_snr_point(
        self,
        snr_db: float,
        config: SimulationConfig,
        snr_idx: int,
        total_snr_points: int,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """仿真单个 SNR 点。"""
        
        # 统计变量
        total_frames = 0
        error_frames = 0
        total_bit_errors = 0
        total_iterations = 0

        # 噪声方差计算 (对于 AWGN)
        if config.channel_type == "awgn":
            noise_variance = 10 ** (-snr_db / 10) / (2 * self.rate)
        elif config.channel_type == "bsc":
            # BSC 的交叉概率与 SNR 的关系 (简化模型)
            crossover_prob = 0.5 * np.exp(-10 ** (snr_db / 10))
            crossover_prob = np.clip(crossover_prob, 1e-6, 0.49)

        while (total_frames < config.frame_count and 
               (error_frames < config.max_errors or total_frames < config.min_frames)):
            
            if self.should_stop:
                break

            # 生成随机信息位
            info_bits = np.random.randint(0, 2, self.k)
            
            # 编码
            try:
                encoded_bits = self.encoder.encode(info_bits)
            except Exception as e:
                print(f"编码错误: {e}")
                continue

            # 信道传输
            if config.channel_type == "awgn":
                received_signal, received_bits = self._awgn_channel(
                    encoded_bits, noise_variance
                )
                # 计算 LLR
                llr = self.decoder.awgn_llr(received_signal, noise_variance)
            elif config.channel_type == "bsc":
                received_bits = self._bsc_channel(encoded_bits, crossover_prob)
                # 计算 LLR
                llr = self.decoder.bsc_llr(received_bits, crossover_prob)
            else:
                raise ValueError(f"不支持的信道类型: {config.channel_type}")

            # 解码
            try:
                decoded_bits, decode_stats = self.decoder.decode(
                    llr, config.decoder_algorithm
                )
                total_iterations += decode_stats['iterations']
            except Exception as e:
                print(f"解码错误: {e}")
                continue

            # 提取信息位
            try:
                decoded_info_bits = self.decoder.extract_information_bits(decoded_bits)
            except Exception as e:
                print(f"信息位提取错误: {e}")
                continue

            # 错误统计
            bit_errors = np.sum(info_bits != decoded_info_bits)
            total_bit_errors += bit_errors
            
            if bit_errors > 0:
                error_frames += 1

            total_frames += 1

            # 进度回调
            if (progress_callback and 
                total_frames % config.progress_interval == 0):
                
                current_ber = total_bit_errors / (total_frames * self.k) if total_frames > 0 else 0
                current_fer = error_frames / total_frames if total_frames > 0 else 0
                
                progress_info = {
                    'snr_idx': snr_idx,
                    'total_snr_points': total_snr_points,
                    'snr_db': snr_db,
                    'frames_completed': total_frames,
                    'total_frames_target': config.frame_count,
                    'error_frames': error_frames,
                    'current_ber': current_ber,
                    'current_fer': current_fer,
                    'avg_iterations': total_iterations / total_frames if total_frames > 0 else 0
                }
                progress_callback(progress_info)

        # 计算最终结果
        ber = total_bit_errors / (total_frames * self.k) if total_frames > 0 else 0
        fer = error_frames / total_frames if total_frames > 0 else 0
        avg_iterations = total_iterations / total_frames if total_frames > 0 else 0

        return {
            'ber': ber,
            'fer': fer,
            'total_frames': total_frames,
            'error_frames': error_frames,
            'avg_iterations': avg_iterations
        }

    def _awgn_channel(self, transmitted_bits: np.ndarray, noise_variance: float) -> Tuple[np.ndarray, np.ndarray]:
        """AWGN 信道模拟。"""
        # BPSK 调制: 0 -> +1, 1 -> -1
        transmitted_signal = 1 - 2 * transmitted_bits.astype(float)
        
        # 添加高斯噪声
        noise = np.random.normal(0, np.sqrt(noise_variance), len(transmitted_signal))
        received_signal = transmitted_signal + noise
        
        # 硬判决 (仅用于统计)
        received_bits = (received_signal < 0).astype(int)
        
        return received_signal, received_bits

    def _bsc_channel(self, transmitted_bits: np.ndarray, crossover_prob: float) -> np.ndarray:
        """BSC 信道模拟。"""
        # 生成随机翻转模式
        flip_mask = np.random.random(len(transmitted_bits)) < crossover_prob
        received_bits = transmitted_bits ^ flip_mask.astype(int)
        return received_bits

    def stop_simulation(self):
        """停止仿真。"""
        self.should_stop = True

    def get_code_info(self) -> Dict[str, Any]:
        """获取码信息。"""
        return {
            'n': self.n,
            'k': self.k,
            'm': self.decoder.m,
            'rate': self.rate,
            'variable_degrees': [len(self.decoder.var_to_check[i]) for i in range(self.n)],
            'check_degrees': [len(self.decoder.check_to_var[i]) for i in range(self.decoder.m)]
        }

    def estimate_simulation_time(self, config: SimulationConfig) -> float:
        """估算仿真时间（秒）。"""
        # 基于经验公式估算
        frames_per_snr = config.frame_count
        snr_points = len(config.snr_range)
        
        # 假设每帧平均处理时间（毫秒）
        time_per_frame_ms = 0.1 + (self.n * config.max_iterations * 0.001)
        
        total_time_seconds = (frames_per_snr * snr_points * time_per_frame_ms) / 1000
        
        return total_time_seconds

    def run_quick_test(self, snr_db: float, frames: int = 100) -> Dict[str, Any]:
        """快速测试单个 SNR 点。"""
        config = SimulationConfig(
            snr_range=[snr_db],
            frame_count=frames,
            max_errors=frames,  # 不提前停止
            min_frames=frames
        )
        
        results = self.run_ber_simulation(config)
        
        if len(results.ber) > 0:
            return {
                'snr_db': snr_db,
                'ber': results.ber[0],
                'fer': results.fer[0],
                'frames': results.total_frames[0],
                'avg_iterations': results.avg_iterations[0],
                'simulation_time': results.simulation_time
            }
        else:
            return {
                'snr_db': snr_db,
                'ber': 0,
                'fer': 0,
                'frames': 0,
                'avg_iterations': 0,
                'simulation_time': results.simulation_time
            }

    def run_simulation(self, config: SimulationConfig) -> Dict[str, Any]:
        """运行仿真并返回字典格式结果（用于API）。"""
        results = self.run_ber_simulation(config)
        
        return {
            'snr_db': results.snr_db,
            'ber': results.ber,
            'fer': results.fer,
            'frames_simulated': results.total_frames,
            'error_frames': results.error_frames,
            'iterations': results.avg_iterations,
            'simulation_time': results.simulation_time,
            'config': {
                'snr_range': config.snr_range,
                'frame_count': config.frame_count,
                'algorithm': config.decoder_algorithm,
                'channel_type': config.channel_type,
                'max_iterations': config.max_iterations
            }
        }


# 辅助函数
def create_snr_range(start: float, stop: float, step: float) -> List[float]:
    """创建 SNR 范围。"""
    return list(np.arange(start, stop + step/2, step))


def format_simulation_summary(results: SimulationResults) -> str:
    """格式化仿真结果摘要。"""
    summary = f"LDPC 仿真结果摘要\n"
    summary += f"={'='*50}\n"
    summary += f"码参数: n={results.config.snr_range}, k={len(results.snr_db)}\n"
    summary += f"仿真帧数: {results.config.frame_count}\n"
    summary += f"信道类型: {results.config.channel_type}\n"
    summary += f"解码算法: {results.config.decoder_algorithm}\n"
    summary += f"仿真时间: {results.simulation_time:.2f} 秒\n\n"
    
    summary += f"{'SNR(dB)':<8} {'BER':<12} {'FER':<12} {'帧数':<8} {'迭代':<8}\n"
    summary += f"{'-'*50}\n"
    
    for i in range(len(results.snr_db)):
        summary += f"{results.snr_db[i]:<8.1f} "
        summary += f"{results.ber[i]:<12.2e} "
        summary += f"{results.fer[i]:<12.2e} "
        summary += f"{results.total_frames[i]:<8d} "
        summary += f"{results.avg_iterations[i]:<8.1f}\n"
    
    return summary
