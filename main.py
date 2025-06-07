import asyncio
import json
import csv
import pandas as pd
from urllib.parse import urljoin, urlparse
import logging
from typing import List, Dict
import aiofiles
import time
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
import re

# ตั้งค่า logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_user_pdf_limit():
    """รับจำนวนไฟล์ PDF ที่ต้องการประมวลผลจากผู้ใช้"""
    try:
        limit = int(input("\nจำนวนไฟล์ PDF ที่ต้องการประมวลผล (0=ทั้งหมด): ").strip() or "0")
        return max(0, limit)
    except ValueError:
        print("⚠️ โปรดป้อนตัวเลขเท่านั้น")
        return 0

def get_user_pdf_limit():
    """รับจำนวนไฟล์ PDF ที่ต้องการประมวลผลจากผู้ใช้"""
    try:
        limit = int(input("จำนวนไฟล์ PDF ที่ต้องการประมวลผล (0=ทั้งหมด): ").strip() or "0")
        return max(0, limit)
    except Exception:
        print("⚠️ โปรดป้อนตัวเลขเท่านั้น")
        return 0

def get_user_input():
    """รับข้อมูลจากผู้ใช้"""
    print("\n===== ตั้งค่าการประมวลผล =====")
    try:
        limit = int(input("จำนวนไฟล์ที่ต้องการประมวลผล (0=ทั้งหมด): ").strip() or "0")
        return max(0, limit)
    except ValueError:
        print("⚠️ โปรดป้อนตัวเลขเท่านั้น")
        return 0

