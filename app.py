import streamlit as st
import google.generativeai as genai
import requests
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi 

# ==========================================
# ⚙️ 1. ตั้งค่าหน้าเว็บ (ต้องอยู่บรรทัดแรกสุด)
# ==========================================
st.set_page_config(
    page_title="เฮียยอน AI Station",
    page_icon="⚽",
    layout="wide"
)

# ==========================================
# 🔐 2. ดึงค่าความลับ (Secrets)
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    WP_URL = st.secrets["WP_URL"]
    WP_USER = st.secrets["WP_USER"]
    WP_APP_PASSWORD = st.secrets["WP_APP_PASSWORD"]
    APP_PASSWORD = st.secrets["APP_PASSWORD"] # รหัสเข้า App

    # ใช้ตัว 2.5 Flash ตามที่ตกลงกัน
    MODEL_NAME = "models/gemini-2.5-flash" 
except FileNotFoundError:
    st.error("❌ ไม่เจอไฟล์ Secrets! กรุณาตั้งค่า API Key ก่อนเริ่มใช้งาน")
    st.stop()
except KeyError as e:
    st.error(f"❌ ตั้งค่า Secrets ไม่ครบ: ขาดตัวแปร {e}")
    st.stop()

# ==========================================
# 🔒 3. ระบบป้องกัน (Login)
# ==========================================
def check_password():
    """Returns `True` if the user had the correct password."""
    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 ห้องลับเฮียยอน Morroc")
    st.write("กรุณาใส่รหัสผ่านเพื่อเข้าใช้งานระบบ")

    password_input = st.text_input("Password", type="password")

    if st.button("เข้าสู่ระบบ"):
        if password_input == APP_PASSWORD:
            st.session_state["password_correct"] = True
            st.rerun()  
        else:
            st.error("❌ รหัสผิด! ไปเดามาใหม่นะไอ้น้อง")
    return False

if not check_password():
    st.stop()

# ==========================================
# 🛠️ 4. ฟังก์ชันและเครื่องมือ (Tools)
# ==========================================
def convert_to_thai_date(date_obj):
    """แปลงวันที่เป็นภาษาไทย"""
    if not date_obj: return ""
    thai_months = [
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    year_th = date_obj.year + 543
    return f"{date_obj.day} {thai_months[date_obj.month - 1]} {year_th}"

def extract_video_id(url):
    """แกะ ID จากลิงก์ YouTube"""
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1]
    return None

def get_transcripts_from_links(links_text):
    """รับลิงก์หลายบรรทัด แล้วไปดูดซับมาต่อกัน"""
    if not links_text.strip():
        return ""
    
    urls = links_text.strip().split('\n')
    combined_transcript = ""
    
    for url in urls:
        if not url.strip(): continue
        video_id = extract_video_id(url)
        if video_id:
            try:
                # พยายามดึงซับไทยก่อน ถ้าไม่มีเอาอังกฤษ
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['th', 'en'])
                # เอาแค่ 2000 ตัวอักษรแรกต่อคลิป พอกรุบกริบ (กัน Token เต็ม)
                text = " ".join([t['text'] for t in transcript_list])
                combined_transcript += f"\n[สรุปเกมจากคลิป {url}]: {text[:2000]}..." 
            except Exception as e:
                combined_transcript += f"\n[คลิป {url} ดึงข้อมูลไม่ได้ (อาจไม่มีซับ): {e}]"
                
    return combined_transcript

