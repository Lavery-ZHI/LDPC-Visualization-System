#!/usr/bin/env python3
"""
LDPC仿真引擎API测试脚本
"""

import requests
import json
import numpy as np

def test_quick_test_api():
    """测试快速仿真API"""
    print("=" * 50)
    print("测试快速仿真API")
    print("=" * 50)
    
    # 使用测试矩阵
    H = [
        [1, 1, 0, 1, 1, 0, 0],
        [1, 0, 1, 1, 0, 1, 0],  
        [0, 1, 1, 1, 0, 0, 1]
    ]
    
    try:
        # 直接调用仿真引擎
        from algorithms.simulation_engine import SimulationEngine
        
        engine = SimulationEngine(np.array(H))
        result = engine.run_quick_test(snr_db=2.0, frames=50)
        
        print("✓ 快速测试成功!")
        print(f"  SNR: {result['snr_db']} dB")
        print(f"  BER: {result['ber']:.2e}")
        print(f"  FER: {result['fer']:.2e}")
        print(f"  仿真时间: {result['simulation_time']:.3f} 秒")
        print(f"  平均迭代: {result['avg_iterations']:.1f}")
        
        return True
        
    except Exception as e:
        print(f"✗ 快速测试失败: {e}")
        return False

def test_full_simulation():
    """测试完整仿真功能"""
    print("\n" + "=" * 50)
    print("测试完整仿真功能")
    print("=" * 50)
    
    # 使用测试矩阵
    H = [
        [1, 1, 0, 1, 1, 0, 0],
        [1, 0, 1, 1, 0, 1, 0],  
        [0, 1, 1, 1, 0, 0, 1]
    ]
    
    try:
        from algorithms.simulation_engine import SimulationEngine, SimulationConfig
        
        engine = SimulationEngine(np.array(H))
        
        # 配置仿真参数
        config = SimulationConfig(
            snr_range=[0.0, 1.0, 2.0],
            frame_count=100,
            channel_type="awgn",
            max_iterations=50,
            decoder_algorithm="min_sum"
        )
        
        def progress_callback(progress_info):
            frame = progress_info['frames_completed']
            snr = progress_info['snr_db']
            ber = progress_info['current_ber']
            if frame % 25 == 0:
                print(f"  进度: SNR {snr} dB, 帧 {frame}/100, BER: {ber:.2e}")
        
        # 运行仿真
        results = engine.run_ber_simulation(config, progress_callback)
        
        print(f"✓ 完整仿真成功! 总耗时: {results.simulation_time:.2f} 秒")
        print("\n结果摘要:")
        print("SNR(dB)  BER          FER")
        print("-" * 30)
        for i, snr in enumerate(results.snr_db):
            print(f"{snr:4.1f}     {results.ber[i]:.2e}     {results.fer[i]:.2e}")
        
        return True
        
    except Exception as e:
        print(f"✗ 完整仿真失败: {e}")
        return False

def test_bsc_simulation():
    """测试BSC信道仿真"""
    print("\n" + "=" * 50)
    print("测试BSC信道仿真")
    print("=" * 50)
    
    H = [
        [1, 1, 0, 1, 1, 0, 0],
        [1, 0, 1, 1, 0, 1, 0],  
        [0, 1, 1, 1, 0, 0, 1]
    ]
    
    try:
        from algorithms.simulation_engine import SimulationEngine, SimulationConfig
        
        engine = SimulationEngine(np.array(H))
        
        # BSC信道配置
        config = SimulationConfig(
            snr_range=[5.0, 10.0],  # BSC中SNR对应不同的错误概率
            frame_count=50,
            channel_type="bsc",
            max_iterations=20,
            decoder_algorithm="min_sum"
        )
        
        def progress_callback(progress_info):
            snr = progress_info['snr_db']
            ber = progress_info['current_ber']
            print(f"  BSC 进度: SNR {snr} dB, BER: {ber:.2e}")
        
        results = engine.run_ber_simulation(config, progress_callback)
        
        print("✓ BSC仿真完成!")
        for i, snr in enumerate(results.snr_db):
            print(f"SNR {snr} dB: BER={results.ber[i]:.2e}, FER={results.fer[i]:.2e}")
        
        return True
        
    except Exception as e:
        print(f"✗ BSC仿真失败: {e}")
        return False

if __name__ == "__main__":
    print("LDPC仿真引擎API测试")
    print("=" * 50)
    
    success_count = 0
    total_tests = 3
    
    # 运行所有测试
    if test_quick_test_api():
        success_count += 1
    
    if test_full_simulation():
        success_count += 1
        
    if test_bsc_simulation():
        success_count += 1
    
    # 总结
    print("\n" + "=" * 50)
    print(f"测试结果: {success_count}/{total_tests} 通过")
    if success_count == total_tests:
        print("✓ 所有测试通过!")
        print("仿真引擎已准备好集成到前端!")
    else:
        print("✗ 部分测试失败")
    print("=" * 50)
