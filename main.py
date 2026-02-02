import os
import csv
import random
import requests
import io
import google.generativeai as genai
from pypdf import PdfReader

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
CSV_FILE = "nccn_links.csv"

# --- STEP 1: DOWNLOADER & READER ---
def get_random_cancer_topic():
    """Reads the CSV and returns a random topic and URL."""
    try:
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = list(reader)
            if not data:
                return None, None
            selection = random.choice(data)
            return selection['topic'], selection['url']
    except FileNotFoundError:
        print("❌ Error: CSV file not found.")
        return None, None

def download_and_extract_pdf(url):
    """Downloads PDF from NCCN and extracts text."""
    print(f"📥 Downloading PDF from: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'} # Pretend to be a browser
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            print("✅ Download successful. Extracting text...")
            f = io.BytesIO(response.content)
            reader = PdfReader(f)
            
            # Extract text from the first 10 pages only (Title + Key Summaries)
            # We skip the rest to avoid token limits and irrelevant info
            text = ""
            max_pages = min(10, len(reader.pages)) 
            for i in range(max_pages):
                text += reader.pages[i].extract_text() + "\n"
            return text
        else:
            print(f"❌ Failed to download. Status Code: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error processing PDF: {e}")
        return None

# --- STEP 2: TRANSLATOR & WRITER (Formal Egyptian) ---
def write_medical_post(pdf_text, topic):
    print("✍️  Dr. AI is writing and translating...")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    You are a Senior Oncologist at 'Elite Oncology Clinic' in Egypt.
    
    SOURCE MATERIAL (Extracted from NCCN Patient Guidelines):
    {pdf_text[:15000]}  # Limit characters to avoid API errors
    
    TASK:
    Write a professional Facebook post about '{topic}' based ONLY on the text above.
    
    LANGUAGE REQUIREMENTS (STRICT):
    1. Language: **Modern Standard Arabic (Fusha)**.
    2. Tone: Professional, Warm, Reassuring. 
    3. **NO SLANG**: Do NOT use colloquial Egyptian words (e.g., avoid 'كده', 'عشان', 'دلوقتي'). 
       - Instead use: 'هكذا', 'من أجل', 'الآن'.
       - Use 'يجب' instead of 'لازم'.
       - Use 'نحن' instead of 'احنا'.
    4. Style: Use distinct headings and bullet points.
    
    POST STRUCTURE:
    1. **Headline**: Catchy and clear, no need to mention the topic in the headline, use subtopics from the guidelines.
    2. **Introduction**: A welcoming sentence.
    3. **Key Information**: Extract 3-4 vital facts/symptoms/treatments from the text.
    4. **Conclusion**: A hopeful closing statement.
    5. **Call to Action**: "For consultations, visit Elite Oncology Clinic."
    
    OUTPUT:
    Return only the Arabic post text.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Generation Error: {e}")
        return None

# --- STEP 3: POSTER ---
def post_to_facebook(content):
    if not content:
        return

    print(f"🚀 Publishing to Page ID: {FB_PAGE_ID}...")
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    payload = {
        "message": content,
        "access_token": FB_PAGE_ACCESS_TOKEN
    }
    
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print(f"✅ Success! Post Published. ID: {response.json().get('id')}")
        else:
            print(f"❌ Facebook API Error: {response.text}")
    except Exception as e:
        print(f"❌ Network Error: {e}")

# --- MAIN LOOP ---
if __name__ == "__main__":
    if not all([GEMINI_API_KEY, FB_PAGE_ACCESS_TOKEN, FB_PAGE_ID]):
        print("❌ Error: Missing API Keys.")
        exit(1)

    # 1. Get Topic
    topic, url = get_random_cancer_topic()
    if not topic:
        print("❌ No topics found in CSV.")
        exit(1)

    print(f"📋 Selected Topic: {topic}")
    
    # 2. Get Content (Download PDF)
    pdf_content = download_and_extract_pdf(url)
    
    # 3. Write & Post
    if pdf_content:
        post_content = write_medical_post(pdf_content, topic)
        if post_content:
            print("\n--- DRAFT ---")
            print(post_content)
            print("-------------\n")
            post_to_facebook(post_content)
        else:
            print("❌ Failed to generate post content.")
    else:
        print("❌ Failed to get PDF content. (Check URL in CSV)")