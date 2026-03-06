from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import qrcode, io, base64, uuid, os, smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
app.secret_key = 'change-this-to-something-random'

# ══════════════════════════════════════════════════════════════
#  CONFIGURATION  ← edit only this section
# ══════════════════════════════════════════════════════════════
MAIL_HOST      = 'smtp.gmail.com'
MAIL_PORT      = 587
MAIL_USER      = 'iaffanmohammed7683@gmail.com'   # your Gmail
MAIL_PASS      = 'pabs cslf ocou cnkb'      # Gmail App Password (16 chars)

EVENT_NAME     = 'Technocraft 2026'
EVENT_DATE     = '15th MARCH 2026'
EVENT_VENUE    = 'VAAGDEVI COLLEGE'
REG_FEE        = 500                   # INR

UPI_ID         = '9133651540@axl'           # e.g. 9876543210@ybl
ACCOUNT_NAME   = 'md affan'

ADMIN_USERNAME = 'orion'
ADMIN_PASSWORD = 'affannasif'               # ← change this!

BANK_QR_IMAGE  = os.path.join(os.path.dirname(__file__), 'static', 'bank_qr.png')
# ══════════════════════════════════════════════════════════════

pending   = {}   # pass_id → student dict
approved  = {}
rejected  = {}
used_utrs = set()


# ── HELPERS ───────────────────────────────────────────────────

def generate_pass_id():
    return f"TF{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"


def generate_qr_bytes(data: str) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#1a1a2e', back_color='white')
    buf = io.BytesIO(); img.save(buf, format='PNG'); return buf.getvalue()


def generate_epass_image(student: dict) -> bytes:
    W, H = 900, 400
    img  = Image.new('RGB', (W, H), '#0f0c29')
    draw = ImageDraw.Draw(img)
    for i in range(H):
        draw.line([(0,i),(W,i)], fill=(int(15+(i/H)*20), int(12+(i/H)*10), int(41+(i/H)*30)))
    draw.rectangle([0,0,8,H],     fill='#e94560')
    draw.rectangle([0,0,W,4],     fill='#e94560')
    draw.rectangle([0,H-4,W,H],   fill='#e94560')
    draw.rectangle([620,0,W,H],   fill='#16213e')
    draw.rectangle([620,0,624,H], fill='#e94560')
    try:
        fb  = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 36)
        fm  = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
        fs  = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
        fxs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
        fl  = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
    except Exception:
        fb = fm = fs = fxs = fl = ImageFont.load_default()
    draw.text((30,20),  '● E-PASS',  font=fs, fill='#e94560')
    draw.text((30,60),  EVENT_NAME,  font=fb, fill='#ffffff')
    draw.rectangle([30,110,600,112], fill='#e94560')
    y = 130
    for label, val in [('NAME', student['name'].upper()), ('ROLL NO', student['roll_no']),
                        ('BRANCH', student['branch']),     ('YEAR', f"Year {student['year']}"),
                        ('EMAIL', student['email'])]:
        draw.text((30,y), label, font=fl, fill='#e94560')
        draw.text((130,y), val,  font=fs, fill='#ffffff')
        y += 34
    draw.text((30,320), f"📅  {EVENT_DATE}     📍  {EVENT_VENUE}", font=fxs, fill='#8a8fa8')
    qr_img = Image.open(io.BytesIO(
        generate_qr_bytes(f"PASS:{student['pass_id']}|NAME:{student['name']}|ROLL:{student['roll_no']}")
    )).resize((180,180))
    img.paste(qr_img, (645,90))
    draw.text((635,285), 'PASS ID',          font=fl,  fill='#e94560')
    draw.text((635,302), student['pass_id'], font=fxs, fill='#ffffff')
    draw.rectangle([645,340,860,375], fill='#e94560')
    draw.text((700,350), '✓  CONFIRMED', font=fm, fill='#ffffff')
    buf = io.BytesIO(); img.save(buf, format='PNG', dpi=(150,150)); return buf.getvalue()


