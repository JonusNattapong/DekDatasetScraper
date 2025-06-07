# 🤖 Crawl4AI Dataset Scraper with AI-Powered OCR

ระบบดึงข้อมูลเว็บไซต์อัตโนมัติด้วย Crawl4AI เพื่อสร้าง Dataset ในรูปแบบ CSV และ JSON พร้อมฟีเจอร์ AI OCR สำหรับ PDF ภาษาไทย

## 🏛️ เพิ่มเติม: Ratchakitcha Scraper with Qwen2-VL-OCR

โปรเจกต์นี้รวม **Ratchakitcha Scraper** สำหรับดึงข้อมูล PDF จากเว็บไซต์ราชกิจจานุเบกษา (ratchakitcha.soc.go.th) โดยเฉพาะ! **ตอนนี้รองรับ AI OCR ด้วย Qwen2-VL-OCR-2B-Instruct สำหรับ PDF ภาษาไทยที่มีปัญหาการเข้ารหัส**

## ✨ ฟีเจอร์หลัก

- 🚀 **ใช้ Crawl4AI**: ประสิทธิภาพสูง รวดเร็วกว่า Traditional scraping 6x
- 🔗 **ดึงลิ้งค์อัตโนมัติ**: ค้นหาและดึงลิ้งค์จากหน้าเว็บได้อย่างชาญฉลาด
- 📄 **สร้าง Dataset**: แปลงเนื้อหาเป็น Dataset รูปแบบ `id,url,title,text`
- 🎯 **กรองข้อมูล**: ใช้ keywords ในการกรองเนื้อหาที่ต้องการ
- 💾 **Export หลายรูปแบบ**: บันทึกเป็น CSV และ JSON
- 🌏 **รองรับภาษาไทย**: ออกแบบมาสำหรับเว็บไซต์ไทยโดยเฉพาะ

### 🔥 ฟีเจอร์ใหม่: Ratchakitcha Scraper

- 🔍 **ค้นหาลิ้งค์ PDF อัตโนมัติ** - สแกนเว็บไซต์ราชกิจจานุเบกษาหาลิ้งค์ PDF ทั้งหมด
- 📄 **ดึงเนื้อหาจาก PDF** - ใช้ AI OCR ด้วย Qwen2-VL-OCR เท่านั้น
- 🤖 **AI OCR ด้วย Qwen2-VL-OCR** - อ่าน PDF ภาษาไทยผ่าน Vision Language Model
- ⚡ **ประมวลผลแบบ Concurrent** - ดาวน์โหลดหลายไฟล์พร้อมกัน
- 📊 **Export หลายรูปแบบ** - บันทึกเป็น CSV และ JSON
- 🏷️ **รูปแบบ Dataset ตาม Hugging Face** - id, url, title, text
- 🛡️ **จัดการ Error** - รองรับ HTTP 403/404 และ timeout
- 📷 **PDF to Image OCR** - แปลง PDF เป็นรูปภาพแล้วใช้ AI อ่านข้อความ

## 🛠️ การติดตั้ง

1. **ติดตั้ง dependencies:**
```bash
pip install -r requirements.txt
```

2. **ติดตั้ง Crawl4AI และตั้งค่า browser:**
```bash
pip install crawl4ai
crawl4ai-setup
```

3. **สำหรับ OCR (ถ้าต้องการ):**
```bash
# ติดตั้ง dependencies สำหรับ OCR
pip install torch torchvision transformers pdf2image pillow qwen-vl-utils

# สำหรับ Windows ติดตั้ง poppler
# Download poppler-utils และเพิ่มใน PATH
# หรือใช้ conda: conda install poppler
```

4. **ทดสอบการติดตั้ง:**
```bash
python -c "import crawl4ai; print('✅ Crawl4AI พร้อมใช้งาน')"
python -c "import torch; print('✅ PyTorch พร้อมใช้งาน')"
```

## 🎮 วิธีการใช้งาน

### รันโปรแกรมหลัก
```bash
python main.py
```

### รัน Ratchakitcha Scraper พร้อม AI OCR
```bash
python ratchakitcha_scraper.py
```

### โหมดการทำงาน 3 แบบ:

#### 1. 🚀 สแกนเว็บไซต์อัตโนมัติ
- ดึงลิ้งค์จากหน้าหลัก
- สแกนเนื้อหาจากแต่ละลิ้งค์
- สร้าง Dataset อัตโนมัติ

```python
# ตัวอย่างการใช้งานในโค้ด
scraper = Crawl4AiDatasetScraper()
dataset = await scraper.auto_scrape_website(
    start_url="https://ratchakitcha.soc.go.th",
    max_pages=20,
    keywords=["กฎหมาย", "พระราชบัญญัติ"]
)
```

#### 2. 🔗 ดึงลิ้งค์จากหน้าเดียว
- วิเคราะห์และดึงลิ้งค์ทั้งหมดจากหน้าเว็บ
- แสดงรายการลิ้งค์และหัวข้อ

#### 3. 📄 ดึงเนื้อหาจาก URL เดียว
- ดึงเนื้อหาจาก URL ที่กำหนด
- แปลงเป็น Dataset format

## 🤖 AI OCR สำหรับ PDF ภาษาไทย

### วิธีการทำงานของ Qwen2-VL-OCR:

1. **ดาวน์โหลด PDF** - ดึงไฟล์ PDF จาก URL
2. **แปลงเป็นรูปภาพ** - ใช้ pdf2image แปลง PDF เป็นรูปภาพ (DPI 200)
3. **ใช้ AI OCR** - Qwen2-VL-OCR-2B-Instruct อ่านข้อความจากรูปภาพแต่ละหน้า
4. **ประมวลผลผลลัพธ์** - รวมข้อความทุกหน้าและจัดรูปแบบ

### ตัวเลือกการใช้งาน:
```bash
# เมื่อรันโปรแกรม จะถามว่าต้องการใช้ OCR หรือไม่
ต้องการใช้ Qwen2-VL-OCR หรือไม่? (y/N): y

# ถ้าเลือก y จะโหลด AI model และใช้ OCR สำหรับ PDF ที่มีปัญหา
# ถ้าเลือก N จะใช้วิธีปกติเท่านั้น
```

## 📊 รูปแบบ Dataset

Dataset ที่ได้จะมีรูปแบบดังนี้:

```csv
id,url,title,text
1,https://example.com/page1,หัวข้อหน้าแรก,"เนื้อหาทั้งหมดของหน้าเว็บ..."
2,https://example.com/page2,หัวข้อหน้าที่สอง,"เนื้อหาทั้งหมดของหน้าเว็บ..."
```

### คอลัมน์ข้อมูล:
- **id**: หมายเลขลำดับ
- **url**: URL ของหน้าเว็บ
- **title**: หัวข้อของหน้า
- **text**: เนื้อหาทั้งหมด (markdown format)

## 🎯 ตัวอย่างการใช้งานขั้นสูง

### การปรับแต่ง Browser Config
```python
browser_config = BrowserConfig(
    headless=True,          # รันแบบไม่แสดงหน้าต่าง
    verbose=True,           # แสดงรายละเอียดการทำงาน
    browser_type="chromium" # ใช้ Chromium browser
)
```

### การปรับแต่ง Crawler Config
```python
run_config = CrawlerRunConfig(
    cache_mode=CacheMode.ENABLED,      # เปิดใช้งาน cache
    word_count_threshold=10,           # ข้ามหน้าที่มีคำน้อยกว่า 10 คำ
    wait_for_images=True,              # รอให้รูปภาพโหลดเสร็จ
    delay_before_return_html=2.0,      # รอ 2 วินาทีก่อนดึงข้อมูล
    timeout=30                         # Timeout 30 วินาที
)
```

## 🔧 การปรับแต่งขั้นสูง

### กรองลิ้งค์ด้วย Custom Pattern
```python
# แก้ไขใน method _is_valid_link()
invalid_patterns = [
    r'^#',                     # ลิ้งค์ภายในหน้า
    r'^javascript:',           # JavaScript links
    r'^mailto:',               # Email links
    r'\.(pdf|doc|docx)$',     # ไฟล์เอกสาร
    r'/(admin|login)/',       # หน้า admin/login
]
```

