#!/usr/bin/env python3
"""
前后端对接测试脚本
测试Flutter前端和Python后端的API兼容性
"""
import requests
import json

def test_encode_api():
    """测试编码API"""
    print("🧪 测试前后端API对接...")
    
    # 后端API地址
    base_url = "http://127.0.0.1:5000"
    
    # 测试数据 - Flutter前端格式
    test_data = {
        "nodes": [
            {"id": "V0", "type": "variable"},
            {"id": "V1", "type": "variable"},
            {"id": "V2", "type": "variable"},
            {"id": "C0", "type": "check"}
        ],
        "edges": [
            {"fromId": "V0", "toId": "C0"},
            {"fromId": "V1", "toId": "C0"},
            {"fromId": "V2", "toId": "C0"}
        ]
    }
    
    try:
        # 1. 测试基本连接
        print("1. 测试服务器连接...")
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("   ✅ 服务器在线")
        else:
            print(f"   ❌ 服务器响应异常: {response.status_code}")
            return
        
        # 2. 测试编码API
        print("2. 测试编码API...")
        response = requests.post(
            f"{base_url}/api/v1/encode", 
            json=test_data, 
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("   ✅ 编码API响应成功")
            print(f"   📊 码率: {result.get('code_rate')}")
            print(f"   📏 码长n: {result.get('n')}")
            print(f"   📏 信息长k: {result.get('k')}")
            print(f"   📏 校验长m: {result.get('m')}")
            
            h_matrix = result.get('h_matrix')
            g_matrix = result.get('g_matrix')
            if h_matrix:
                print(f"   🔢 H矩阵: {len(h_matrix)}×{len(h_matrix[0])}")
            if g_matrix:
                print(f"   🔢 G矩阵: {len(g_matrix)}×{len(g_matrix[0])}")
        else:
            print(f"   ❌ 编码API失败: {response.status_code}")
            print(f"   📄 错误信息: {response.text}")
            return
        
        # 3. 测试带信息位的编码
        print("3. 测试信息位编码...")
        encode_data = {
            "h_matrix": [[1, 0, 1, 1], [0, 1, 1, 0]],
            "info_bits": [1, 0]
        }
        
        response = requests.post(
            f"{base_url}/api/v1/encode",
            json=encode_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("   ✅ 信息位编码成功")
            codeword = result.get('codeword')
            if codeword:
                print(f"   🔗 码字: {codeword}")
        else:
            print(f"   ❌ 信息位编码失败: {response.status_code}")
        
        print("\n🎉 前后端对接测试完成!")
        print("📱 Flutter前端现在可以正常连接后端API")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务器")
        print("💡 请确保后端正在运行: python main.py")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_encode_api() 