class Crawl4AiDatasetScraper:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or "https://ratchakitcha.soc.go.th"
        self.session_data = []
        self.dataset = []
        
        # Browser config for Crawl4AI
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=True,
            browser_type="chromium"
        )
        
        # Crawler config
        self.run_config = CrawlerRunConfig(
            cache_mode=CacheMode.ENABLED,
            word_count_threshold=10,
            wait_for_images=True,
            delay_before_return_html=2.0,
            timeout=30
        )

    async def extract_links_from_page(self, url: str, link_patterns: List[str] = None) -> List[Dict]:
        """
        ดึงลิ้งค์และหัวข้อจากหน้าเว็บโดยใช้ Crawl4AI
        """
        links_data = []
        
        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                logger.info(f"🔍 กำลังดึงลิ้งค์จาก: {url}")
                
                result = await crawler.arun(url=url, config=self.run_config)
                
                if result.success:
                    # ใช้ regex หาลิ้งค์และหัวข้อ
                    if not link_patterns:
                        link_patterns = [
                            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',
                            r'href=["\']([^"\']+)["\'][^>]*[^>]*>([^<]{10,})</a>'
                        ]
                    
                    # หาลิ้งค์จาก HTML
                    for pattern in link_patterns:
                        matches = re.findall(pattern, result.html, re.IGNORECASE | re.DOTALL)
                        for match in matches:
                            if len(match) >= 2:
                                link_url = match[0].strip()
                                title = re.sub(r'<[^>]+>', '', match[1]).strip()
                                
                                # ตรวจสอบว่าเป็นลิ้งค์ที่ต้องการหรือไม่
                                if self._is_valid_link(link_url, title):
                                    full_url = urljoin(self.base_url, link_url)
                                    links_data.append({
                                        'url': full_url,
                                        'title': title
                                    })
                    
                    # หาลิ้งค์จาก links ที่ Crawl4AI extract ไว้แล้ว
                    if hasattr(result, 'links') and result.links:
                        internal_links = result.links.get('internal', [])
                        for link_info in internal_links:
                            if isinstance(link_info, dict):
                                link_url = link_info.get('href', '')
                                title = link_info.get('text', '').strip()
                            else:
                                continue
                            
                            if self._is_valid_link(link_url, title):
                                full_url = urljoin(self.base_url, link_url)
                                links_data.append({
                                    'url': full_url,
                                    'title': title
                                })
                    
                    logger.info(f"✅ พบลิ้งค์ {len(links_data)} รายการ")
                else:
                    logger.error(f"❌ ไม่สามารถดึงข้อมูลจาก {url}: {result.error_message}")
                    
        except Exception as e:
            logger.error(f"❌ Error ในการดึงลิ้งค์: {str(e)}")
            
        return self._remove_duplicates(links_data)

    def _is_valid_link(self, url: str, title: str) -> bool:
        """ตรวจสอบว่าลิ้งค์และหัวข้อถูกต้องหรือไม่"""
        if not url or not title:
            return False
        
        # กรองลิ้งค์ที่ไม่ต้องการ
        invalid_patterns = [
            r'^#', r'^javascript:', r'^mailto:', r'^tel:',
            r'\.(css|js|jpg|jpeg|png|gif|pdf|doc|docx)(\?|$)',
            r'/(login|logout|register|admin)/',
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # กรองหัวข้อที่สั้นเกินไป
        if len(title.strip()) < 5:
            return False
            
        return True

    def _remove_duplicates(self, links_data: List[Dict]) -> List[Dict]:
        """ลบลิ้งค์ซ้ำ"""
        seen = set()
        unique_links = []
        
        for link in links_data:
            identifier = (link['url'], link['title'])
            if identifier not in seen:
                seen.add(identifier)
                unique_links.append(link)
                
        return unique_links

    async def scrape_content_from_url(self, url: str, title: str = "") -> Dict:
        """
        ดึงเนื้อหาจาก URL และส่งคืนในรูปแบบ Dataset
        """
        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                logger.info(f"📄 กำลังดึงเนื้อหาจาก: {url}")
                
                result = await crawler.arun(url=url, config=self.run_config)
                
                if result.success:
                    # ใช้ markdown เป็นข้อความหลัก
                    text_content = result.markdown or result.cleaned_html or ""
                    
                    # หาหัวข้อหากไม่ได้ระบุมา
                    if not title and hasattr(result, 'metadata'):
                        title = result.metadata.get('title', '') or self._extract_title_from_content(text_content)
                    
                    return {
                        'url': url,
                        'title': title.strip(),
                        'text': text_content.strip()
                    }
                else:
                    logger.error(f"❌ ไม่สามารถดึงเนื้อหาจาก {url}: {result.error_message}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error ในการดึงเนื้อหา {url}: {str(e)}")
            return None

    def _extract_title_from_content(self, content: str) -> str:
        """แยกหัวข้อจากเนื้อหา"""
        lines = content.split('\n')
        for line in lines[:10]:  # ดูแค่ 10 บรรทัดแรก
            line = line.strip()
            if len(line) > 10 and len(line) < 200:
                return line
        return "ไม่ระบุหัวข้อ"

    async def create_dataset_from_links(self, links_data: List[Dict], max_pages: int = 50) -> List[Dict]:
        """
        สร้าง Dataset จากรายการลิ้งค์
        """
        dataset = []
        processed = 0
        
        for i, link_info in enumerate(links_data[:max_pages], 1):
            try:
                content_data = await self.scrape_content_from_url(
                    link_info['url'], 
                    link_info['title']
                )
                
                if content_data and content_data['text']:
                    dataset.append({
                        'id': i,
                        'url': content_data['url'],
                        'title': content_data['title'],
                        'text': content_data['text']
                    })
                    processed += 1
                    logger.info(f"✅ ประมวลผลแล้ว {processed}/{len(links_data[:max_pages])} หน้า")
                
                # หยุดพักเล็กน้อยเพื่อไม่ให้โหลดเซิร์ฟเวอร์หนัก
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Error ในการประมวลผล {link_info['url']}: {str(e)}")
                continue
        
        logger.info(f"🎉 สร้าง Dataset เสร็จสิ้น: {len(dataset)} รายการ")
        return dataset

    async def save_dataset_to_csv(self, dataset: List[Dict], filename: str = "dataset.csv"):
        """บันทึก Dataset เป็น CSV"""
        try:
            if not dataset:
                logger.warning("⚠️ ไม่มีข้อมูลให้บันทึก")
                return
            
            df = pd.DataFrame(dataset)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"💾 บันทึก Dataset ลง {filename} เรียบร้อยแล้ว ({len(dataset)} รายการ)")
            
        except Exception as e:
            logger.error(f"❌ Error ในการบันทึก CSV: {str(e)}")

    async def save_dataset_to_json(self, dataset: List[Dict], filename: str = "dataset.json"):
        """บันทึก Dataset เป็น JSON"""
        try:
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(dataset, ensure_ascii=False, indent=2))
            logger.info(f"💾 บันทึก Dataset ลง {filename} เรียบร้อยแล้ว")
            
        except Exception as e:
            logger.error(f"❌ Error ในการบันทึก JSON: {str(e)}")

    async def auto_scrape_website(self, start_url: str, max_pages: int = 20,
                                 keywords: List[str] = None) -> List[Dict]:
        """
        สแกนเว็บไซต์อัตโนมัติและสร้าง Dataset
        """
        logger.info(f"🚀 เริ่มการสแกน {start_url} อัตโนมัติ")
        
        # รับจำนวนไฟล์ที่ต้องการประมวลผลจากผู้ใช้
        pdf_limit = get_user_pdf_limit()
        if pdf_limit > 0:
            logger.info(f"📌 จะประมวลผล {pdf_limit} ไฟล์แรก")
            max_pages = min(max_pages, pdf_limit)
        
        # 1. ดึงลิ้งค์จากหน้าหลัก
        links_data = await self.extract_links_from_page(start_url)
        
        # 2. กรองลิ้งค์ตาม keywords ถ้ามี
        if keywords:
            filtered_links = []
            for link in links_data:
                for keyword in keywords:
                    if keyword.lower() in link['title'].lower() or keyword.lower() in link['url'].lower():
                        filtered_links.append(link)
                        break
            links_data = filtered_links
            logger.info(f"🔍 กรองด้วย keywords เหลือ {len(links_data)} ลิ้งค์")
        
        # 3. สร้าง Dataset
        dataset = await self.create_dataset_from_links(links_data, max_pages)
        
        return dataset