### กรองด้วย Keywords
```python
keywords = ["พระราชบัญญัติ", "กฎหมาย", "ประกาศ"]
dataset = await scraper.auto_scrape_website(
    start_url="https://ratchakitcha.soc.go.th",
    max_pages=50,
    keywords=keywords
)
```

## 📁 ไฟล์ที่จะได้

- `auto_scraped_dataset.csv` - Dataset ในรูปแบบ CSV
- `auto_scraped_dataset.json` - Dataset ในรูปแบบ JSON
- `single_page_dataset.csv` - Dataset จากหน้าเดียว

## ⚠️ ข้อควรระวัง

1. **ความเร็วในการ Scrape**: มี delay 1 วินาทีระหว่างหน้าเพื่อไม่ให้เซิร์ฟเวอร์โหลดหนัก
2. **Timeout**: หน้าที่โหลดนานเกิน 30 วินาทีจะถูกข้าม
3. **Memory Usage**: การ scrape หน้าจำนวนมากอาจใช้ RAM มาก
4. **Robots.txt**: ควรตรวจสอบ robots.txt ของเว็บไซต์ก่อนใช้งาน
5. **AI OCR**: ใช้ GPU/CPU มากขึ้น และใช้เวลานานกว่า

## 🚨 การแก้ไขปัญหาที่พบบ่อย

### ปัญหา: ไม่สามารถติดตั้ง Crawl4AI
```bash
# ลองติดตั้งด้วย pre-release version
pip install crawl4ai --pre

# หรือติดตั้ง browser manually
python -m playwright install chromium
```

### ปัญหา: Browser ไม่เริ่มต้น
```bash
# รัน setup อีกครั้ง
crawl4ai-setup

# ตรวจสอบการติดตั้ง
crawl4ai-doctor
```

### ปัญหา: OCR ไม่ทำงาน
```bash
# ตรวจสอบ PyTorch
python -c "import torch; print(torch.cuda.is_available())"

# ติดตั้ง poppler สำหรับ pdf2image
# Windows: ดาวน์โหลดจาก https://poppler.freedesktop.org/
# macOS: brew install poppler
# Linux: apt-get install poppler-utils
```

### ปัญหา: ดึงข้อมูลไม่ได้
- ตรวจสอบ URL ว่าถูกต้อง
- ลองปรับ `delay_before_return_html` ให้มากขึ้น
- เช็คว่าเว็บไซต์ไม่ได้บล็อก bot

## 🤝 การมีส่วนร่วม

หากต้องการปรับปรุงหรือเพิ่มฟีเจอร์:

1. Fork repository นี้
2. สร้าง feature branch
3. ทำการเปลี่ยนแปลง
4. Submit Pull Request

## 📝 License

โปรเจกต์นี้ใช้ MIT License - ดูรายละเอียดในไฟล์ LICENSE

## 🙏 Credits

- **Crawl4AI**: Framework หลักที่ใช้ในการ web crawling
- **Qwen2-VL-OCR-2B-Instruct**: AI model สำหรับ OCR ภาษาไทย
- **BeautifulSoup**: สำหรับ HTML parsing เสริม
- **Pandas**: สำหรับจัดการ DataFrame
- **aiofiles**: สำหรับ async file operations
- **pdf2image & pdfplumber**: สำหรับจัดการ PDF

## 🏛️ Ratchakitcha Scraper - เฉพาะสำหรับราชกิจจานุเบกษา

### การใช้งาน Ratchakitcha Scraper:

```bash
# รันการค้นหา PDF ทั้งหมดจากเว็บไซต์ราชกิจจานุเบกษา
python ratchakitcha_scraper.py

# ทดสอบระบบ
python test_ratchakitcha.py

# ทดสอบแบบเต็ม (รวมการค้นหาจริง)
python test_ratchakitcha.py full
```