def send_epass_email(student: dict) -> bool:
    epass_bytes = generate_epass_image(student)
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🎟️ Your E-Pass for {EVENT_NAME} — {student['pass_id']}"
    msg['From']    = MAIL_USER
    msg['To']      = student['email']
    html = f"""
    <div style="font-family:Arial,sans-serif;background:#f4f4f4;padding:30px;">
      <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.1);">
        <div style="background:#0f0c29;padding:30px;text-align:center;">
          <h1 style="color:#e94560;margin:0;font-size:28px;">{EVENT_NAME}</h1>
          <p style="color:#8a8fa8;margin:8px 0 0;">Registration Approved! 🎉</p>
        </div>
        <div style="padding:30px;">
          <p style="color:#333;font-size:16px;">Hi <strong>{student['name']}</strong>,</p>
          <p style="color:#555;">Your payment has been verified and your registration is confirmed. Your E-Pass is attached below.</p>
          <div style="background:#f8f8f8;border-left:4px solid #e94560;padding:15px 20px;margin:20px 0;border-radius:0 8px 8px 0;">
            <p style="margin:4px 0;color:#333;"><strong>Pass ID:</strong> {student['pass_id']}</p>
            <p style="margin:4px 0;color:#333;"><strong>Event:</strong> {EVENT_NAME}</p>
            <p style="margin:4px 0;color:#333;"><strong>Date:</strong> {EVENT_DATE}</p>
            <p style="margin:4px 0;color:#333;"><strong>Venue:</strong> {EVENT_VENUE}</p>
          </div>
          <p style="color:#555;">Present this E-Pass (or its QR code) at the entrance for entry.</p>
          <p style="color:#999;font-size:13px;">This is an automated email. Do not reply.</p>
        </div>
        <div style="background:#0f0c29;padding:15px;text-align:center;">
          <p style="color:#8a8fa8;margin:0;font-size:12px;">© {EVENT_NAME} · All rights reserved</p>
        </div>
      </div>
    </div>"""
    msg.attach(MIMEText(html, 'html'))
    part = MIMEBase('image','png'); part.set_payload(epass_bytes); encoders.encode_base64(part)
    part.add_header('Content-Disposition','attachment', filename=f"epass_{student['pass_id']}.png")
    msg.attach(part)
    try:
        with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as s:
            s.starttls(); s.login(MAIL_USER, MAIL_PASS); s.send_message(msg)
        return True
    except Exception as e:
        print(f'[EMAIL ERROR] {e}'); return False


def send_rejection_email(student: dict, reason: str) -> bool:
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Registration Update — {EVENT_NAME}"
    msg['From']    = MAIL_USER
    msg['To']      = student['email']
    html = f"""
    <div style="font-family:Arial,sans-serif;background:#f4f4f4;padding:30px;">
      <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;">
        <div style="background:#0f0c29;padding:30px;text-align:center;">
          <h1 style="color:#e94560;margin:0;font-size:28px;">{EVENT_NAME}</h1>
          <p style="color:#8a8fa8;margin:8px 0 0;">Registration Update</p>
        </div>
        <div style="padding:30px;">
          <p style="color:#333;font-size:16px;">Hi <strong>{student['name']}</strong>,</p>
          <p style="color:#555;">We could not verify your payment:</p>
          <div style="background:#fff5f5;border-left:4px solid #e94560;padding:15px 20px;margin:20px 0;border-radius:0 8px 8px 0;">
            <p style="margin:0;color:#c0392b;">{reason}</p>
          </div>
          <p style="color:#555;">Please contact the event coordinator for assistance at {MAIL_USER}.</p>
        </div>
      </div>
    </div>"""
    msg.attach(MIMEText(html, 'html'))
    try:
        with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as s:
            s.starttls(); s.login(MAIL_USER, MAIL_PASS); s.send_message(msg)
        return True
    except Exception as e:
        print(f'[EMAIL ERROR] {e}'); return False


def get_bank_qr_b64() -> str:
    if os.path.exists(BANK_QR_IMAGE):
        with open(BANK_QR_IMAGE, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    upi = f"upi://pay?pa={UPI_ID}&pn={ACCOUNT_NAME}&am={REG_FEE}&cu=INR"
    return base64.b64encode(generate_qr_bytes(upi)).decode()


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ── STUDENT ROUTES ────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html',
        event_name=EVENT_NAME, event_date=EVENT_DATE,
        event_venue=EVENT_VENUE, fee=REG_FEE,
        upi_id=UPI_ID, account_name=ACCOUNT_NAME,
        bank_qr_b64=get_bank_qr_b64())


