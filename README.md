# 🤖 Ratchakitcha PDF Scraper - MULTI OCR SUPPORT

ระบบดึงข้อมูล PDF จากเว็บไซต์ราชกิจจานุเบกษา (ratchakitcha.soc.go.th) ด้วย **Crawl4AI + Multi OCR** พร้อมฟีเจอร์ AI OCR หลายรูปแบบและการแบ่งข้อความยาวอัตโนมัติ

## 🏛️ Ratchakitcha Scraper - สำหรับเอกสารราชการไทย

โปรเจกต์นี้เป็น **Government Document Dataset Creator** ที่ออกแบบมาเฉพาะสำหรับเว็บไซต์ราชกิจจานุเบกษา! รองรับ **Multi-OCR Pipeline** และการประมวลผลเอกสารยาวแบบอัตโนมัติ

## ✨ ฟีเจอร์หลักทั้งหมด

- 🚀 **Crawl4AI + Windows Support**: แก้ไขปัญหา Event Loop สำหรับ Windows Python 3.13
- 🔗 **PDF Link Discovery**: ค้นหาลิ้งค์ PDF อัตโนมัติจากเว็บไซต์ราชกิจจานุเบกษา
- 📄 **Multi-OCR Pipeline**: รองรับ OCR หลายรูปแบบพร้อมกัน
- 🎯 **Smart Text Splitting**: แบ่งข้อความยาวเป็น chunks อัตโนมัติ (30,000 chars/chunk)
- 💾 **Dataset Export**: ส่งออกเป็น CSV และ JSON ตามมาตรฐาน Hugging Face
- 🧹 **Advanced Text Cleaning**: ทำความสะอาดข้อความพร้อมแก้ไข OCR errors
- ⚡ **Concurrent Processing**: ประมวลผลหลายไฟล์พร้อมกัน (ปรับได้ตามระบบ)
- 🛡️ **Error Handling**: จัดการ HTTP errors, timeouts, และ PDF corruption
- 📊 **Rich Metadata**: ข้อมูล metadata ครบถ้วนสำหรับแต่ละเอกสาร

### 🔥 ฟีเจอร์ใหม่ล่าสุด (เวอร์ชัน 2.0)

- 🤖 **Mistral OCR Integration** - OCR หลักด้วย Mistral OCR API (ความแม่นยำสูง)
- 💎 **DeepSeek Text Correction** - แก้ไขข้อผิดพลาดด้วย DeepSeek LLM (ประหยัด 70เท่า!)
- 📝 **PyThaiNLP Enhancement** - ตรวจสอบและแก้ไขคำผิดภาษาไทยอัตโนมัติ
- 📄 **Auto Text Chunking** - แบ่งเอกสารยาวเป็นหลาย rows อัตโนมัติ
- 🔢 **Smart ID System** - ระบบ ID แบบ 1, 1.1, 1.2 สำหรับ chunks
- 🎯 **Pattern-based OCR Fixes** - แก้ไขข้อผิดพลาด OCR ทั่วไป (เช่น ๒๕ะ๘ → ๒๕๖๘)
- 🏷️ **Document Classification** - จำแนกประเภทเอกสาร (พรบ., ประกาศ, กฎกระทรวง ฯลฯ)
- 🗄️ **Cache System** - ระบบ cache ป้องกันการ OCR ซ้ำ

## 🛠️ การติดตั้ง

### 1. **Clone Repository:**
```bash
git clone https://github.com/your-repo/ratchakitcha-scraper.git
cd ratchakitcha-scraper
```

### 2. **ติดตั้ง Dependencies:**
```bash
pip install -r requirements.txt
```

### 3. **ติดตั้ง Crawl4AI (สำหรับ Windows):**
```bash
pip install crawl4ai
crawl4ai-setup
```

