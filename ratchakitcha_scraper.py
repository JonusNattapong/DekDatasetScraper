#!/usr/bin/env python3
"""
Ratchakitcha.soc.go.th Dataset Scraper - CRAWL4AI FIXED VERSION
ดึงข้อมูลและลิ้งค์ PDF จากเว็บไซต์ราชกิจจานุเบกษา
ใช้ crawl4ai แต่แก้ไขปัญหา Windows + Anti-Block
"""

import asyncio
import json
import pandas as pd
from urllib.parse import urljoin, urlparse
import logging
import re
from typing import List, Dict, Optional, Set
import aiofiles
import aiohttp
import os
from datetime import datetime
import hashlib
import time
from pathlib import Path
import gc
from mistralai import Mistral
try:
    from openai import OpenAI  # DeepSeek ใช้ OpenAI format
    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False
import sys
import random
import platform

# PyThaiNLP for text correction - Optimized
try:
    # Import เฉพาะที่จำเป็น - แก้ไขปัญหา callable
    import pythainlp
    from pythainlp.correct import correct
    from pythainlp import word_tokenize
    PYTHAINLP_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ PyThaiNLP imported successfully (optimized)")
except ImportError as e:
    PYTHAINLP_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ PyThaiNLP not available: {e}")

# Cache สำหรับ PyThaiNLP เพื่อเร็วขึ้น
_pythainlp_cache = {}

# env
from dotenv import load_dotenv
load_dotenv()

# แก้ไขปัญหา Event Loop สำหรับ Windows Python 3.13
def fix_windows_event_loop():
    """แก้ไขปัญหา NotImplementedError ใน Windows"""
    if platform.system() == 'Windows':
        # สำหรับ Python 3.13 ใน Windows
        if sys.version_info >= (3, 8):
            try:
                # ลองใช้ ProactorEventLoopPolicy ก่อน (ดีสำหรับ subprocess)
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                logger.info("✅ ใช้ WindowsProactorEventLoopPolicy")
            except Exception as e:
                try:
                    # ถ้าไม่ได้ ใช้ SelectorEventLoopPolicy
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                    logger.info("✅ ใช้ WindowsSelectorEventLoopPolicy")
                except Exception as e2:
                    logger.warning(f"⚠️ ไม่สามารถตั้งค่า event loop policy: {e2}")

# ตั้งค่า logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# แก้ไข Windows event loop ทันที
fix_windows_event_loop()

# Import crawl4ai หลังจากแก้ไข event loop
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    CRAWL4AI_AVAILABLE = True
    logger.info("✅ crawl4ai imported successfully")
except ImportError as e:
    logger.error(f"❌ ไม่สามารถ import crawl4ai: {e}")
    logger.error("💡 ติดตั้งด้วย: pip install crawl4ai")
    CRAWL4AI_AVAILABLE = False
except Exception as e:
    logger.error(f"❌ crawl4ai error: {e}")
    CRAWL4AI_AVAILABLE = False

