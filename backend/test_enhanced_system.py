"""
Enhanced test script for improved LDPC system functionality
Tests matrix templates, error handling, and performance optimizations
"""

import requests
import json
import numpy as np
import time
from typing import Dict, Any

class LDPCSystemTester:
    """Comprehensive tester for enhanced LDPC system"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000/api"):
        self.base_url = base_url
        self.test_results = []
        
    def test_matrix_templates(self) -> Dict[str, Any]:
        """Test matrix template functionality"""
        print("\n=== Testing Matrix Templates ===")
        
        try:
            # Test getting available templates
            response = requests.get(f"{self.base_url}/matrix-templates")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Successfully retrieved {len(data.get('templates', {}))} templates")
                
                # Test generating each template
                for template_name in data.get('templates', {}):
                    print(f"Testing template: {template_name}")
                    
                    template_response = requests.post(
                        f"{self.base_url}/generate-template",
                        params={"template_name": template_name}
                    )
                    
                    if template_response.status_code == 200:
                        template_data = template_response.json()
                        if template_data.get('success'):
                            validation = template_data.get('validation', {})
                            print(f"  ✅ {template_name}: ({validation.get('n')}x{validation.get('m')}) "
                                  f"Rate: {validation.get('rate', 0):.3f}")
                        else:
                            print(f"  ❌ {template_name}: Generation failed")
                    else:
                        print(f"  ❌ {template_name}: HTTP {template_response.status_code}")
                        
                return {"status": "success", "templates_tested": len(data.get('templates', {}))}
            else:
                return {"status": "failed", "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def test_enhanced_quick_test(self) -> Dict[str, Any]:
        """Test enhanced quick test with error handling"""
        print("\n=== Testing Enhanced Quick Test ===")
        
        try:
            # Test with valid parameters
            valid_request = {
                "h_matrix": [
                    [1, 1, 1, 0, 0, 0],
                    [0, 1, 1, 1, 0, 0],
                    [0, 0, 1, 1, 1, 1]
                ],
                "snr_db": 2.0,
                "frames": 10,
                "algorithm": "min_sum",
                "channel": "awgn"
            }
            
            response = requests.post(f"{self.base_url}/quick-test", json=valid_request)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    results = data.get('results', {})
                    print(f"✅ Valid test passed - BER: {results.get('ber', 0):.6f}")
                    
                    # Test error handling with invalid inputs
                    error_tests = [
                        {
                            "name": "Invalid SNR",
                            "request": {**valid_request, "snr_db": 100},  # Invalid SNR
                            "expected_error": "SNR must be between"
                        },
                        {
                            "name": "Invalid Algorithm", 
                            "request": {**valid_request, "algorithm": "invalid_algo"},
                            "expected_error": "Algorithm must be"
                        },
                        {
                            "name": "Missing H Matrix",
                            "request": {k: v for k, v in valid_request.items() if k != "h_matrix"},
                            "expected_error": "H matrix is required"
                        }
                    ]
                    
                    error_results = []
                    for test in error_tests:
                        error_response = requests.post(f"{self.base_url}/quick-test", json=test["request"])
                        error_data = error_response.json()
                        
                        if not error_data.get('success', True):
                            error_msg = error_data.get('error', {}).get('message', '')
                            if test["expected_error"] in error_msg:
                                print(f"  ✅ {test['name']}: Error correctly caught")
                                error_results.append(True)
                            else:
                                print(f"  ❌ {test['name']}: Unexpected error message")
                                error_results.append(False)
                        else:
                            print(f"  ❌ {test['name']}: Should have failed but didn't")
                            error_results.append(False)
                    
                    return {
                        "status": "success",
                        "valid_test_passed": True,
                        "error_handling_tests": len([r for r in error_results if r]),
                        "total_error_tests": len(error_results)
                    }
                else:
                    return {"status": "failed", "error": "Test returned success=false"}
            else:
                return {"status": "failed", "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def test_performance_monitoring(self) -> Dict[str, Any]:
        """Test performance monitoring capabilities"""
        print("\n=== Testing Performance Monitoring ===")
        
        try:
            # Run a few operations to generate performance data
            for i in range(3):
                requests.post(f"{self.base_url}/quick-test", json={
                    "h_matrix": [[1, 1, 1, 0, 0, 0], [0, 1, 1, 1, 0, 0], [0, 0, 1, 1, 1, 1]],
                    "snr_db": 1.0 + i,
                    "frames": 5
                })
                time.sleep(0.1)
            
            # Get performance metrics
            response = requests.get(f"{self.base_url}/performance-metrics")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    metrics = data.get('metrics', {})
                    print(f"✅ Performance metrics retrieved:")
                    print(f"  Total runs: {metrics.get('total_runs', 0)}")
                    print(f"  Average time: {metrics.get('average_time', 0):.3f}s")
                    print(f"  Total errors: {metrics.get('total_errors', 0)}")
                    
                    return {"status": "success", "metrics_available": True}
                else:
                    return {"status": "failed", "error": "No metrics data"}
            else:
                return {"status": "failed", "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def test_template_integration(self) -> Dict[str, Any]:
        """Test integration between templates and code generation"""
        print("\n=== Testing Template Integration ===")
        
        try:
            # Test generating code with different templates
            templates_to_test = ["simple_6_3", "hamming_7_4", "regular_12_6"]
            results = []
            
            for template in templates_to_test:
                response = requests.post(
                    f"{self.base_url}/generate-from-graph",
                    params={"template_name": template}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        params = data.get('parameters', {})
                        print(f"✅ {template}: Generated ({params.get('code_length')},{params.get('info_length')}) code")
                        results.append(True)
                    else:
                        print(f"❌ {template}: Generation failed")
                        results.append(False)
                else:
                    print(f"❌ {template}: HTTP {response.status_code}")
                    results.append(False)
            
            return {
                "status": "success" if all(results) else "partial",
                "successful_templates": sum(results),
                "total_templates": len(templates_to_test)
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and generate comprehensive report"""
        print("🚀 Starting Comprehensive LDPC System Test")
        print("=" * 50)
        
        test_suite = [
            ("Matrix Templates", self.test_matrix_templates),
            ("Enhanced Quick Test", self.test_enhanced_quick_test),
            ("Performance Monitoring", self.test_performance_monitoring),
            ("Template Integration", self.test_template_integration)
        ]
        
        results = {}
        passed_tests = 0
        
        for test_name, test_func in test_suite:
            try:
                result = test_func()
                results[test_name] = result
                
                if result.get('status') == 'success':
                    passed_tests += 1
                    print(f"✅ {test_name}: PASSED")
                elif result.get('status') == 'partial':
                    print(f"🔶 {test_name}: PARTIAL")
                else:
                    print(f"❌ {test_name}: FAILED - {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                results[test_name] = {"status": "error", "error": str(e)}
                print(f"❌ {test_name}: ERROR - {str(e)}")
        
        print("\n" + "=" * 50)
        print(f"📊 Test Summary: {passed_tests}/{len(test_suite)} tests passed")
        
        if passed_tests == len(test_suite):
            print("🎉 All tests passed! System is ready for use.")
        elif passed_tests >= len(test_suite) * 0.75:
            print("✅ Most tests passed. System is functional with minor issues.")
        else:
            print("⚠️  Multiple test failures. Please check system configuration.")
        
        return {
            "summary": {
                "total_tests": len(test_suite),
                "passed_tests": passed_tests,
                "pass_rate": passed_tests / len(test_suite)
            },
            "detailed_results": results
        }

if __name__ == "__main__":
    tester = LDPCSystemTester()
    results = tester.run_comprehensive_test()
    
    # Save results to file
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📝 Detailed test results saved to test_results.json")
