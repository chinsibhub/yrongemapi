import streamlit as st
import google.generativeai as genai
import requests
from PIL import Image
from datetime import datetime

# ==========================================
# 🔐 2. ดึงค่าความลับ (Secrets)
# ==========================================
# ระบบจะอ่านจากไฟล์ .streamlit/secrets.toml (ในคอม) หรือ Secrets Management (บน Cloud)
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    WP_URL = st.secrets["WP_URL"]
    WP_USER = st.secrets["WP_USER"]
    WP_APP_PASSWORD = st.secrets["WP_APP_PASSWORD"]

    # ใช้ตัว 2.5 Flash ตามที่ตกลงกัน (หรือจะเปลี่ยนเป็น models/gemini-2.0-flash-exp ก็ได้)
    MODEL_NAME = "models/gemini-2.5-flash" 
except FileNotFoundError:
    st.error("❌ ไม่เจอไฟล์ Secrets! กรุณาตั้งค่า API Key ก่อนเริ่มใช้งาน")
    st.stop()
except KeyError as e:
    st.error(f"❌ ตั้งค่า Secrets ไม่ครบ: ขาดตัวแปร {e}")
    st.stop()
# ==========================================
# 🔒 0. ระบบป้องกัน (Login)
# ==========================================
def check_password():
    """Returns `True` if the user had the correct password."""

    # 1. เช็กว่าล็อกอินผ่านหรือยัง ถ้าผ่านแล้วก็คืนค่า True เลย
    if st.session_state.get("password_correct", False):
        return True

    # 2. ถ้ายังไม่ผ่าน ให้โชว์ช่องใส่รหัส
    st.set_page_config(page_title="เฮียยอน Morroc - Login", page_icon="🔒")
    st.title("🔒 ห้องลับเฮียยอน Morroc")
    st.write("กรุณาใส่รหัสผ่านเพื่อเข้าใช้งานระบบ")

    password_input = st.text_input("Password", type="password")

    if st.button("เข้าสู่ระบบ"):
        # เช็กกับค่าใน secrets.toml
        if password_input == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()  # รีเฟรชหน้าจอเพื่อเข้าหน้าหลัก
        else:
            st.error("❌ รหัสผิด! ไปเดามาใหม่นะไอ้น้อง")

    return False

# ถ้ายังไม่ล็อกอิน ให้หยุดการทำงานตรงนี้ (ไม่โหลดโค้ดส่วนอื่น)
if not check_password():
    st.stop()