class CacheManager:
    """จัดการ Cache สำหรับ OCR Results"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_cache = {}
        
    def _get_cache_key(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()
    
    async def get(self, url: str) -> Optional[str]:
        cache_key = self._get_cache_key(url)
        
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        cache_file = self.cache_dir / f"{cache_key}.txt"
        if cache_file.exists():
            try:
                async with aiofiles.open(cache_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    self.memory_cache[cache_key] = content
                    return content
            except Exception as e:
                logger.warning(f"Error reading cache: {e}")
        
        return None
    
    async def set(self, url: str, content: str):
        cache_key = self._get_cache_key(url)
        self.memory_cache[cache_key] = content
        
        cache_file = self.cache_dir / f"{cache_key}.txt"
        try:
            async with aiofiles.open(cache_file, 'w', encoding='utf-8') as f:
                await f.write(content)
        except Exception as e:
            logger.warning(f"Error writing cache: {e}")

class ProgressTracker:
    """ติดตามความคืบหน้า"""
    
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.start_time = time.time()
        self.failed = 0
    
    def update(self, success: bool = True):
        self.completed += 1
        if not success:
            self.failed += 1
        
        if self.completed % 5 == 0 or self.completed == self.total:
            elapsed = time.time() - self.start_time
            rate = self.completed / elapsed if elapsed > 0 else 0
            eta = (self.total - self.completed) / rate if rate > 0 else 0
            
            logger.info(f"🚀 Progress: {self.completed}/{self.total} ({self.completed/self.total*100:.1f}%) "
                       f"Rate: {rate:.1f}/s ETA: {eta/60:.1f}m Failed: {self.failed}")

class MistralOCRWithDeepSeekCorrection:
    """คลาสใช้ Mistral OCR + DeepSeek แก้ไขคำผิด"""
    
    def __init__(self, use_deepseek_correction=False):
        self.use_deepseek_correction = use_deepseek_correction
        self.cache = CacheManager()
        self.embedding_cache = {}  # Cache สำหรับ embeddings
        
        # Mistral API สำหรับ OCR (บังคับ)
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if not mistral_key:
            raise ValueError("MISTRAL_API_KEY is required for OCR")
        
        self.mistral_client = Mistral(api_key=mistral_key)
        self.embedding_model = "mistral-embed"
        self.ocr_model = "mistral-ocr-latest"
        
        # DeepSeek API สำหรับแก้ไขคำผิด (ถ้ามี)
        self.deepseek_client = None
        if use_deepseek_correction and DEEPSEEK_AVAILABLE:
            deepseek_key = os.getenv("DEEPSEEK_API_KEY")
            if deepseek_key:
                self.deepseek_client = OpenAI(
                    api_key=deepseek_key,
                    base_url="https://api.deepseek.com/v1"
                )
                logger.info("✅ Mistral OCR + DeepSeek Text Correction พร้อมใช้งาน!")
            else:
                logger.warning("⚠️ DEEPSEEK_API_KEY ไม่พบ จะใช้ Pattern-based correction")
        else:
            logger.info("✅ Mistral OCR + Pattern-based correction พร้อมใช้งาน")
    
    async def extract_text_from_pdf_url_cached(self, pdf_url: str) -> str:
        cached_result = await self.cache.get(pdf_url)
        if cached_result:
            logger.debug(f"📚 Cache hit: {pdf_url}")
            return cached_result
        
        try:
            # ตรวจสอบว่า url ลงท้าย .pdf ก่อนเรียก OCR
            if not pdf_url.lower().endswith(".pdf"):
                logger.error(f"❌ Invalid PDF URL (not .pdf): {pdf_url}")
                return ""
            # ดาวน์โหลด PDF มาบนเครื่องก่อน แล้วอัพโหลดไปยัง API
            try:
                import tempfile
                import aiohttp
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmpfile:
                    tmp_path = tmpfile.name
                async with aiohttp.ClientSession() as session:
                    async with session.get(pdf_url) as resp:
                        if resp.status == 200:
                            with open(tmp_path, "wb") as f:
                                f.write(await resp.read())
                        else:
                            logger.error(f"❌ Download failed: {pdf_url} (HTTP {resp.status})")
                            return f"Download failed: HTTP {resp.status}"
                with open(tmp_path, "rb") as pdf_file:
                    uploaded_file = self.mistral_client.files.upload(
                        file={
                            "file_name": tmp_path.split("/")[-1],
                            "content": pdf_file,
                        },
                        purpose="ocr"
                    )
                # get signed url
                signed_url = self.mistral_client.files.get_signed_url(file_id=uploaded_file.id)
                ocr_response = self.mistral_client.ocr.process(
                    model="mistral-ocr-latest",
                    document={
                        "type": "document_url",
                        "document_url": signed_url.url
                    },
                    include_image_base64=False
                )
            finally:
                import os
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            
            # ตรวจสอบผลลัพธ์จาก OCR อย่างละเอียด
            if not ocr_response:
                return "OCR Error: ไม่ได้รับผลลัพธ์จาก API"
            
            # Debug OCR response structure
            logger.debug(f"OCR Response type: {type(ocr_response)}")
            logger.debug(f"OCR Response dir: {dir(ocr_response)}")
            
            result = ""
            
            # วิธีการดึงข้อความจาก Mistral OCR response
            try:
                # ลองดึงจาก attribute ต่างๆ
                if hasattr(ocr_response, "pages") and ocr_response.pages:
                    # Mistral OCR มักจะใส่ข้อความใน pages
                    pages_text = []
                    for page in ocr_response.pages:
                        if hasattr(page, "markdown") and page.markdown:
                            # Mistral OCR ใช้ markdown format
                            pages_text.append(page.markdown)
                        elif hasattr(page, "text") and page.text:
                            pages_text.append(page.text)
                        elif hasattr(page, "content") and page.content:
                            pages_text.append(page.content)
                    if pages_text:
                        result = "\n".join(pages_text)
                        
                elif hasattr(ocr_response, "text") and ocr_response.text:
                    result = ocr_response.text
                elif hasattr(ocr_response, "content") and ocr_response.content:
                    result = ocr_response.content
                elif hasattr(ocr_response, "result") and ocr_response.result:
                    result = ocr_response.result
                elif hasattr(ocr_response, "data") and ocr_response.data:
                    result = ocr_response.data
                elif hasattr(ocr_response, "extracted_text"):
                    result = ocr_response.extracted_text
                elif isinstance(ocr_response, dict):
                    # ค้นหาใน dict
                    result = (
                        ocr_response.get("text")
                        or ocr_response.get("content") 
                        or ocr_response.get("result")
                        or ocr_response.get("data")
                        or ocr_response.get("extracted_text")
                        or ""
                    )
                    # ถ้าไม่เจอ ลองดูใน pages
                    if not result and "pages" in ocr_response:
                        pages = ocr_response["pages"]
                        if isinstance(pages, list):
                            pages_text = []
                            for page in pages:
                                if isinstance(page, dict):
                                    page_text = page.get("text") or page.get("content") or ""
                                    if page_text:
                                        pages_text.append(page_text)
                            result = "\n".join(pages_text)
                
                # ถ้ายังไม่ได้ ให้ดู raw response
                if not result:
                    logger.warning(f"ไม่สามารถดึงข้อความได้ OCR Response: {str(ocr_response)[:500]}")
                    return f"OCR Error: ไม่พบข้อความใน response (Type: {type(ocr_response).__name__})"
                    
            except Exception as e:
                logger.error(f"Error parsing OCR response: {e}")
                return f"OCR Error: ไม่สามารถอ่าน response ({str(e)})"
            
            if result:
                await self.cache.set(pdf_url, result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ OCR Error for {pdf_url}: {str(e)}")
            return ""
    
    async def create_text_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
        """สร้าง embeddings สำหรับช่วยแก้คำผิด"""
        try:
            if not text_chunks:
                return []
            
            # จำกัดความยาวของแต่ละ chunk
            processed_chunks = []
            for chunk in text_chunks:
                if len(chunk) > 1000:  # จำกัด 1000 ตัวอักษร
                    chunk = chunk[:1000]
                processed_chunks.append(chunk)
            
            # สร้าง embeddings ด้วย Mistral
            embeddings_response = self.mistral_client.embeddings.create(
                model=self.embedding_model,
                inputs=processed_chunks,
            )
            
            # แยกเฉพาะ embeddings data
            embeddings = []
            for data in embeddings_response.data:
                embeddings.append(data.embedding)
            
            logger.info(f"✅ สร้าง embeddings สำเร็จ: {len(embeddings)} chunks")
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Embeddings Error: {str(e)}")
            return []
    
    async def correct_text_with_deepseek(self, error_text: str) -> str:
        """ใช้ DeepSeek แก้ไขข้อความผิด"""
        try:
            # ตรวจสอบ cache
            error_hash = hashlib.md5(error_text.encode()).hexdigest()[:8]
            if error_hash in self.embedding_cache:
                return self.embedding_cache[error_hash]
            
            # ถ้าไม่มี DeepSeek client ให้ return ข้อความเดิม
            if not self.deepseek_client:
                return error_text
            
            # สร้าง prompt สำหรับแก้ไขคำผิด
            prompt = f"""กรุณาแก้ไขข้อผิดพลาดในข้อความภาษาไทยต่อไปนี้ โดยเฉพาะข้อผิดพลาดจาก OCR:

ข้อความที่มีข้อผิดพลาด: {error_text}

กรุณาแก้ไข:
1. ตัวอักษรที่ OCR อ่านผิด เช่น "ะ" ที่ควรเป็น "๖", "ตม" ที่ควรเป็น "กม"
2. ตัวเลขไทยที่ผิด เช่น "๒๕ะ๘" ที่ควรเป็น "๒๕๖๘"
3. คำที่สะกดผิดในบริบทราชการไทย
4. เว้นวรรคผิด