# ==========================================
# 🖥️ 5. ส่วนหน้าจอใช้งาน (UI)
# ==========================================
st.title("⚽ เฮียยอน AI Station (Project: yrongemapi)")
st.caption("ระบบวิเคราะห์บอล AI Gen 2.5 Flash + YouTube Analysis ส่งตรงเข้า WordPress")
st.markdown("---")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        match_date_input = st.date_input("📅 วันที่แข่งขัน", datetime.now())
        match_date = convert_to_thai_date(match_date_input)
    with col2:
        match_time = st.text_input("⏰ เวลาแข่งขัน (เช่น 02:00 น.)", "02:00 น.")

    st.info(f"📌 ข้อมูลที่จะใช้ในบทความ: **{match_date} เวลา {match_time}**")

    # --- ส่วนที่ 1: รูปภาพ ---
    st.markdown("### 📸 1. ข้อมูลรูปภาพ (สถิติหลัก)")
    uploaded_files = st.file_uploader(
        "อัปโหลด 4 รูป: Win Prob / เหย้า / เยือน / Head to Head", 
        type=['png', 'jpg', 'jpeg'], 
        accept_multiple_files=True
    )

    # --- ส่วนที่ 2: YouTube ---
    st.markdown("### 📺 2. ข้อมูลคลิปย้อนหลัง (YouTube Link)")
    st.caption("แปะลิงก์ YouTube ไฮไลท์ (บรรทัดละ 1 ลิงก์) ระบบจะอ่านคำบรรยายไปวิเคราะห์ให้")
    
    col_yt1, col_yt2 = st.columns(2)
    with col_yt1:
        st.markdown("**ไฮไลท์ 5 นัดหลัง (เจ้าบ้าน)**")
        home_yt_links = st.text_area("YouTube เจ้าบ้าน", height=100, placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...")
    with col_yt2:
        st.markdown("**ไฮไลท์ 5 นัดหลัง (ทีมเยือน)**")
        away_yt_links = st.text_area("YouTube ทีมเยือน", height=100, placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...")

    # --- ส่วนที่ 3: รูปแทรกบทความ ---
    st.markdown("### 🔗 3. รูปสำหรับแทรกในบทความ (กราฟิก)")
    col_img1, col_img2 = st.columns(2)
    with col_img1:
        img4_url = st.text_input("🔗 Link รูปที่ 4 (แทรกเจ้าบ้าน)", placeholder="https://morroc.net/wp-content/...")
    with col_img2:
        img5_url = st.text_input("🔗 Link รูปที่ 5 (แทรกทีมเยือน)", placeholder="https://morroc.net/wp-content/...")

# ==========================================
# 🚀 6. ปุ่มรันและการทำงานหลัก
# ==========================================
if st.button("🚀 วิเคราะห์และส่งบทความ (Start)", type="primary"):
    if len(uploaded_files) < 4:
        st.warning("⚠️ อัปรูปให้ครบ 4 ใบก่อนลูกพี่! (Win Prob, เหย้า, เยือน, H2H)")
    else:
        status_box = st.status("กำลังร่ายมนตร์เฮียยอน...", expanded=True)
        
        try:
            # --- Step 1: เตรียมรูปภาพ ---
            status_box.write("📸 กำลังแปลงไฟล์รูปภาพ...")
            contents_to_send = []
            # ใช้แค่ 4 รูปแรกที่อัปโหลดมา (ตามลำดับ)
            for up_file in uploaded_files[:4]:
                bytes_data = up_file.getvalue()
                contents_to_send.append({"mime_type": "image/jpeg", "data": bytes_data})

            # --- Step 2: เตรียมข้อมูล YouTube ---
            status_box.write("📺 กำลังดูดข้อมูลจาก YouTube...")
            home_transcript = get_transcripts_from_links(home_yt_links)
            away_transcript = get_transcripts_from_links(away_yt_links)
            
            youtube_context = f"""
            **ข้อมูลเสริมจากคำบรรยายคลิปไฮไลท์ 5 นัดหลัง:**
            [ฝั่งเจ้าบ้าน]: {home_transcript}
            [ฝั่งทีมเยือน]: {away_transcript}
            """

            # --- Step 3: เตรียม Prompt (โหลดจาก Secrets) ---
            status_box.write("🧠 กำลังเรียบเรียง Prompt เทพๆ...")

            # โหลด Prompt จาก secrets.toml
            raw_prompt = st.secrets["prompts"]["football_analysis_template"]
            PROMPT_TEMPLATE = raw_prompt.replace("{match_date}", match_date).replace("{match_time}", match_time)
            
            # รวม Prompt + YouTube Context
            full_prompt_text = PROMPT_TEMPLATE + "\n\n" + youtube_context
            
            # รวมร่าง Prompt + รูป ส่งให้ AI
            full_payload = [full_prompt_text] + contents_to_send

            # --- Step 4: ส่งให้ Gemini ---
            status_box.write(f"🧠 กำลังปลุกเฮียยอน ({MODEL_NAME})...")
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(MODEL_NAME)
            
            generation_config = genai.types.GenerationConfig(
                temperature=1.2,
                top_p=0.95,
                top_k=60,
                max_output_tokens=8192
            )

            response = model.generate_content(
                full_payload,
                generation_config=generation_config
            )
            
            # --- Step 5: ระบบเสียบรูป (Image Injection) ---
            status_box.write("🔧 กำลังประกอบร่างบทความ...")
            final_content = response.text

            # แทนที่รูปที่ 4 (เจ้าบ้าน) - ใช้คำว่า [แทรกรูปเจ้าบ้าน] ให้ตรงกับ Prompt มาตรฐาน
            if img4_url:
                html_img4 = f'<div class="wp-block-image"><figure class="aligncenter"><img src="{img4_url}" alt="สถิติเจ้าบ้าน วิเคราะห์บอล" /></figure></div>'
                final_content = final_content.replace("[แทรกรูปเจ้าบ้าน]", html_img4)
            else:
                final_content = final_content.replace("[แทรกรูปเจ้าบ้าน]", "")

            # แทนที่รูปที่ 5 (ทีมเยือน) - ใช้คำว่า [แทรกรูปทีมเยือน]
            if img5_url:
                html_img5 = f'<div class="wp-block-image"><figure class="aligncenter"><img src="{img5_url}" alt="สถิติทีมเยือน วิเคราะห์บอล" /></figure></div>'
                final_content = final_content.replace("[แทรกรูปทีมเยือน]", html_img5)
            else:
                final_content = final_content.replace("[แทรกรูปทีมเยือน]", "")

            # --- Step 6: ส่งเข้า WordPress ---
            status_box.write("🚀 กำลังยิงบทความขึ้นเว็บ Morroc.net...")
            
            # แยกหัวข้อ Title ออกจากเนื้อหา Content
            lines = final_content.split('\n')
            post_title = "วิเคราะห์บอล (Auto Draft)" 
            content_start_index = 0
            
            for i, line in enumerate(lines):
                if line.startswith("Title:"):
                    post_title = line.replace("Title:", "").strip()
                    content_start_index = i + 1
                    break
            
            post_content = "\n".join(lines[content_start_index:]).strip()

            # ยิง API WordPress
            auth = (WP_USER, WP_APP_PASSWORD)
            headers = {"Content-Type": "application/json"}
            data = { 
                "title": post_title, 
                "content": post_content, 
                "status": "draft" 
            }
            
            wp_res = requests.post(WP_URL, json=data, auth=auth, headers=headers)
            
            if wp_res.status_code == 201:
                link = wp_res.json().get('link')
                status_box.update(label="✅ ภารกิจสำเร็จ! บทความขึ้นเว็บแล้ว", state="complete", expanded=False)
                st.balloons()
                st.success(f"**เรียบร้อยลูกพี่!** บทความวันที่ {match_date} ถูกส่งไปแล้ว")
                st.markdown(f"👉 **คลิกตรวจงานได้ที่นี่:** [{link}]({link})")
                
                with st.expander("ดู Code HTML ที่ส่งไป"):
                    st.code(post_content, language='html')
                    
            else:
                status_box.update(label="❌ ส่ง WordPress ไม่ผ่าน", state="error")
                st.error(f"Error Code: {wp_res.status_code}")
                st.code(wp_res.text)

        except Exception as e:
            status_box.update(label="❌ เกิดข้อผิดพลาด", state="error")
            st.error(f"Error: {e}")
            if "503" in str(e):
                st.warning("💡 Server Google แน่นครับ รอสัก 1 นาทีแล้วกดปุ่มใหม่นะ")
            if "429" in str(e):
                st.warning("💡 โควตาเต็มหรือยิงถี่ไปครับ พักแป๊บนึง")