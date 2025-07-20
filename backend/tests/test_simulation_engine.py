"""测试仿真引擎功能。"""
import numpy as np
import sys
import os

# 添加路径以导入模块
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from algorithms.simulation_engine import SimulationEngine, SimulationConfig, create_snr_range


def test_simulation_engine():
    """测试仿真引擎基本功能。"""
    print("测试 LDPC 仿真引擎...")
    
    # 创建一个简单的 LDPC 校验矩阵 (7,4) 汉明码
    H = np.array([
        [1, 1, 0, 1, 1, 0, 0],
        [1, 0, 1, 1, 0, 1, 0],
        [0, 1, 1, 1, 0, 0, 1]
    ], dtype=int)
    
    print(f"使用校验矩阵 H (形状: {H.shape})")
    
    # 初始化仿真引擎
    try:
        engine = SimulationEngine(H)
        print(f"✓ 仿真引擎初始化成功")
        
        # 获取码信息
        code_info = engine.get_code_info()
        print(f"✓ 码参数: n={code_info['n']}, k={code_info['k']}, rate={code_info['rate']:.3f}")
        
    except Exception as e:
        print(f"✗ 仿真引擎初始化失败: {e}")
        return False
    
    # 快速测试
    print("\n执行快速测试...")
    try:
        test_result = engine.run_quick_test(snr_db=2.0, frames=50)
        print(f"✓ 快速测试完成:")
        print(f"  SNR: {test_result['snr_db']} dB")
        print(f"  BER: {test_result['ber']:.2e}")
        print(f"  FER: {test_result['fer']:.2e}")
        print(f"  仿真时间: {test_result['simulation_time']:.3f} 秒")
        print(f"  平均迭代: {test_result['avg_iterations']:.1f}")
        
    except Exception as e:
        print(f"✗ 快速测试失败: {e}")
        return False
    
    # 完整仿真测试
    print("\n执行完整仿真测试...")
    
    # 创建仿真配置
    config = SimulationConfig(
        snr_range=create_snr_range(0.0, 4.0, 1.0),  # 0, 1, 2, 3, 4 dB
        frame_count=100,
        max_errors=50,
        min_frames=50,
        channel_type="awgn",
        decoder_algorithm="min_sum",
        progress_interval=25
    )
    
    print(f"SNR 范围: {config.snr_range} dB")
    print(f"每点帧数: {config.frame_count}")
    
    # 进度回调函数
    def progress_callback(info):
        print(f"  进度: SNR {info['snr_db']:.1f} dB, "
              f"帧 {info['frames_completed']}/{info['total_frames_target']}, "
              f"当前 BER: {info['current_ber']:.2e}")
    
    try:
        # 估算仿真时间
        estimated_time = engine.estimate_simulation_time(config)
        print(f"估算仿真时间: {estimated_time:.1f} 秒")
        
        # 运行仿真
        results = engine.run_ber_simulation(config, progress_callback)
        
        print(f"✓ 仿真完成! 总耗时: {results.simulation_time:.2f} 秒")
        print(f"\n结果摘要:")
        print(f"{'SNR(dB)':<8} {'BER':<12} {'FER':<12} {'帧数':<8}")
        print("-" * 40)
        
        for i in range(len(results.snr_db)):
            print(f"{results.snr_db[i]:<8.1f} "
                  f"{results.ber[i]:<12.2e} "
                  f"{results.fer[i]:<12.2e} "
                  f"{results.total_frames[i]:<8d}")
        
        return True
        
    except Exception as e:
        print(f"✗ 仿真失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bsc_channel():
    """测试 BSC 信道。"""
    print("\n\n测试 BSC 信道...")
    
    # 创建校验矩阵
    H = np.array([
        [1, 1, 0, 1, 1, 0, 0],
        [1, 0, 1, 1, 0, 1, 0],
        [0, 1, 1, 1, 0, 0, 1]
    ], dtype=int)
    
    engine = SimulationEngine(H)
    
    # BSC 仿真配置
    config = SimulationConfig(
        snr_range=[5.0, 10.0],  # 对于 BSC，这里 SNR 用于计算交叉概率
        frame_count=100,
        channel_type="bsc",
        decoder_algorithm="sum_product",  # 测试 Sum-Product 算法
        progress_interval=50
    )
    
    def progress_callback(info):
        print(f"  BSC 进度: SNR {info['snr_db']:.1f} dB, "
              f"BER: {info['current_ber']:.2e}")
    
    try:
        results = engine.run_ber_simulation(config, progress_callback)
        print(f"✓ BSC 仿真完成!")
        
        for i in range(len(results.snr_db)):
            print(f"SNR {results.snr_db[i]:.1f} dB: "
                  f"BER={results.ber[i]:.2e}, "
                  f"FER={results.fer[i]:.2e}")
        
        return True
        
    except Exception as e:
        print(f"✗ BSC 仿真失败: {e}")
        return False


if __name__ == "__main__":
    print("LDPC 仿真引擎测试")
    print("=" * 50)
    
    # 测试基本功能
    success1 = test_simulation_engine()
    
    # 测试 BSC 信道
    success2 = test_bsc_channel()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("✓ 所有测试通过!")
    else:
        print("✗ 部分测试失败!")