ตอบด้วยข้อความที่แก้ไขแล้วเท่านั้น ไม่ต้องอธิบาย:"""

            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "คุณเป็นผู้เชี่ยวชาญในการแก้ไขข้อผิดพลาดจาก OCR ภาษาไทย"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.1
                )
            )
            
            corrected_text = response.choices[0].message.content.strip()
            
            # Cache ผลลัพธ์
            self.embedding_cache[error_hash] = corrected_text
            
            logger.info(f"🤖 DeepSeek แก้ไข: '{error_text[:30]}...' → '{corrected_text[:30]}...'")
            return corrected_text
            
        except Exception as e:
            logger.warning(f"⚠️ DeepSeek correction failed: {e}")
            return error_text

class RatchakitchaScraperCrawl4AI:
    """Scraper ใช้ crawl4ai แต่แก้ไขปัญหา Windows"""
    
    def __init__(self):
        self.base_url = "https://ratchakitcha.soc.go.th"
        self.documents_pattern = r'(?:href|src)=["\']([^"\']*documents/[^"\']*\.pdf)["\']'
        self.processed_urls: Set[str] = set()
        
        # เริ่มต้น OCR - Mistral OCR + DeepSeek Text Correction
        try:
            # ตรวจสอบว่าจะใช้ DeepSeek สำหรับแก้ไขคำผิดหรือไม่
            use_deepseek_correction = DEEPSEEK_AVAILABLE and os.getenv("DEEPSEEK_API_KEY")
            self.ocr = MistralOCRWithDeepSeekCorrection(use_deepseek_correction=use_deepseek_correction)
        except ValueError as e:
            logger.error(f"❌ ไม่สามารถเริ่มต้น OCR: {e}")
            self.ocr = None
        
        # ตรวจสอบว่า crawl4ai ใช้งานได้หรือไม่
        self.use_crawl4ai = CRAWL4AI_AVAILABLE
        
        if self.use_crawl4ai:
            # Browser config - เพิ่มความเสถียรสำหรับ Windows
            self.browser_config = BrowserConfig(
                headless=True,
                verbose=False,
                browser_type="chromium",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                extra_args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage", 
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-ipc-flooding-protection",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-default-apps",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-sync",
                    "--disable-translate",
                    "--hide-scrollbars",
                    "--mute-audio",
                    "--no-zygote",  # สำคัญสำหรับ Windows
                    "--single-process"  # ลด process overhead
                ]
            )
            
            # Crawler config - เร็วและเสถียร
            self.run_config = CrawlerRunConfig(
                cache_mode=CacheMode.ENABLED,
                word_count_threshold=5,
                wait_for_images=False,
                delay_before_return_html=2.0,  # เพิ่มเล็กน้อยสำหรับความเสถียร
                page_timeout=20000,  # 20 วินาที
                remove_overlay_elements=True,
                simulate_user=True,  # จำลองผู้ใช้จริง
                override_navigator=True  # หลีกเลี่ยงการตรวจจับ bot
            )
        
        # Fallback headers สำหรับ aiohttp
        self.fallback_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }

    async def discover_pdf_links_crawl4ai(self, start_url: str = None, max_pages: int = 25) -> List[Dict]:
        """ค้นหาลิ้งค์ PDF ด้วย crawl4ai (Fixed for Windows)"""
        if not start_url:
            start_url = self.base_url
            
        all_pdf_links = []
        logger.info(f"🚀 เริ่มค้นหาลิ้งค์ PDF ด้วย crawl4ai (Windows Fixed): {start_url}")
        
        if not self.use_crawl4ai:
            logger.error("❌ crawl4ai ไม่สามารถใช้งานได้ กลับไปใช้ aiohttp")
            return await self.discover_pdf_links_fallback(start_url, max_pages)
        
        try:
            # สร้าง new event loop สำหรับ crawl4ai
            if platform.system() == 'Windows':
                # สำหรับ Windows ใช้ ProactorEventLoop
                try:
                    loop = asyncio.ProactorEventLoop()
                    asyncio.set_event_loop(loop)
                except:
                    # fallback ถ้าไม่ได้
                    pass
            
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                logger.info("🌐 เริ่มต้น crawl4ai browser...")
                
                # ดึงหน้าหลักด้วย retry
                result = None
                for attempt in range(3):
                    try:
                        logger.info(f"📄 ดึงหน้าหลัก (ครั้งที่ {attempt + 1})...")
                        result = await crawler.arun(url=start_url, config=self.run_config)
                        if result.success:
                            break
                        else:
                            logger.warning(f"⚠️ ครั้งที่ {attempt + 1} ไม่สำเร็จ: {result.error_message}")
                            if attempt < 2:
                                await asyncio.sleep(random.uniform(2, 5))
                    except Exception as e:
                        logger.warning(f"⚠️ ครั้งที่ {attempt + 1} เกิดข้อผิดพลาด: {e}")
                        if attempt < 2:
                            await asyncio.sleep(random.uniform(2, 5))
                
                if result and result.success:
                    logger.info(f"✅ ดึงหน้าหลักสำเร็จ ({len(result.html)} characters)")
                    
                    # หาลิ้งค์ PDF และ navigation links พร้อมกัน
                    pdf_task = self._extract_pdf_links_from_html(result.html, start_url)
                    nav_task = self._find_navigation_links(result.html, start_url)
                    
                    pdf_links, page_links = await asyncio.gather(pdf_task, nav_task)
                    all_pdf_links.extend(pdf_links)
                    
                    logger.info(f"📄 พบ PDF {len(pdf_links)} ไฟล์จากหน้าหลัก")
                    
                    # จำกัดจำนวนหน้า
                    page_links = page_links[:max_pages]
                    logger.info(f"🔗 จะสแกน {len(page_links)} หน้าเพิ่มเติม")
                    
                    # สแกนหลายหน้าพร้อมกัน แต่จำกัด concurrent สำหรับ Windows
                    if page_links:
                        semaphore = asyncio.Semaphore(8)  # ลดลงสำหรับ Windows
                        
                        async def scan_page(page_url):
                            async with semaphore:
                                try:
                                    # เพิ่ม delay แบบสุ่ม
                                    await asyncio.sleep(random.uniform(1, 3))
                                    
                                    page_result = await crawler.arun(url=page_url, config=self.run_config)
                                    if page_result.success:
                                        return await self._extract_pdf_links_from_html(page_result.html, page_url)
                                    else:
                                        logger.warning(f"⚠️ ไม่สามารถดึง {page_url}: {page_result.error_message}")
                                except Exception as e:
                                    logger.warning(f"Error scanning {page_url}: {e}")
                                return []
                        
                        # รันทุกหน้าพร้อมกัน
                        tasks = [scan_page(url) for url in page_links]
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        for i, result in enumerate(results):
                            if isinstance(result, list):
                                all_pdf_links.extend(result)
                                if result:
                                    logger.info(f"   ✅ หน้า {i+1}: พบ {len(result)} PDF")
                            elif isinstance(result, Exception):
                                logger.warning(f"   ❌ หน้า {i+1}: {result}")
                else:
                    logger.error("❌ ไม่สามารถดึงหน้าหลักด้วย crawl4ai")
                    return await self.discover_pdf_links_fallback(start_url, max_pages)
                
        except Exception as e:
            logger.error(f"❌ crawl4ai Error: {e}")
            logger.info("🔄 กลับไปใช้ aiohttp fallback...")
            return await self.discover_pdf_links_fallback(start_url, max_pages)
        
        # ลบรายการซ้ำ
        unique_pdf_links = self._remove_duplicate_links_fast(all_pdf_links)
        logger.info(f"🎉 พบลิ้งค์ PDF ทั้งหมด {len(unique_pdf_links)} ไฟล์")
        
        return unique_pdf_links

    async def discover_pdf_links_fallback(self, start_url: str, max_pages: int) -> List[Dict]:
        """Fallback ใช้ aiohttp เมื่อ crawl4ai ไม่ได้"""
        logger.info("🔄 ใช้ aiohttp fallback สำหรับการค้นหา PDF")
        
        all_pdf_links = []
        timeout = aiohttp.ClientTimeout(total=30)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=self.fallback_headers) as session:
                # ดึงหน้าหลัก
                async with session.get(start_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        pdf_links = await self._extract_pdf_links_from_html(content, start_url)
                        all_pdf_links.extend(pdf_links)
                        logger.info(f"📄 aiohttp fallback: พบ {len(pdf_links)} PDF")
                    else:
                        logger.warning(f"aiohttp fallback HTTP {response.status}")
        except Exception as e:
            logger.error(f"❌ aiohttp fallback error: {e}")
        
        return self._remove_duplicate_links_fast(all_pdf_links)

    async def _extract_pdf_links_from_html(self, html: str, base_url: str) -> List[Dict]:
        """แยกลิ้งค์ PDF จาก HTML - Optimized"""
        pdf_links = []
        
        # รวม patterns ทั้งหมด
        all_patterns = [
            self.documents_pattern,
            r'href=["\']([^"\']*\.pdf)["\']',
            r'documents/(\d+)\.pdf',
            r'/documents/([^"\']*\.pdf)',
            r'href=["\']([^"\']*\.PDF)["\']',  # uppercase
            r'src=["\']([^"\']*\.pdf)["\']'
        ]
        
        for pattern in all_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                # สร้าง URL เต็ม
                if match.startswith('http'):
                    full_url = match
                else:
                    full_url = urljoin(base_url, match)
                
                # ตรวจสอบไม่ให้ซ้ำ
                if full_url not in self.processed_urls:
                    self.processed_urls.add(full_url)
                    
                    title = self._extract_title_near_link_fast(html, match)
                    pdf_links.append({
                        'url': full_url,
                        'title': title,
                        'filename': os.path.basename(match),
                        'found_on_page': base_url
                    })
        
        return pdf_links

    def _extract_title_near_link_fast(self, html: str, link: str) -> str:
        """หาชื่อเอกสารอย่างรวดเร็ว"""
        try:
            link_pos = html.find(link)
            if link_pos == -1:
                return "ไม่ระบุชื่อ"
            
            # ค้นหาในพื้นที่จำกัด
            start = max(0, link_pos - 150)
            end = min(len(html), link_pos + 150)
            context = html[start:end]
            
            # ใช้ pattern เดียวที่มีประสิทธิภาพสูงสุด
            patterns = [
                r'<title[^>]*>([^<]+)</title>',
                r'<h[1-6][^>]*>([^<]+)</h[1-6]>',
                r'>([^<]{15,80})<',
                r'alt=["\']([^"\']{10,})["\']'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    clean_title = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                    if len(clean_title) > 10 and 'pdf' not in clean_title.lower():
                        return clean_title[:100]
            
            return f"เอกสาร PDF จาก {urlparse(link).netloc}"
            
        except Exception:
            return "ไม่ระบุชื่อ"

    async def _find_navigation_links(self, html: str, base_url: str) -> List[str]:
        """หาลิ้งค์นำทางอย่างรวดเร็ว"""
        nav_links = []
        
        # ใช้ pattern ที่ครอบคลุม
        patterns = [
            r'href=["\']([^"\']*(?:page|หน้า|next|category|archive)[^"\']*)["\']',
            r'href=["\']([^"\']*\/\d+\/?)["\']',
            r'href=["\']([^"\']*\?page[^"\']*)["\']'
        ]
        
        base_netloc = urlparse(base_url).netloc
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if match.startswith('http'):
                    full_url = match
                else:
                    full_url = urljoin(base_url, match)
                
                # ตรวจสอบ domain เดียวกัน
                if urlparse(full_url).netloc == base_netloc:
                    nav_links.append(full_url)
        
        return list(set(nav_links))

    def _remove_duplicate_links_fast(self, links: List[Dict]) -> List[Dict]:
        """ลบลิ้งค์ซ้ำอย่างรวดเร็ว"""
        seen_urls = set()
        unique_links = []
        
        for link in links:
            url = link['url']
            if url not in seen_urls:
                seen_urls.add(url)
                unique_links.append(link)
        
        return unique_links

    async def extract_pdf_text_fast(self, pdf_url: str) -> tuple:
        """ดึงเนื้อหาและ metadata พร้อมกัน"""
        if not self.ocr:
            return "ไม่สามารถใช้ OCR ได้", {'content_length': 'N/A', 'content_type': 'N/A'}
        
        try:
            # ใช้ OCR กับ URL โดยตรง
            text_task = self.ocr.extract_text_from_pdf_url_cached(pdf_url)
            
            # ดึง metadata
            async def get_metadata():
                try:
                    timeout = aiohttp.ClientTimeout(total=10)
                    async with aiohttp.ClientSession(timeout=timeout, headers=self.fallback_headers) as session:
                        async with session.head(pdf_url) as response:
                            return {
                                'content_length': response.headers.get('content-length', 'N/A'),
                                'content_type': response.headers.get('content-type', 'N/A'),
                                'status': response.status
                            }
                except:
                    return {'content_length': 'N/A', 'content_type': 'N/A', 'status': 'Error'}
            
            # รันพร้อมกัน
            text, metadata = await asyncio.gather(text_task, get_metadata(), return_exceptions=True)
            
            if isinstance(text, Exception):
                text = f"OCR Error: {str(text)}"
            if isinstance(metadata, Exception):
                metadata = {'content_length': 'N/A', 'content_type': 'N/A', 'status': 'Error'}
            
            return text, metadata
            
        except Exception as e:
            return f"Error: {str(e)}", {'content_length': 'N/A', 'content_type': 'N/A', 'status': 'Error'}

    async def process_single_pdf_fast(self, pdf_info: Dict, index: int, pdf_limit: int = 0) -> List[Dict]:
        """ประมวลผล PDF เดียว (รองรับการจำกัดจำนวนไฟล์และแบ่งข้อความยาว)"""
        try:
            # ถ้าเกิน limit ให้ return None
            if pdf_limit > 0 and index > pdf_limit:
                return []

            text, metadata = await self.extract_pdf_text_fast(pdf_info['url'])

            # ทำความสะอาดข้อความและคำนวณ metadata
            original_text = text
            is_ocr_success = text and len(text.strip()) > 20 and not text.startswith("OCR Error")
            
            if is_ocr_success:
                cleaned_text = await self._clean_extracted_text_fast(text)
            else:
                cleaned_text = f"OCR Error: ไม่สามารถดึงข้อความจาก PDF นี้ได้"

            # สร้าง enhanced metadata
            enhanced_metadata = self._generate_enhanced_metadata(
                pdf_info, cleaned_text, original_text, metadata, is_ocr_success
            )

            # ถ้าข้อความยาวเกิน 30,000 ตัวอักษร ให้แบ่งเป็นหลาย rows
            max_length = 30000
            results = []
            
            if len(cleaned_text) <= max_length:
                # ถ้าไม่เกิน 30,000 ให้สร้าง row เดียว
                results.append({
                    'id': index,
                    'url': pdf_info['url'],
                    'title': pdf_info['title'],
                    'text': cleaned_text,
                    'filename': pdf_info['filename'],
                    'found_on_page': pdf_info['found_on_page'],
                    'file_size': metadata.get('content_length', 'N/A'),
                    'content_type': metadata.get('content_type', 'N/A'),
                    'created_at': datetime.now().isoformat(),
                    'metadata': enhanced_metadata
                })
            else:
                # ถ้าเกิน 30,000 ให้แบ่งเป็นหลาย rows
                text_chunks = self._split_text_smartly(cleaned_text, max_length)
                logger.info(f"📄 แบ่งข้อความยาว {len(cleaned_text):,} ตัวอักษรเป็น {len(text_chunks)} ส่วน")
                
                for chunk_index, chunk_text in enumerate(text_chunks):
                    # สร้าง metadata สำหรับแต่ละ chunk
                    chunk_metadata = enhanced_metadata.copy()
                    chunk_metadata['text_analysis']['is_chunk'] = True
                    chunk_metadata['text_analysis']['chunk_index'] = chunk_index + 1
                    chunk_metadata['text_analysis']['total_chunks'] = len(text_chunks)
                    chunk_metadata['text_analysis']['character_count'] = len(chunk_text)
                    chunk_metadata['text_analysis']['word_count'] = len(chunk_text.split())
                    
                    results.append({
                        'id': f"{index}.{chunk_index + 1}",  # เช่น 1.1, 1.2, 1.3
                        'url': pdf_info['url'],
                        'title': f"{pdf_info['title']} (ส่วนที่ {chunk_index + 1}/{len(text_chunks)})",
                        'text': chunk_text,
                        'filename': pdf_info['filename'],
                        'found_on_page': pdf_info['found_on_page'],
                        'file_size': metadata.get('content_length', 'N/A'),
                        'content_type': metadata.get('content_type', 'N/A'),
                        'created_at': datetime.now().isoformat(),
                        'metadata': chunk_metadata
                    })

            return results

        except Exception as e:
            logger.error(f"❌ Error processing {pdf_info['url']}: {e}")
            return []

    async def _clean_extracted_text_fast(self, text: str) -> str:
        """ทำความสะอาดข้อความอย่างรวดเร็วและมีคุณภาพ"""
        if not text:
            return ""
        
        # 1. ลบ markdown elements และคำว่า "text" ที่ไม่ต้องการ (แบบเจาะจง)
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)  # ลบ image references
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)   # ลบ links
        text = re.sub(r'#{1,6}\s*', '', text)       # ลบ headers แต่เก็บข้อความ
        
        # ลบคำ "text" แบบเจาะจง (ไม่ลบ context, texture etc.)
        text = re.sub(r'\btext\b', '', text, flags=re.IGNORECASE)  # ลบคำ "text" เดี่ยวๆ
        text = re.sub(r'^\s*text\s*$', '', text, flags=re.IGNORECASE | re.MULTILINE)  # ลบบรรทัดที่มีแค่ "text"
        text = re.sub(r'\s+text\s+', ' ', text, flags=re.IGNORECASE)  # ลบ "text" ที่มี space รอบ
        
        # 2. ลบ HTML tags และ entities
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
        
        # 3. ลบ table formatting และ special characters ที่ไม่จำเป็น
        text = re.sub(r'\|+', ' ', text)            # ลบ table separators
        text = re.sub(r':--+:?', ' ', text)         # ลบ table alignment
        text = re.sub(r'\$+.*?\$+', ' ', text)      # ลบ LaTeX math
        text = re.sub(r'\\[a-zA-Z]+\{.*?\}', ' ', text)  # ลบ LaTeX commands
        
        # 4. จัดการ whitespace และ newlines
        text = re.sub(r'\n+', ' ', text)            # แปลง newlines เป็น spaces
        text = re.sub(r'\s+', ' ', text)            # รวม multiple spaces
        text = text.strip()
        
        # 4.5. แก้ไขเลขเทวนาครีให้เป็นเลขไทย
        devanagari_to_thai = str.maketrans('०१२३४५६७८९', '๐๑๒๓๔๕๖๗๘๙')
        text = text.translate(devanagari_to_thai)
        
        # 4.6. แก้ไขเลขไทยที่ OCR อ่านผิด (เช่น ะ ที่ควรเป็น ๖) - ขยายครอบคลุม
        
        # Pattern-based fixes สำหรับเลขปี พ.ศ. ที่ผิด
        text = re.sub(r'(\d+)ะ(\d+)', r'\1๖\2', text)  # เปลี่ยน ะ ระหว่างเลขเป็น ๖
        text = re.sub(r'พ\.ศ\.\s*๒๕ะ([๐-๙])', r'พ.ศ. ๒๕๖\1', text)  # แก้ปี พ.ศ. เฉพาะ
        
        # Common OCR fixes
        common_ocr_fixes = {
            # ปีที่พบบ่อย
            '๒๕ะ๘': '๒๕๖๘', '๒๕ะ๗': '๒๕๖๗', '๒๕ะ๙': '๒๕๖๙', '๒๕ะ๐': '๒๕๖๐',
            '๒๕ะ๑': '๒๕๖๑', '๒๕ะ๒': '๒๕๖๒', '๒๕ะ๓': '๒๕๖๓', '๒๕ะ๔': '๒๕๖๔', '๒๕ะ๕': '๒๕๖๕',
            # เลขมาตรา
            'มาตรา ะ': 'มาตรา ๖', 'มาตรา ๑ะ': 'มาตรา ๑๖', 'มาตรา ๒ะ': 'มาตรา ๒๖',
            # ตัวเลขทั่วไป
            'ะ๐': '๖๐', 'ะ๑': '๖๑', 'ะ๒': '๖๒', 'ะ๓': '๖๓', 'ะ๔': '๖๔', 'ะ๕': '๖๕',
            'ะ๗': '๖๗', 'ะ๘': '๖๘', 'ะ๙': '๖๙',
        }
        for wrong, correct in common_ocr_fixes.items():
            text = text.replace(wrong, correct)
        
        # แก้ไขความสอดคล้องของปี พ.ศ. ในเอกสาร
        # หาปีหลักที่ปรากฏใน title หรือต้นเอกสาร
        year_match = re.search(r'พ\.ศ\.\s*(\d{4})', text[:500])
        if year_match:
            main_year = year_match.group(1)
            # แทนที่ปีที่ไม่สอดคล้องด้วยปีหลัก (สำหรับเอกสารเดียวกัน)
            text = re.sub(r'พ\.ศ\.\s*\d{4}', f'พ.ศ. {main_year}', text)
        
        logger.debug("🔢 แปลงเลขเทวนาครีและแก้ไข OCR ตัวเลขแล้ว")
        
        # 5. ลบอักขระพิเศษที่ไม่จำเป็น แต่เก็บสระไทยและเครื่องหมายวรรคตอน
        # เก็บ: ตัวอักษร ตัวเลข วรรคตอนพื้นฐาน วงเล็บ และอักขระไทย
        text = re.sub(r'[^\w\s\.\,\!\?\-\(\)\:\;\"\'๐-๙\u0E00-\u0E7F]', '', text, flags=re.UNICODE)
        
        # 6. ตรวจสอบความยาวและคุณภาพ
        if len(text) < 20:
            return f"ข้อความสั้น: {text}"
        
        # 7. แก้ไขคำผิดด้วย PyThaiNLP (ถ้ามี) - Smart Error Detection + Fast Correction
        if PYTHAINLP_AVAILABLE and len(text) > 50:
            try:
                # 🎯 Step 1: ตรวจจับคำผิดก่อน (เร็วมาก)
                potential_errors = []
                
                # Pattern สำหรับหาคำผิดที่พบบ่อยใน OCR
                error_patterns = [
                    r'[๐-๙०-९]+[ะ][๐-๙०-९]+',  # เช่น "๒๕ะ๘" ควรเป็น "๒๕๖๘"
                    r'[๐-๙०-९]+[,][๐-๙०-९]+[०][๐-๙०-९]+[,][०]+',  # เลขผสม เทวนาครี เช่น "๓,๗๕๖,๗๐๐,๐๐๐,०००"
                    r'[०-९]+',  # เลขเทวนาครีที่ต้องแปลงเป็นเลขไทย
                    r'[ก-๙]{1,3}[กี่]{1,2}[ก-๙]{1,3}',  # เช่น "กี่" ควรเป็น "กัน"
                    r'[๐-๙]+[ตบปผฝพฟภม]\b',  # ตัวเลขติดตัวอักษรผิด
                    r'\b[ตบปผฝพฟภม]{1,2}\b',  # ตัวอักษรเดี่ยวผิดๆ
                    r'[ก-ฮ]{10,}',     # คำยาวผิดปกติ
                    r'\.{3,}',         # จุดมากเกินไป
                    r'\s{3,}',         # space มากเกินไป
                ]
                
                # หาส่วนที่มีปัญหา
                error_spans = []
                for pattern in error_patterns:
                    for match in re.finditer(pattern, text):
                        start, end = match.span()
                        # เพิ่มบริบทรอบๆ (เล็กลง 15 ตัวอักษรข้างหน้า-หลัง เพื่อความเร็ว)
                        context_start = max(0, start - 15)
                        context_end = min(len(text), end + 15)
                        error_spans.append((context_start, context_end, match.group()))
                
                # 🚀 Step 2: แก้ไขเฉพาะส่วนที่มีปัญหา (เร็วมาก)
                if error_spans:
                    logger.info(f"🔍 พบข้อผิดพลาด {len(error_spans)} จุด - จะแก้ไขเฉพาะส่วนนี้")
                    
                    corrected_parts = {}
                    corrected_count = 0
                    
                    for i, (start, end, error_text) in enumerate(error_spans[:3]):  # จำกัดแค่ 3 จุดแรก (เร็วขึ้นมาก)
                        context = text[start:end]
                        
                        # ลบช่วงที่ยาวเกินไป เพื่อความเร็ว
                        if len(context) > 50:
                            context = context[:50]
                        
                        # ตรวจสอบ cache
                        context_hash = hashlib.md5(context.encode()).hexdigest()[:8]
                        if context_hash in _pythainlp_cache:
                            corrected_parts[(start, end)] = _pythainlp_cache[context_hash]
                            logger.debug(f"📚 Cache hit สำหรับ error {i+1}")
                            continue
                        
                        # 🎯 Step 2.1: ใช้ PyThaiNLP ตรวจหาคำผิด (ด้วย timeout เร็วขึ้น)
                        start_time = time.time()
                        try:
                            # ใช้ executor เพื่อ timeout PyThaiNLP - แก้ไขปัญหา callable
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                # แก้ไข: ใช้ pythainlp.correct.correct แทน correct โดยตรง
                                future = executor.submit(pythainlp.correct.correct, context)
                                try:
                                    pythainlp_corrected = future.result(timeout=2.0)  # เพิ่มเวลาให้ PyThaiNLP ทำงาน
                                except concurrent.futures.TimeoutError:
                                    logger.warning(f"⏰ Error {i+1} PyThaiNLP timeout หลัง 2.0s, ข้าม")
                                    break
                            
                            elapsed = time.time() - start_time
                            
                            # ถ้า PyThaiNLP แก้ไขได้และไม่ช้าเกินไป
                            if pythainlp_corrected and pythainlp_corrected != context:
                                # ใช้ PyThaiNLP เพื่อตรวจหาคำผิด แล้วส่งให้ DeepSeek แก้ไข
                                if hasattr(self, 'ocr') and self.ocr and self.ocr.deepseek_client:
                                    # ส่งข้อความที่ PyThaiNLP ตรวจพบความผิดปกติให้ DeepSeek แก้ไข
                                    import asyncio
                                    deepseek_corrected = await self.ocr.correct_text_with_deepseek(context)
                                    if deepseek_corrected != context:
                                        corrected_parts[(start, end)] = deepseek_corrected
                                        _pythainlp_cache[context_hash] = deepseek_corrected
                                        corrected_count += 1
                                        logger.info(f"🤖 PyThaiNLP→DeepSeek แก้ไข error {i+1}: '{error_text[:15]}...'")
                                        continue
                                
                                # ถ้าไม่มี DeepSeek ให้ใช้ PyThaiNLP แก้ไข
                                corrected_parts[(start, end)] = pythainlp_corrected
                                _pythainlp_cache[context_hash] = pythainlp_corrected
                                corrected_count += 1
                                logger.info(f"📝 PyThaiNLP แก้ไข error {i+1}/{len(error_spans)} ({elapsed:.1f}s): '{error_text[:15]}...'")
                        except Exception as e:
                            logger.warning(f"⚠️ Error {i+1} PyThaiNLP ล้มเหลว: {e}")
                    
                    # 🔧 Step 3: รวมผลลัพธ์
                    if corrected_parts:
                        # เรียงจากหลังไปหน้า เพื่อไม่ให้ index เปลี่ยน
                        for (start, end), corrected_text in sorted(corrected_parts.items(), reverse=True):
                            text = text[:start] + corrected_text + text[end:]
                        
                        logger.info(f"🎉 PyThaiNLP: แก้ไข {corrected_count}/{len(error_spans)} ข้อผิดพลาด สำเร็จ!")
                    else:
                        logger.info("📝 PyThaiNLP: ไม่พบข้อผิดพลาดที่แก้ไขได้")
                else:
                    logger.info("✅ PyThaiNLP: ไม่พบข้อผิดพลาดที่ต้องแก้ไข")
                
                # จำกัดขนาด cache
                if len(_pythainlp_cache) > 200:
                    _pythainlp_cache.clear()
                    logger.debug("🧹 PyThaiNLP cache cleared")
                        
            except Exception as e:
                logger.warning(f"⚠️ PyThaiNLP smart correction failed: {e}")
        
        # 8. ไม่ตัดข้อความ เก็บไว้ครบ
        return text

    def _generate_enhanced_metadata(self, pdf_info: Dict, cleaned_text: str, original_text: str, 
                                  metadata: Dict, is_ocr_success: bool) -> Dict:
        """สร้าง metadata ที่ละเอียดสำหรับ dataset"""
        try:
            # ข้อมูลพื้นฐาน
            file_size_bytes = metadata.get('content_length', 'N/A')
            if file_size_bytes != 'N/A' and str(file_size_bytes).isdigit():
                file_size_mb = round(int(file_size_bytes) / (1024 * 1024), 2)
            else:
                file_size_mb = 'N/A'

            # วิเคราะห์ข้อความ
            word_count = len(cleaned_text.split()) if cleaned_text else 0
            char_count = len(cleaned_text) if cleaned_text else 0
            line_count = len(cleaned_text.split('\n')) if cleaned_text else 0

            # ตรวจหาประเภทเอกสาร
            doc_type = self._classify_document_type(cleaned_text)
            
            # ดึงปี พ.ศ. จากข้อความ
            buddhist_year = self._extract_buddhist_year(cleaned_text)
            
            # ค้นหาคำสำคัญ
            keywords = self._extract_keywords(cleaned_text)

            # ข้อมูล URL
            url_parts = urlparse(pdf_info['url'])
            document_id = self._extract_document_id(pdf_info['filename'])

            return {
                'processing': {
                    'ocr_success': is_ocr_success,
                    'ocr_engine': 'mistral-ocr-latest',
                    'text_correction': 'pythainlp+deepseek' if (PYTHAINLP_AVAILABLE and self.ocr and self.ocr.deepseek_client) else ('pythainlp' if PYTHAINLP_AVAILABLE else 'none'),
                    'processing_timestamp': datetime.now().isoformat(),
                    'text_length_original': len(original_text) if original_text else 0,
                    'text_length_cleaned': char_count,
                    'has_markdown': '![' in original_text if original_text else False
                },
                'file_info': {
                    'file_size_bytes': file_size_bytes,
                    'file_size_mb': file_size_mb,
                    'content_type': metadata.get('content_type', 'N/A'),
                    'document_id': document_id,
                    'url_domain': url_parts.netloc,
                    'url_path': url_parts.path
                },
                'text_analysis': {
                    'word_count': word_count,
                    'character_count': char_count,
                    'line_count': line_count,
                    'avg_words_per_line': round(word_count / line_count, 2) if line_count > 0 else 0,
                    'document_type': doc_type,
                    'buddhist_year': buddhist_year,
                    'keywords': keywords[:10]  # เอาแค่ 10 คำแรก
                },
                'source': {
                    'base_url': 'https://ratchakitcha.soc.go.th',
                    'discovered_on': pdf_info.get('found_on_page', 'N/A'),
                    'scraper_version': '1.0.0',
                    'scraper_method': 'crawl4ai'
                }
            }
        except Exception as e:
            logger.warning(f"Error generating metadata: {e}")
            return {
                'processing': {'ocr_success': is_ocr_success, 'error': str(e)},
                'file_info': {'file_size_bytes': file_size_bytes},
                'text_analysis': {'word_count': word_count, 'character_count': char_count},
                'source': {'base_url': 'https://ratchakitcha.soc.go.th'}
            }

    def _classify_document_type(self, text: str) -> str:
        """จำแนกประเภทเอกสาร"""
        if not text:
            return "unknown"
        
        text_lower = text.lower()
        
        # รูปแบบเอกสารราชกิจจานุเบกษา
        if any(word in text_lower for word in ['พระราชบัญญัติ', 'royal decree']):
            return "พระราชบัญญัติ"
        elif any(word in text_lower for word in ['ประกาศ', 'announcement']):
            return "ประกาศ"
        elif any(word in text_lower for word in ['กฎกระทรวง', 'ministerial regulation']):
            return "กฎกระทรวง"
        elif any(word in text_lower for word in ['คำสั่ง', 'order']):
            return "คำสั่ง"
        elif any(word in text_lower for word in ['ข้อบังคับ', 'regulation']):
            return "ข้อบังคับ"
        elif any(word in text_lower for word in ['แต่งตั้ง', 'appointment']):
            return "แต่งตั้ง"
        elif any(word in text_lower for word in ['งบประมาณ', 'budget']):
            return "งบประมาณ"
        else:
            return "เอกสารทั่วไป"

    def _extract_buddhist_year(self, text: str) -> Optional[str]:
        """ดึงปี พ.ศ. จากข้อความ"""
        if not text:
            return None
        
        # หา pattern ปี พ.ศ.
        patterns = [
            r'พ\.ศ\.?\s*(\d{4})',
            r'พุทธศักราช\s*(\d{4})',
            r'B\.E\.?\s*(\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                year = match.group(1)
                # ตรวจสอบว่าเป็นปี พ.ศ. ที่สมเหตุสมผล (2400-2600)
                if 2400 <= int(year) <= 2600:
                    return year
        
        return None

    def _extract_keywords(self, text: str) -> List[str]:
        """ดึงคำสำคัญจากข้อความ"""
        if not text:
            return []
        
        # คำสำคัญที่สำคัญในเอกสารราชกิจจานุเบกษา
        important_keywords = [
            'พระบาทสมเด็จพระเจ้าอยู่หัว', 'นายกรัฐมนตรี', 'รัฐมนตรี', 'กระทรวง',
            'พระราชบัญญัติ', 'ประกาศ', 'กฎกระทรวง', 'งบประมาณ', 'แต่งตั้ง',
            'ราชกิจจานุเบกษา', 'รัฐธรรมนูญ', 'พระราชกฤษฎีกา'
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in important_keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        # เพิ่มคำที่ปรากฏบ่อย (simple approach)
        words = re.findall(r'\b\w{4,}\b', text)  # คำที่มีอย่างน้อย 4 ตัวอักษร
        word_freq = {}
        for word in words:
            if len(word) >= 4:  # เฉพาะคำยาวๆ
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # เอาคำที่ปรากฏบ่อยสุด 5 คำ
        frequent_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        found_keywords.extend([word for word, freq in frequent_words if freq > 1])
        
        return list(set(found_keywords))  # ลบซ้ำ

    def _extract_document_id(self, filename: str) -> Optional[str]:
        """ดึงเลขที่เอกสารจากชื่อไฟล์"""
        if not filename:
            return None
        
        # ลองดึงตัวเลขจากชื่อไฟล์
        match = re.search(r'(\d+)', filename)
        if match:
            return match.group(1)
        
        return None

    def _split_text_smartly(self, text: str, max_length: int) -> List[str]:
        """แบ่งข้อความอย่างชาญฉลาด โดยไม่ตัดคำ"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            # คำนวณตำแหน่งสิ้นสุด
            end_pos = min(current_pos + max_length, len(text))
            
            # ถ้าไม่ใช่ส่วนสุดท้าย ให้หาจุดตัดที่เหมาะสม
            if end_pos < len(text):
                # หาจุดตัดที่ดี เช่น จุด, อัตราการขึ้นบรรทัดใหม่, วรรค
                good_break_points = [
                    text.rfind('\n\n', current_pos, end_pos),  # paragraph break
                    text.rfind('. ', current_pos, end_pos),    # sentence end
                    text.rfind('। ', current_pos, end_pos),    # Thai sentence end
                    text.rfind('\n', current_pos, end_pos),    # line break
                    text.rfind(' ', current_pos, end_pos),     # word boundary
                ]
                
                # เลือกจุดตัดที่ดีที่สุด
                best_break = -1
                for break_point in good_break_points:
                    if break_point > current_pos + max_length * 0.7:  # อย่างน้อย 70% ของ max_length
                        best_break = break_point
                        break
                
                if best_break > current_pos:
                    end_pos = best_break + 1  # +1 เพื่อรวม delimiter
            
            # ตัดข้อความ
            chunk = text[current_pos:end_pos].strip()
            if chunk:
                chunks.append(chunk)
            
            current_pos = end_pos
        
        return chunks

    async def create_dataset_ultra_fast(self, pdf_links: List[Dict], concurrent_limit: int = 15) -> List[Dict]:
        """สร้าง Dataset อย่างรวดเร็ว (รองรับการแบ่งข้อความยาว)"""
        logger.info(f"🚀 สร้าง Dataset จาก {len(pdf_links)} ไฟล์ (crawl4ai + Windows, concurrent: {concurrent_limit})")
        
        progress = ProgressTracker(len(pdf_links))
        dataset = []
        
        # ลด concurrent สำหรับ Windows stability
        semaphore = asyncio.Semaphore(min(concurrent_limit, 12))
        
        async def process_with_semaphore(pdf_info, index):
            async with semaphore:
                result = await self.process_single_pdf_fast(pdf_info, index + 1)
                progress.update(success=len(result) > 0 if result else False)
                return result
        
        tasks = [process_with_semaphore(pdf_info, i) for i, pdf_info in enumerate(pdf_links)]
        
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                if result:  # result เป็น List[Dict]
                    dataset.extend(result)  # ใช้ extend แทน append
                
                if len(dataset) % 20 == 0:
                    gc.collect()
                    
            except Exception as e:
                logger.error(f"Task failed: {e}")
                progress.update(success=False)
        
        # เรียงข้อมูลตาม id (รองรับทั้ง int และ string)
        def sort_key(x):
            id_val = x['id']
            if isinstance(id_val, str) and '.' in id_val:
                # สำหรับ id แบบ "1.1", "1.2" 
                parts = id_val.split('.')
                return (int(parts[0]), int(parts[1]))
            else:
                # สำหรับ id แบบ int
                return (int(id_val), 0)
        
        dataset.sort(key=sort_key)
        
        elapsed = time.time() - progress.start_time
        total_chunks = sum(1 for item in dataset if item.get('metadata', {}).get('text_analysis', {}).get('is_chunk', False))
        
        logger.info(f"🎉 เสร็จสิ้น! {len(dataset)} รายการ ใช้เวลา {elapsed/60:.1f} นาที "
                   f"(เร็วเฉลี่ย {len(dataset)/elapsed:.1f} ไฟล์/วินาที)")
        
        if total_chunks > 0:
            logger.info(f"📄 แบ่งข้อความยาวรวม {total_chunks} chunks จากเอกสารหลายชิ้น")
        
        return dataset

    async def save_dataset_to_csv(self, dataset: List[Dict], filename: str = "ratchakitcha_dataset.csv"):
        """บันทึก Dataset เป็น CSV"""
        if not dataset:
            logger.warning("⚠️ ไม่มีข้อมูลให้บันทึก")
            return
        
        try:
            df = pd.DataFrame(dataset)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"💾 บันทึก Dataset ลง {filename} ({len(dataset)} รายการ)")
        except Exception as e:
            logger.error(f"❌ Error บันทึก CSV: {e}")

    async def save_dataset_to_json(self, dataset: List[Dict], filename: str = "ratchakitcha_dataset.json"):
        """บันทึก Dataset เป็น JSON"""
        try:
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(dataset, ensure_ascii=False, indent=2))
            logger.info(f"💾 บันทึก Dataset ลง {filename}")
        except Exception as e:
            logger.error(f"❌ Error บันทึก JSON: {e}")

