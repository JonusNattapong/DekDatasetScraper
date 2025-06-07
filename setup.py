#!/usr/bin/env python3
"""
สคริปต์ติดตั้งสำหรับ Crawl4AI Dataset Scraper
รันไฟล์นี้เพื่อติดตั้งและตั้งค่าระบบอัตโนมัติ
"""

import subprocess
import sys
import os
import platform

def run_command(command, description):
    """รันคำสั่งและแสดงผลลัพธ์"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description} สำเร็จ")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} ล้มเหลว")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """ตรวจสอบเวอร์ชัน Python"""
    print("🐍 ตรวจสอบเวอร์ชัน Python...")
    
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - รองรับ")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - ต้องการ Python 3.8+")
        return False

def install_requirements():
    """ติดตั้ง Python packages"""
    print("\n📦 ติดตั้ง Python packages...")
    
    # อัปเดต pip ก่อน
    if run_command(f"{sys.executable} -m pip install --upgrade pip", "อัปเดต pip"):
        
        # ติดตั้ง requirements
        if os.path.exists("requirements.txt"):
            return run_command(f"{sys.executable} -m pip install -r requirements.txt", 
                             "ติดตั้ง packages จาก requirements.txt")
        else:
            # ติดตั้งแบบ manual
            packages = [
                "crawl4ai>=0.6.0",
                "pandas>=1.5.0", 
                "aiofiles>=0.8.0",
                "requests>=2.28.0",
                "beautifulsoup4>=4.11.0",
                "lxml>=4.9.0"
            ]
            
            success = True
            for package in packages:
                if not run_command(f"{sys.executable} -m pip install {package}", 
                                 f"ติดตั้ง {package}"):
                    success = False
            return success
    
    return False

def setup_crawl4ai():
    """ตั้งค่า Crawl4AI และ browser"""
    print("\n🌐 ตั้งค่า Crawl4AI...")
    
    # รัน crawl4ai-setup
    if run_command("crawl4ai-setup", "ตั้งค่า Crawl4AI"):
        
        # ติดตั้ง browser เพิ่มเติม (สำหรับกรณีที่ setup ไม่สำเร็จ)
        run_command("python -m playwright install chromium", 
                   "ติดตั้ง Chromium browser")
        
        # ทดสอบ Crawl4AI
        test_script = '''
try:
    import crawl4ai
    print(f"Crawl4AI version: {crawl4ai.__version__}")
    print("✅ Crawl4AI พร้อมใช้งาน")
except ImportError as e:
    print(f"❌ ไม่สามารถ import Crawl4AI: {e}")
    exit(1)
'''
        
        with open("test_crawl4ai.py", "w", encoding="utf-8") as f:
            f.write(test_script)
        
        success = run_command(f"{sys.executable} test_crawl4ai.py", 
                            "ทดสอบ Crawl4AI")
        
        # ลบไฟล์ทดสอบ
        if os.path.exists("test_crawl4ai.py"):
            os.remove("test_crawl4ai.py")
            
        return success
    
    return False

def create_project_structure():
    """สร้างโครงสร้างโปรเจกต์"""
    print("\n📁 สร้างโครงสร้างโปรเจกต์...")
    
    directories = [
        "output",
        "logs", 
        "cache",
        "examples"
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ สร้างโฟลเดอร์ {directory}")
        except Exception as e:
            print(f"❌ ไม่สามารถสร้างโฟลเดอร์ {directory}: {e}")

def run_basic_test():
    """รันการทดสอบพื้นฐาน"""
    print("\n🧪 รันการทดสอบพื้นฐาน...")
    
    if os.path.exists("example_usage.py"):
        return run_command(f"{sys.executable} example_usage.py test", 
                         "ทดสอบระบบ")
    else:
        print("⚠️ ไม่พบไฟล์ example_usage.py - ข้ามการทดสอบ")
        return True

def show_system_info():
    """แสดงข้อมูลระบบ"""
    print("💻 ข้อมูลระบบ:")
    print(f"   OS: {platform.system()} {platform.release()}")
    print(f"   Python: {sys.version}")
    print(f"   Current directory: {os.getcwd()}")

def main():
    """ฟังก์ชันหลัก"""
    print("🚀 === Crawl4AI Dataset Scraper Setup ===\n")
    
    show_system_info()
    print()
    
    # ตรวจสอบ Python version
    if not check_python_version():
        print("\n❌ การติดตั้งล้มเหลว: Python version ไม่รองรับ")
        sys.exit(1)
    
    # ติดตั้ง packages
    if not install_requirements():
        print("\n❌ การติดตั้ง Python packages ล้มเหลว")
        print("💡 ลองรันคำสั่งนี้ด้วยตนเอง:")
        print("   pip install crawl4ai pandas aiofiles requests beautifulsoup4 lxml")
        sys.exit(1)
    
    # ตั้งค่า Crawl4AI
    if not setup_crawl4ai():
        print("\n⚠️ การตั้งค่า Crawl4AI ไม่สำเร็จทั้งหมด")
        print("💡 ลองรันคำสั่งนี้ด้วยตนเอง:")
        print("   crawl4ai-setup")
        print("   python -m playwright install chromium")
    
    # สร้างโครงสร้างโปรเจกต์
    create_project_structure()
    
    # รันการทดสอบ (อันนี้อาจจะข้ามได้ถ้าไม่สำเร็จ)
    # run_basic_test()
    
    print("\n" + "="*60)
    print("🎉 การติดตั้งเสร็จสิ้น!")
    print("\n📋 คำสั่งที่สามารถใช้งาน:")
    print("   python main.py              - รันโปรแกรมหลัก")
    print("   python example_usage.py     - รันตัวอย่างการใช้งาน")
    print("   python example_usage.py test - รันการทดสอบ")
    
    print("\n📁 โครงสร้างโปรเจกต์:")
    print("   main.py                     - โปรแกรมหลัก")
    print("   example_usage.py            - ตัวอย่างการใช้งาน")
    print("   requirements.txt            - Python dependencies")
    print("   README.md                   - คู่มือการใช้งาน")
    print("   output/                     - โฟลเดอร์สำหรับไฟล์ผลลัพธ์")
    print("   logs/                       - โฟลเดอร์สำหรับ log files")
    print("   cache/                      - โฟลเดอร์สำหรับ cache")
    
    print("\n💡 เคล็ดลับ:")
    print("   - เริ่มต้นด้วยการรัน: python example_usage.py")
    print("   - อ่านคู่มือใน README.md สำหรับรายละเอียด")
    print("   - ตรวจสอบไฟล์ใน output/ หลังจากรันโปรแกรม")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ การติดตั้งถูกยกเลิกโดยผู้ใช้")
    except Exception as e:
        print(f"\n\n❌ เกิดข้อผิดพลาดในการติดตั้ง: {e}")
        print("💡 กรุณาติดตั้งด้วยตนเองตามคู่มือใน README.md")