### 4. **ตั้งค่า API Keys (.env):**
```bash
# สร้างไฟล์ .env
touch .env

# เพิ่ม API keys (อย่างน้อย 1 อัน)
echo "MISTRAL_API_KEY=your-mistral-api-key" >> .env
echo "DEEPSEEK_API_KEY=your-deepseek-api-key" >> .env
```

### 5. **ติดตั้ง PyThaiNLP (ถ้าต้องการ):**
```bash
pip install pythainlp
```

### 6. **ทดสอบการติดตั้ง:**
```bash
python -c "import crawl4ai; print('✅ Crawl4AI พร้อมใช้งาน')"
python -c "from mistralai import Mistral; print('✅ Mistral API พร้อมใช้งาน')"
python -c "import pythainlp; print('✅ PyThaiNLP พร้อมใช้งาน')"
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

## 🤖 Multi-OCR Pipeline สำหรับ PDF ภาษาไทย

### 1. **Mistral OCR (หลัก):**
- ใช้ Mistral OCR API ความแม่นยำสูง
- รองรับ PDF หลายรูปแบบ
- ประมวลผลรวดเร็ว

### 2. **DeepSeek Text Correction:**
- แก้ไขข้อผิดพลาดจาก OCR อัตโนมัติ
- ใช้ LLM ในการแก้ไขบริบท
- ประหยัดค่าใช้จ่าย 70เท่าเทียบกับ GPT-4

### 3. **PyThaiNLP Enhancement:**
- ตรวจสอบและแก้ไขคำผิดภาษาไทย
- Pattern-based OCR fixes
- แก้ไขตัวเลขไทยที่ OCR ผิด (เช่น ๒๕ะ๘ → ๒๕๖๘)

### การเลือกใช้ OCR:
```bash
# เมื่อรันโปรแกรม
🔗 API Status:
💎 DeepSeek API: ✅ พร้อมใช้งาน (ประหยัด 70เท่า!)
🤖 Mistral API: ✅ พร้อมใช้งาน
📝 PyThaiNLP: ✅ พร้อมใช้งาน