async def main():
    """ฟังก์ชันหลัก - crawl4ai Fixed for Windows + DeepSeek Support"""
    print("🚀 === Ratchakitcha PDF Scraper - MULTI OCR SUPPORT ===")
    print("🪟 ใช้ crawl4ai แต่แก้ไขปัญหา Windows Python 3.13")
    
    # แสดงสถานะ APIs
    print("\n🔗 API Status:")
    mistral_key = os.getenv("MISTRAL_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    
    if deepseek_key and DEEPSEEK_AVAILABLE:
        print("💎 DeepSeek API: ✅ พร้อมใช้งาน (ประหยัด 70เท่า!)")
    else:
        print("💎 DeepSeek API: ❌ ไม่พร้อมใช้งาน")
    
    if mistral_key:
        print("🤖 Mistral API: ✅ พร้อมใช้งาน")
    else:
        print("🤖 Mistral API: ❌ ไม่พร้อมใช้งาน")
    
    # แสดงสถานะ PyThaiNLP
    global PYTHAINLP_AVAILABLE
    if PYTHAINLP_AVAILABLE:
        print(f"📝 PyThaiNLP: ✅ พร้อมใช้งาน (มี cache ป้องกันค้าง)")
        try:
            use_pythainlp = input("\n🤔 ต้องการใช้ PyThaiNLP แก้ไขคำผิด? (y/N, กด Enter = ไม่ใช้): ").strip().lower()
            if use_pythainlp not in ['y', 'yes']:
                PYTHAINLP_AVAILABLE = False
                print("⚠️ ปิดการใช้งาน PyThaiNLP (เร็วขึ้น)")
            else:
                print("✅ เปิดการใช้งาน PyThaiNLP")
        except:
            PYTHAINLP_AVAILABLE = False
            print("⚠️ ปิดการใช้งาน PyThaiNLP (เร็วขึ้น)")
    else:
        print(f"📝 PyThaiNLP: ❌ ไม่พร้อมใช้งาน")
    
    print()
    scraper = RatchakitchaScraperCrawl4AI()
    
    if not scraper.ocr:
        print("❌ ไม่สามารถเริ่มต้น OCR - โปรดตรวจสอบ API Keys")
        if not mistral_key and not deepseek_key:
            print("💡 ต้องการ MISTRAL_API_KEY หรือ DEEPSEEK_API_KEY")
        return
    
    # แสดง OCR ที่ใช้งาน
    if scraper.ocr.use_deepseek_correction:
        print("🎯 ใช้ Mistral OCR + DeepSeek Text Correction (ประหยัด 70เท่า!)")
    else:
        print("🎯 ใช้ Mistral OCR + Pattern-based Text Correction")
    
    if not scraper.use_crawl4ai:
        print("⚠️ crawl4ai ไม่สามารถใช้งานได้ จะใช้ aiohttp fallback")
    
    try:
        start_time = time.time()
        
        # 1. ค้นหาลิ้งค์ PDF
        print("🔍 เริ่มการค้นหาลิ้งค์ PDF (crawl4ai Windows Fixed)...")
        pdf_links = await scraper.discover_pdf_links_crawl4ai(max_pages=30)
        
        if not pdf_links:
            print("❌ ไม่พบลิ้งค์ PDF")
            return
        
        discovery_time = time.time() - start_time
        print(f"✅ พบ {len(pdf_links)} ไฟล์ ใช้เวลา {discovery_time:.1f} วินาที")
        
        # แสดงตัวอย่าง
        print("\n📋 ตัวอย่างไฟล์ที่พบ:")
        for i, pdf in enumerate(pdf_links[:5], 1):
            print(f"   {i}. {pdf['title'][:50]}...")
            print(f"      URL: {pdf['url']}")
            print(f"      ไฟล์: {pdf['filename']}")
        
        if len(pdf_links) > 5:
            print(f"   ... และอีก {len(pdf_links) - 5} ไฟล์")
        
        # 2. ตั้งค่า
        try:
            concurrent_input = input(f"\nConcurrent limit สำหรับ OCR (แนะนำ: 10-15 สำหรับ Windows, default: 12): ").strip()
            concurrent_limit = int(concurrent_input) if concurrent_input.isdigit() else 12
            concurrent_limit = min(concurrent_limit, 15)
        except:
            concurrent_limit = 12
        
        # เพิ่มตัวเลือกจำกัดจำนวนไฟล์
        try:
            limit_input = input(f"\n📊 กำหนดจำนวนไฟล์ที่จะประมวลผล (ทั้งหมด {len(pdf_links)} ไฟล์, กด Enter = ทำทั้งหมด): ").strip()
            if limit_input.isdigit() and int(limit_input) > 0:
                file_limit = min(int(limit_input), len(pdf_links))
                pdf_links = pdf_links[:file_limit]
                print(f"📝 จะประมวลผลเพียง {file_limit} ไฟล์แรก")
            else:
                print(f"📝 จะประมวลผลทั้งหมด {len(pdf_links)} ไฟล์")
        except:
            print(f"📝 จะประมวลผลทั้งหมด {len(pdf_links)} ไฟล์")
        
        print(f"🚀 จะใช้ {concurrent_limit} concurrent connections (Windows Safe)")
        
        # 3. สร้าง Dataset
        dataset = await scraper.create_dataset_ultra_fast(pdf_links, concurrent_limit=concurrent_limit)
        
        if dataset:
            # 4. บันทึกไฟล์
            save_tasks = [
                scraper.save_dataset_to_csv(dataset, "ratchakitcha_dataset.csv"),
                scraper.save_dataset_to_json(dataset, "ratchakitcha_dataset.json")
            ]
            await asyncio.gather(*save_tasks)
            
            total_time = time.time() - start_time
            print(f"\n🎉 เสร็จสิ้น crawl4ai Scraping!")
            print(f"⏱️  เวลาทั้งหมด: {total_time/60:.1f} นาที")
            print(f"📊 ประสิทธิภาพ: {len(dataset)/total_time:.1f} ไฟล์/วินาที")
            print(f"📁 ไฟล์ที่สร้าง: ratchakitcha_dataset.csv, .json ({len(dataset)} รายการ)")
            
            # แสดงตัวอย่าง
            print(f"\n📄 ตัวอย่างข้อมูล:")
            for i, item in enumerate(dataset[:2], 1):
                print(f"\n{i}. {item['title'][:60]}...")
                print(f"   ขนาด: {item['file_size']} bytes")
                if len(item['text']) > 100:
                    print(f"   ข้อความ: {item['text'][:80]}...")
        
    except KeyboardInterrupt:
        print("\n⏹️ หยุดการทำงานโดยผู้ใช้")
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