@app.route('/submit', methods=['POST'])
def submit():
    # Accept multipart form (screenshot upload)
    name     = request.form.get('name','').strip()
    roll_no  = request.form.get('roll_no','').strip()
    branch   = request.form.get('branch','').strip()
    year     = request.form.get('year','').strip()
    email    = request.form.get('email','').strip()
    utr      = request.form.get('utr','').strip().upper()
    upi_sent = request.form.get('upi_id','').strip()  # UPI ID student typed
    screenshot = request.files.get('screenshot')

    # Validations
    if not utr:
        return jsonify({'success': False, 'error': 'Please enter your UTR / transaction ID.'}), 400
    if not upi_sent:
        return jsonify({'success': False, 'error': 'Please enter the UPI ID you paid from.'}), 400
    if not screenshot or screenshot.filename == '':
        return jsonify({'success': False, 'error': 'Please upload a screenshot of your payment.'}), 400
    if utr in used_utrs:
        return jsonify({'success': False, 'error': 'This UTR has already been submitted.'}), 400

    # Read screenshot as base64
    screenshot_bytes = screenshot.read()
    # Resize if too large (max 1MB stored in memory)
    try:
        ss_img = Image.open(io.BytesIO(screenshot_bytes))
        ss_img.thumbnail((800, 800), Image.LANCZOS)
        buf = io.BytesIO()
        ss_img.save(buf, format='JPEG', quality=80)
        screenshot_b64 = base64.b64encode(buf.getvalue()).decode()
    except Exception:
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

    pass_id = generate_pass_id()
    student = {
        'pass_id':        pass_id,
        'name':           name,
        'branch':         branch,
        'roll_no':        roll_no,
        'email':          email,
        'year':           year,
        'utr':            utr,
        'upi_sent':       upi_sent,       # UPI ID the student typed
        'screenshot_b64': screenshot_b64, # payment screenshot
        'submitted_at':   datetime.now().strftime('%d %b %Y, %I:%M %p'),
        'status':         'pending',
    }
    pending[pass_id] = student
    used_utrs.add(utr)
    return jsonify({'success': True, 'pass_id': pass_id})


@app.route('/status/<pass_id>')
def status(pass_id):
    if pass_id in approved:
        return jsonify({'status': 'approved'})
    if pass_id in rejected:
        return jsonify({'status': 'rejected', 'reason': rejected[pass_id].get('reject_reason','')})
    if pass_id in pending:
        return jsonify({'status': 'pending'})
    return jsonify({'status': 'not_found'}), 404


# ── ADMIN ROUTES ──────────────────────────────────────────────

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    error = ''
    if request.method == 'POST':
        if (request.form.get('username') == ADMIN_USERNAME and
                request.form.get('password') == ADMIN_PASSWORD):
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        error = 'Invalid credentials.'
    return render_template('admin_login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin.html',
        pending=list(pending.values()),
        approved=list(approved.values()),
        rejected=list(rejected.values()),
        event_name=EVENT_NAME,
        our_upi=UPI_ID)   # pass our UPI ID so admin can compare


@app.route('/admin/approve/<pass_id>', methods=['POST'])
@admin_required
def approve(pass_id):
    student = pending.pop(pass_id, None)
    if not student:
        return jsonify({'success': False, 'error': 'Not found.'}), 404
    student['status']      = 'approved'
    student['approved_at'] = datetime.now().strftime('%d %b %Y, %I:%M %p')
    approved[pass_id]      = student
    email_sent = send_epass_email(student)
    return jsonify({'success': True, 'email_sent': email_sent, 'name': student['name']})


@app.route('/admin/reject/<pass_id>', methods=['POST'])
@admin_required
def reject(pass_id):
    data    = request.get_json()
    reason  = data.get('reason', 'Payment could not be verified.')
    student = pending.pop(pass_id, None)
    if not student:
        return jsonify({'success': False, 'error': 'Not found.'}), 404
    student['status']        = 'rejected'
    student['reject_reason'] = reason
    student['rejected_at']   = datetime.now().strftime('%d %b %Y, %I:%M %p')
    rejected[pass_id]        = student
    used_utrs.discard(student['utr'])
    send_rejection_email(student, reason)
    return jsonify({'success': True, 'name': student['name']})


if __name__ == '__main__':
    os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)
    app.run(debug=True)