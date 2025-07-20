"""
Simple test script to check if the fixes work
"""

import requests
import json

def test_template_generation():
    """Test a single template generation to see if the fix works"""
    try:
        # Test getting templates first
        response = requests.get("http://127.0.0.1:8000/api/matrix-templates")
        if response.status_code == 200:
            print("✅ Matrix templates endpoint working")
            
            # Test generating a simple template
            response = requests.post("http://127.0.0.1:8000/api/generate-template?template_name=simple_6_3")
            if response.status_code == 200:
                data = response.json()
                print("✅ Template generation working!")
                print(f"Template data: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"❌ Template generation failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        else:
            print(f"❌ Templates endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    print("Testing fixed template generation...")
    if test_template_generation():
        print("🎉 All fixes working correctly!")
    else:
        print("⚠️  Still have issues to fix.")