# ==========================================
# ⚙️ 1. ตั้งค่าหน้าเว็บ
# ==========================================
st.set_page_config(
    page_title="Hia Yon AI Station",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ เฮียยอน AI Station (Project: yrongemapi)")
st.caption("ระบบวิเคราะห์บอล AI Gen 2.5 Flash ส่งตรงเข้า WordPress")


# ==========================================
# 🛠️ 3. ฟังก์ชันและเครื่องมือ
# ==========================================
def convert_to_thai_date(date_obj):
    """แปลงวันที่เป็นภาษาไทย เช่น 7 มกราคม 2569"""
    if not date_obj: return ""
    thai_months = [
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    year_th = date_obj.year + 543
    return f"{date_obj.day} {thai_months[date_obj.month - 1]} {year_th}"

# ==========================================
# 🖥️ 3. ส่วนหน้าจอใช้งาน (UI)
# ==========================================
st.set_page_config(page_title="เฮียยอน Morroc AI", page_icon="⚽", layout="wide")

st.title("⚽ เฮียยอน Morroc : ระบบผลิตทีเด็ดบอล AI")
st.markdown("---")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        match_date_input = st.date_input("📅 วันที่แข่งขัน", datetime.now())
        match_date = convert_to_thai_date(match_date_input)
    with col2:
        match_time = st.text_input("⏰ เวลาแข่งขัน (เช่น 02:00 น.)", "02:00 น.")

    st.info(f"📌 ข้อมูลที่จะใช้ในบทความ: **{match_date} เวลา {match_time}**")

    st.markdown("### 📸 ส่วนจัดการรูปภาพ")
    
    # Upload 3 รูปหลักสำหรับ AI
    uploaded_files = st.file_uploader(
        "1️⃣ อัปโหลดรูปให้ AI วิเคราะห์ (4 รูป: Win Prob / เหย้า / เยือน / Head to Head)", 
        type=['png', 'jpg', 'jpeg'], 
        accept_multiple_files=True
    )

    # Input Link รูปที่ 4-5 สำหรับแทรกในเนื้อหา
    st.markdown("👇 **ใส่ Link รูปที่ต้องการแทรกในบทความ (รูปที่ 4 และ 5)**")
    col_img1, col_img2 = st.columns(2)
    with col_img1:
        img4_url = st.text_input("🔗 Link รูปที่ 4 (แทรกเจ้าบ้าน)", placeholder="https://morroc.net/wp-content/...")
    with col_img2:
        img5_url = st.text_input("🔗 Link รูปที่ 5 (แทรกทีมเยือน)", placeholder="https://morroc.net/wp-content/...")

# ==========================================
# 🚀 4. ปุ่มรันและการทำงานหลัก
# ==========================================
if st.button("🚀 วิเคราะห์และส่งบทความ (Start)", type="primary"):
    if len(uploaded_files) < 3:
        st.warning("⚠️ รูปสำหรับวิเคราะห์ยังไม่ครบ 3 ใบนะลูกพี่! (Win Prob, เหย้า, เยือน)")
    else:
        status_box = st.status("กำลังเริ่มระบบปฏิบัติการเฮียยอน...", expanded=True)
        
        try:
            # --- ขั้นตอนที่ 1: เตรียมรูปภาพส่ง AI ---
            status_box.write("📸 กำลังแปลงไฟล์รูปภาพ...")
            contents_to_send = []
            # ใช้แค่ 4 รูปแรกที่อัปโหลดมา
            for up_file in uploaded_files[:4]:
                bytes_data = up_file.getvalue()
                contents_to_send.append({"mime_type": "image/jpeg", "data": bytes_data})

            # --- ขั้นตอนที่ 2: เตรียม Prompt ---
            status_box.write("🧠 กำลังเรียบเรียง Prompt เทพๆ...")

            raw_prompt = st.secrets["prompts"]["football_analysis_template"]
            PROMPT_TEMPLATE = raw_prompt.replace("{match_date}", match_date).replace("{match_time}", match_time)
            
            # รวมร่าง Prompt + รูป
            full_payload = [PROMPT_TEMPLATE] + contents_to_send

            # --- ขั้นตอนที่ 3: ส่งให้ Gemini ---
            status_box.write(f"🧠 กำลังปลุกเฮียยอน ({MODEL_NAME})...")
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(MODEL_NAME)
            
            # Config สูตรปากแจ๋ว
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
            
            # --- ขั้นตอนที่ 4: ระบบเสียบรูป (Image Injection) ---
            # *สำคัญ* เราจะเอา Text จาก AI มาแก้ ก่อนส่งไป WordPress
            final_content = response.text

            # แทนที่รูปที่ 4
            if img4_url:
                html_img4 = f'<div class="wp-block-image"><figure class="aligncenter"><img src="{img4_url}" alt="สถิติเจ้าบ้าน วิเคราะห์บอล" /></figure></div>'
                final_content = final_content.replace("[แทรกรูปเจ้าบ้าน]", html_img4)
            else:
                final_content = final_content.replace("[แทรกรูปเจ้าบ้าน]", "") # ลบออกถ้าไม่มี

            # แทนที่รูปที่ 5
            if img5_url:
                html_img5 = f'<div class="wp-block-image"><figure class="aligncenter"><img src="{img5_url}" alt="สถิติทีมเยือน วิเคราะห์บอล" /></figure></div>'
                final_content = final_content.replace("[แทรกรูปทีมเยือน]", html_img5)
            else:
                final_content = final_content.replace("[แทรกรูปทีมเยือน]", "") # ลบออกถ้าไม่มี

            # --- ขั้นตอนที่ 5: ส่งเข้า WordPress ---
            status_box.write("🚀 กำลังยิงบทความขึ้นเว็บ Morroc.net...")
            
            # แยกหัวข้อ Title ออกจากเนื้อหา Content
            lines = final_content.split('\n')
            post_title = "วิเคราะห์บอล (Auto Draft)" # ค่าเริ่มต้น
            content_start_index = 0
            
            for i, line in enumerate(lines):
                if line.startswith("Title:"):
                    post_title = line.replace("Title:", "").strip()
                    content_start_index = i + 1
                    break
            
            # เนื้อหาที่จะส่งคือส่วนที่เหลือ ตัด Title บรรทัดแรกออก
            post_content = "\n".join(lines[content_start_index:]).strip()

            # ยิง API WordPress
            auth = (WP_USER, WP_APP_PASSWORD)
            headers = {"Content-Type": "application/json"}
            data = { 
                "title": post_title, 
                "content": post_content, 
                "status": "draft" # แนะนำ Draft ก่อน จะได้เข้าไปเช็คความเรียบร้อย
                # ถ้าจะใส่ Tags/Category ต้องรู้ ID ถ้ายังไม่รู้ ใส่ไว้ในเนื้อหาก่อนดีแล้ว
            }
            
            wp_res = requests.post(WP_URL, json=data, auth=auth, headers=headers)
            
            if wp_res.status_code == 201:
                link = wp_res.json().get('link')
                status_box.update(label="✅ ภารกิจสำเร็จ! บทความขึ้นเว็บแล้ว", state="complete", expanded=False)
                st.balloons()
                st.success(f"**เรียบร้อยลูกพี่!** บทความวันที่ {match_date} ถูกส่งไปแล้ว")
                st.markdown(f"👉 **คลิกตรวจงานได้ที่นี่:** [{link}]({link})")
                
                # โชว์ตัวอย่างผลลัพธ์ที่แก้แล้ว
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