🤔 ต้องการใช้ PyThaiNLP แก้ไขคำผิด? (y/N): y
```

## 📊 รูปแบบ Dataset ใหม่

Dataset ที่ได้จะมีรูปแบบสมบูรณ์:

### สำหรับเอกสารปกติ:
```csv
id,url,title,text,filename,found_on_page,file_size,content_type,created_at,metadata
1,https://ratchakitcha.soc.go.th/documents/12345.pdf,พระราชบัญญัติ...,เนื้อหาจาก OCR...,12345.pdf,https://ratchakitcha.soc.go.th,1234567,application/pdf,2024-01-01T10:00:00,{...}
```

### สำหรับเอกสารยาวที่แบ่งเป็น chunks:
```csv
id,url,title,text,filename,found_on_page,file_size,content_type,created_at,metadata
2.1,https://ratchakitcha.soc.go.th/documents/67890.pdf,เอกสารยาว (ส่วนที่ 1/3),ส่วนแรกของเอกสาร...,67890.pdf,https://ratchakitcha.soc.go.th,7890123,application/pdf,2024-01-01T10:05:00,{...}
2.2,https://ratchakitcha.soc.go.th/documents/67890.pdf,เอกสารยาว (ส่วนที่ 2/3),ส่วนกลางของเอกสาร...,67890.pdf,https://ratchakitcha.soc.go.th,7890123,application/pdf,2024-01-01T10:05:00,{...}
2.3,https://ratchakitcha.soc.go.th/documents/67890.pdf,เอกสารยาว (ส่วนที่ 3/3),ส่วนท้ายของเอกสาร...,67890.pdf,https://ratchakitcha.soc.go.th,7890123,application/pdf,2024-01-01T10:05:00,{...}
```

### Metadata ที่รวมอยู่:
```json
{
  "processing": {
    "ocr_success": true,
    "ocr_engine": "mistral-ocr-latest",
    "text_correction": "pythainlp+deepseek",
    "text_length_cleaned": 25000
  },
  "file_info": {
    "file_size_mb": 2.5,
    "document_id": "12345"
  },
  "text_analysis": {
    "word_count": 3500,
    "character_count": 25000,
    "document_type": "พระราชบัญญัติ",
    "buddhist_year": "2567",
    "keywords": ["การศึกษา", "พัฒนา", "คุณภาพ"],
    "is_chunk": false
  }
}
```

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
- **Mistral AI**: สำหรับ OCR API ที่มีประสิทธิภาพสูง
- **DeepSeek**: สำหรับ LLM text correction ราคาประหยัด
- **PyThaiNLP**: สำหรับการประมวลผลภาษาไทย
- **BeautifulSoup**: สำหรับ HTML parsing เสริม
- **Pandas**: สำหรับจัดการ DataFrame
- **aiofiles**: สำหรับ async file operations

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

### การทำงานของระบบใหม่:

1. **🔍 Discovery Phase**: สแกนเว็บไซต์หาลิ้งค์ PDF ทั้งหมดด้วย Crawl4AI (แก้ไขปัญหา Windows)
2. **⚡ Concurrent Processing**: ดาวน์โหลดและประมวลผลพร้อมกัน (ปรับได้ตามระบบ)
3. **📄 Multi-OCR Text Extraction**: 
   - **Mistral OCR** (หลัก): อ่าน PDF ด้วย AI OCR ความแม่นยำสูง
   - **DeepSeek Text Correction**: แก้ไขข้อผิดพลาดด้วย LLM (ประหยัด 70เท่า!)
   - **PyThaiNLP Enhancement**: แก้ไขคำผิดภาษาไทยและ OCR errors
4. **🧹 Advanced Text Cleaning**: 
   - ลบ markdown elements และ artifacts
   - แก้ไขตัวเลขไทยที่ OCR ผิด (๒๕ะ๘ → ๒๕๖๘)
   - Pattern-based OCR fixes
5. **📄 Smart Text Chunking**: แบ่งข้อความยาว (>30,000 chars) เป็นหลาย rows อัตโนมัติ
6. **🏷️ Document Analysis**: จำแนกประเภทเอกสาร, ดึงปี พ.ศ., keywords
7. **💾 Export**: บันทึกเป็น CSV และ JSON พร้อม metadata ครบถ้วน

### ตัวอย่างผลลัพธ์จาก Multi-OCR:
```
พระราชบัญญัติการศึกษาแห่งชาติ พ.ศ. ๒๕๖๗

หมวด ๑ บททั่วไป 
มาตรา ๓ ในพระราชบัญญัตินี้ "การศึกษา" หมายความว่า กระบวนการเรียนรู้
เพื่อความเจริญงอกงามของบุคคลและสังคม โดยการถ่ายทอดความรู้ การฝึก 
อบรม การปฏิบัติ การศึกษาค้นคว้า การแลกเปลี่ยนเรียนรู้ การสืบสาน
ประเพณี และวัฒนธรรม การสร้างสรรค์งานศิลปกรรม การพัฒนาทักษะ 
การประกอบอาชีพ และการพัฒนาคุณภาพชีวิต

มาตรา ๔ การจัดการศึกษาต้องเป็นไปเพื่อพัฒนาคนไทยให้เป็นมนุษย์ที่สมบูรณ์
ทั้งร่างกาย จิตใจ สติปัญญา ความรู้ และคุณธรรม มีจริยธรรมและวัฒนธรรม
ในการดำรงชีวิต สามารถอยู่ร่วมกับผู้อื่นได้อย่างมีความสุข
```

### ไฟล์ที่จะได้:
- `ratchakitcha_dataset.csv` - Dataset ครบถ้วนพร้อม chunks
- `ratchakitcha_dataset.json` - Dataset ในรูปแบบ JSON พร้อม metadata
- `cache/` - โฟลเดอร์ cache สำหรับ OCR results (ประหยัดเวลา)

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