### ตัวอย่างการใช้งานในโค้ด:
```python
from ratchakitcha_scraper import RatchakitchaScraper

async def main():
    scraper = RatchakitchaScraper()
    
    # เลือกใช้ OCR หรือไม่
    await scraper.ocr.initialize()  # สำหรับ OCR
    # หรือ scraper.ocr = None      # ไม่ใช้ OCR
    
    # ค้นหาลิ้งค์ PDF ทั้งหมด
    pdf_links = await scraper.discover_pdf_links()
    
    # สร้าง Dataset (concurrent processing)
    dataset = await scraper.create_dataset(pdf_links, concurrent_limit=10)
    
    # บันทึกไฟล์
    await scraper.save_dataset_to_csv(dataset, "ratchakitcha_dataset.csv")
    await scraper.save_dataset_to_json(dataset, "ratchakitcha_dataset.json")
```

### รูปแบบ Dataset ที่ได้จาก Ratchakitcha:
```csv
id,url,title,text,filename,found_on_page,file_size,content_type,last_modified,created_at
1,https://ratchakitcha.soc.go.th/documents/72675.pdf,พระราชบัญญัติ...,เนื้อหาจาก PDF หรือ OCR...,72675.pdf,https://ratchakitcha.soc.go.th,1234567,application/pdf,Mon 01 Jan 2024,2024-01-01T10:00:00
```

### การทำงานของระบบ:

1. **🔍 Discovery Phase**: สแกนเว็บไซต์หาลิ้งค์ PDF ทั้งหมด
2. **⚡ Concurrent Processing**: ดาวน์โหลดและประมวลผลพร้อมกัน
3. **📄 Text Extraction**: 
   - ใช้ Qwen2-VL-OCR เท่านั้น (ไม่ใช้ traditional PDF text extraction)
   - แปลง PDF เป็นรูปภาพแล้วใช้ AI อ่านข้อความ
4. **🧹 Text Cleaning**: ทำความสะอาดข้อความ
5. **💾 Export**: บันทึกเป็น CSV และ JSON

### ตัวอย่างผลลัพธ์จาก OCR:
```
=== หน้า 1 ===
พระราชบัญญัติการศึกษาแห่งชาติ พ.ศ. ๒๕๖๒

หมวด ๑ บททั่วไป
มาตรา ๓ ในพระราชบัญญัตินี้
"การศึกษา" หมายความว่า กระบวนการเรียนรู้เพื่อความเจริญงอกงาม
ของบุคคลและสังคม

=== หน้า 2 ===
มาตรา ๔ การจัดการศึกษาต้องเป็นไปเพื่อพัฒนาคนไทย
ให้เป็นมนุษย์ที่สมบูรณ์ทั้งร่างกาย จิตใจ สติปัญญา
ความรู้ และคุณธรรม
```

### ไฟล์ที่จะได้:
- `ratchakitcha_dataset.csv` - Dataset รายการ PDF ทั้งหมด
- `ratchakitcha_dataset.json` - Dataset ในรูปแบบ JSON
- `test_ratchakitcha_dataset.csv` - ไฟล์ทดสอบ

### คำสั่งทดสอบ:
```bash
python test_ratchakitcha.py pattern    # ทดสอบการหา URL pattern
python test_ratchakitcha.py metadata   # ทดสอบการดึง metadata PDF
python test_ratchakitcha.py dataset    # ทดสอบการสร้าง Dataset
python test_ratchakitcha.py discover   # ทดสอบการค้นหา PDF จริง
```

### ประสิทธิภาพ:
- **ไม่ใช้ OCR**: ~1,500 PDF ใน 12-15 นาที
- **ใช้ OCR**: ช้าลง 3-5 เท่า แต่ได้ข้อความที่ถูกต้องมากกว่า
- **Concurrent**: ประมวลผลพร้อมกัน 5-15 ไฟล์ (ปรับได้)

---

💡 **เคล็ดลับ**: เริ่มต้นด้วยการทดสอบหน้าเดียวก่อน แล้วค่อยขยายไปยังการ scrape หลายหน้า!

🎯 **สำหรับ Ratchakitcha**: รัน `python test_ratchakitcha.py` เพื่อทดสอบการทำงานก่อนใช้งานจริง!

🤖 **AI OCR**: เหมาะสำหรับ PDF ที่สแกนจากเอกสารกระดาษหรือมีปัญหาการเข้ารหัสภาษาไทย