async def main():
    """ฟังก์ชันหลักสำหรับทดสอบและใช้งาน"""
    print("🤖 === Crawl4AI Dataset Scraper ===\n")
    
    # ตัวอย่างการใช้งาน
    scraper = Crawl4AiDatasetScraper()
    
    # ตัวอย่าง URLs ที่สามารถทดสอบได้
    test_urls = [
        "https://ratchakitcha.soc.go.th",
        "https://news.thaigov.go.th", 
        "https://www.bangkokpost.com",
        "https://www.thairath.co.th",
    ]
    
    try:
        print("เลือกโหมดการทำงาน:")
        print("1. สแกนเว็บไซต์อัตโนมัติ")
        print("2. ดึงลิ้งค์จากหน้าเดียว")
        print("3. ดึงเนื้อหาจาก URL เดียว")
        
        choice = input("\nป้อนหมายเลข (1-3): ").strip()
        
        if choice == "1":
            # โหมดสแกนอัตโนมัติ
            url = input(f"ป้อน URL เริ่มต้น (หรือกด Enter ใช้ {test_urls[0]}): ").strip()
            if not url:
                url = test_urls[0]
            
            max_pages = input("จำนวนหน้าสูงสุด (ค่าเริ่มต้น 20): ").strip()
            max_pages = int(max_pages) if max_pages.isdigit() else 20
            
            keywords_input = input("คำค้นหา (คั่นด้วยเครื่องหมายจุลภาค, หรือเว้นว่าง): ").strip()
            keywords = [k.strip() for k in keywords_input.split(',') if k.strip()] if keywords_input else None
            
            dataset = await scraper.auto_scrape_website(url, max_pages, keywords)
            
            if dataset:
                await scraper.save_dataset_to_csv(dataset, "auto_scraped_dataset.csv")
                await scraper.save_dataset_to_json(dataset, "auto_scraped_dataset.json")
                
                print(f"\n📊 ตัวอย่างข้อมูลที่ได้:")
                for i, item in enumerate(dataset[:3], 1):
                    print(f"\n{i}. ID: {item['id']}")
                    print(f"   URL: {item['url']}")
                    print(f"   Title: {item['title'][:100]}...")
                    print(f"   Text: {item['text'][:200]}...")
        
        elif choice == "2":
            # โหมดดึงลิ้งค์
            url = input(f"ป้อน URL (หรือกด Enter ใช้ {test_urls[0]}): ").strip()
            if not url:
                url = test_urls[0]
            
            links = await scraper.extract_links_from_page(url)
            
            print(f"\n🔗 พบลิ้งค์ {len(links)} รายการ:")
            for i, link in enumerate(links[:10], 1):
                print(f"{i}. {link['title'][:80]}")
                print(f"   {link['url']}")
        
        elif choice == "3":
            # โหมดดึงเนื้อหาจาก URL เดียว
            url = input("ป้อน URL: ").strip()
            if not url:
                print("❌ กรุณาป้อน URL")
                return
            
            content = await scraper.scrape_content_from_url(url)
            if content:
                print(f"\n📄 เนื้อหาที่ได้:")
                print(f"Title: {content['title']}")
                print(f"URL: {content['url']}")
                print(f"Text: {content['text'][:500]}...")
                
                # บันทึกเป็น dataset
                dataset = [{
                    'id': 1,
                    'url': content['url'],
                    'title': content['title'],
                    'text': content['text']
                }]
                await scraper.save_dataset_to_csv(dataset, "single_page_dataset.csv")
        
        else:
            print("❌ ตัวเลือกไม่ถูกต้อง")
    
    except KeyboardInterrupt:
        print("\n⏹️ หยุดการทำงานโดยผู้ใช้")
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    # ตรวจสอบว่าติดตั้ง Crawl4AI แล้วหรือยัง
    try:
        import crawl4ai
        print(f"✅ Crawl4AI version: {crawl4ai.__version__}")
    except ImportError:
        print("❌ กรุณาติดตั้ง Crawl4AI ก่อน: pip install crawl4ai")
        print("❌ แล้วรัน: crawl4ai-setup")
        exit(1)
    
    # รันโปรแกรม
    asyncio.run(main())
