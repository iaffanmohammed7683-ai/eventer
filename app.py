from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import qrcode, io, base64, uuid, os, requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from supabase import create_client, Client

# ══════════════════════════════════════════════════════════════
os.environ.setdefault('SUPABASE_URL',   'https://mnsgpgoakhwoixcotlpk.supabase.co')
os.environ.setdefault('SUPABASE_KEY',   'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1uc2dwZ29ha2h3b2l4Y290bHBrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMwMzk2NjEsImV4cCI6MjA4ODYxNTY2MX0.k-vVLPBj2y9J_kGvAEl_bATsEn8LBA3AD3RsxZ0U8Jg')
os.environ.setdefault('SECRET_KEY',     'anyrandomstring456')
os.environ.setdefault('ADMIN_USERNAME', 'orion')
os.environ.setdefault('ADMIN_PASSWORD', 'affannasif')
os.environ.setdefault('EVENT_NAME',     'Euphoria 2k26')
os.environ.setdefault('EVENT_DATE',     '14,15 march 2026')
os.environ.setdefault('EVENT_VENUE',    'VAAGDEVI COLLEGES BOLLIKUNTA')
os.environ.setdefault('UPI_ID',         '9985213286@ybl')
os.environ.setdefault('ACCOUNT_NAME',   'AR nasif')
os.environ.setdefault('MAIL_USER',      'iaffanmohammed7683@gmail.com')
os.environ.setdefault('BREVO_API_KEY',  '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')
# ══════════════════════════════════════════════════════════════

app = Flask(__name__)

EVENT_NAME    = os.environ.get('EVENT_NAME',  'euphoria 2k26')
EVENT_DATE    = os.environ.get('EVENT_DATE',  '14,15 march 2026')
EVENT_VENUE   = os.environ.get('EVENT_VENUE', 'VAAGDEVI COLLEGES BOLLIKUNTA')
UPI_ID        = os.environ.get('UPI_ID',      '99985213286@ybl')
ACCOUNT_NAME  = os.environ.get('ACCOUNT_NAME','AR Nasif')
BANK_QR_IMAGE = os.path.join(os.path.dirname(__file__), 'static', 'bank_qr.png')
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(32)

SUB_EVENTS = {
    'esports': {
        'name':        'Esports',
        'emoji':       '🎮',
        'fee':         300,
        'type':        'team',
        'max_members': 4,
        'description': 'Team gaming tournament — max 4 players per team',
        'color':       '#7c3aed',
        'full':        False,
    },
    'treasure-hunt': {
        'name':        'Treasure Hunt',
        'emoji':       '🗺️',
        'fee':         200,
        'type':        'team',
        'max_members': 5,
        'description': 'Campus-wide treasure hunt — max 5 members per team',
        'color':       '#d97706',
        'full':        True,
    },
    'slow-bike-race': {
        'name':        'Slow Bike Race',
        'emoji':       '🚲',
        'fee':         100,
        'type':        'individual',
        'max_members': 1,
        'description': 'Last one to finish wins!',
        'color':       '#059669',
        'full':        False,
    },
}

def check_admin_credentials(username, password):
    u = os.environ.get('ADMIN_USERNAME','').strip()
    p = os.environ.get('ADMIN_PASSWORD','').strip()
    if not u or not p: return False
    return username.strip() == u and password.strip() == p

def get_db():
    return create_client(os.environ.get('SUPABASE_URL',''), os.environ.get('SUPABASE_KEY',''))

def generate_pass_id(prefix='SE'):
    return f"{prefix}{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"

def generate_qr_bytes(data):
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(data); qr.make(fit=True)
    img = qr.make_image(fill_color='#1a1a2e', back_color='white')
    buf = io.BytesIO(); img.save(buf, format='PNG'); return buf.getvalue()

def get_bank_qr_b64():
    if os.path.exists(BANK_QR_IMAGE):
        with open(BANK_QR_IMAGE, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    upi = f"upi://pay?pa={UPI_ID}&pn={ACCOUNT_NAME}&am=0&cu=INR"
    return base64.b64encode(generate_qr_bytes(upi)).decode()

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ── SUB-EVENT E-PASS IMAGE ────────────────────────────────────

def generate_subevent_epass(reg, ev):
    W, H = 900, 420
    hex_col = ev['color'].lstrip('#')
    img  = Image.new('RGB', (W, H), '#0a0a1a')
    draw = ImageDraw.Draw(img)
    for i in range(H):
        r = int(10+(i/H)*15); g = int(10+(i/H)*10); b = int(26+(i/H)*20)
        draw.line([(0,i),(W,i)], fill=(r,g,b))
    draw.rectangle([0,0,8,H],     fill=ev['color'])
    draw.rectangle([0,0,W,4],     fill=ev['color'])
    draw.rectangle([0,H-4,W,H],   fill=ev['color'])
    draw.rectangle([620,0,W,H],   fill='#12122a')
    draw.rectangle([620,0,624,H], fill=ev['color'])
    try:
        fb  = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30)
        fm  = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
        fs  = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)
        fxs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
        fl  = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 10)
    except:
        fb = fm = fs = fxs = fl = ImageFont.load_default()
    draw.text((30,15),  f"{EVENT_NAME} — SUB EVENT", font=fl,  fill=ev['color'])
    draw.text((30,45),  ev['name'],                   font=fb,  fill='#ffffff')
    draw.text((30,85),  ev['description'],             font=fxs, fill='#8a8fa8')
    draw.rectangle([30,108,600,110], fill=ev['color'])
    y = 120
    for label, val in [
        ('NAME',    reg['name'].upper()),
        ('ROLL NO', reg['roll_no']),
        ('BRANCH',  reg['branch']),
        ('YEAR',    f"Year {reg['year']}"),
    ]:
        draw.text((30,y), label, font=fl, fill=ev['color'])
        draw.text((130,y), val,  font=fs, fill='#ffffff'); y += 30
    if ev['type'] == 'team':
        draw.text((30,y), 'TEAM', font=fl, fill=ev['color'])
        draw.text((130,y), reg.get('team_name',''), font=fs, fill='#ffffff'); y += 30
    draw.text((30,y), 'EMAIL', font=fl, fill=ev['color'])
    draw.text((130,y), reg['email'], font=fxs, fill='#ffffff')
    draw.text((30,390), f"{EVENT_DATE}  |  {EVENT_VENUE}", font=fl, fill='#8a8fa8')
    qr_data = f"SUBEVENT:{ev['name']}|PASS:{reg['pass_id']}|NAME:{reg['name']}"
    if ev['type'] == 'team':
        qr_data += f"|TEAM:{reg.get('team_name','')}"
    qr_img = Image.open(io.BytesIO(generate_qr_bytes(qr_data))).resize((170,170))
    img.paste(qr_img, (650,80))
    draw.text((635,262), 'PASS ID',      font=fl,  fill=ev['color'])
    draw.text((635,278), reg['pass_id'], font=fxs, fill='#ffffff')
    draw.rectangle([640,310,875,345], fill=ev['color'])
    draw.text((688,318), 'CONFIRMED', font=fm, fill='#ffffff')
    buf = io.BytesIO(); img.save(buf, format='PNG', dpi=(150,150)); return buf.getvalue()


# ── EMAIL via Brevo ───────────────────────────────────────────

def _send_brevo(to_email, subject, html, attachment_b64=None, attachment_name=None):
    api_key  = os.environ.get('BREVO_API_KEY','').strip()
    sender   = os.environ.get('MAIL_USER','iaffanmohammed7683@gmail.com').strip()
    if not api_key:
        print('[EMAIL ERROR] BREVO_API_KEY not set'); return False
    payload = {
        'sender':  {'name': 'Euphoria 2K26', 'email': sender},
        'to':      [{'email': to_email}],
        'subject': subject,
        'htmlContent': html,
    }
    if attachment_b64 and attachment_name:
        payload['attachment'] = [{'name': attachment_name, 'content': attachment_b64}]
    try:
        resp = requests.post(
            'https://api.brevo.com/v3/smtp/email',
            headers={'api-key': api_key, 'Content-Type': 'application/json'},
            json=payload,
            timeout=20
        )
        if resp.status_code in (200, 201):
            print(f'[EMAIL OK - BREVO] Sent to {to_email}'); return True
        else:
            print(f'[EMAIL ERROR - BREVO] {resp.status_code} {resp.text}'); return False
    except Exception as e:
        print(f'[EMAIL ERROR - BREVO] {e}'); return False

def send_subevent_epass_email(reg, ev):
    epass_bytes = generate_subevent_epass(reg, ev)
    epass_b64   = base64.b64encode(epass_bytes).decode()
    team_line   = f"<p style='margin:4px 0'><strong>Team:</strong> {reg.get('team_name','')}</p>" if ev['type']=='team' else ''
    html = f"""<div style="font-family:Arial,sans-serif;background:#f4f4f4;padding:30px;">
      <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;">
        <div style="background:#0a0a1a;padding:30px;text-align:center;">
          <h1 style="color:{ev['color']};margin:0;">{ev['name']}</h1>
          <p style="color:#8a8fa8;margin:8px 0 0;">{EVENT_NAME} — Registration Approved!</p></div>
        <div style="padding:30px;">
          <p>Hi <strong>{reg['name']}</strong>,</p>
          <p>Your payment has been verified. Your E-Pass is attached.</p>
          <div style="background:#f8f8f8;border-left:4px solid {ev['color']};padding:15px;margin:20px 0;border-radius:0 8px 8px 0;">
            <p style="margin:4px 0"><strong>Pass ID:</strong> {reg['pass_id']}</p>
            <p style="margin:4px 0"><strong>Event:</strong> {ev['name']}</p>
            {team_line}
            <p style="margin:4px 0"><strong>Date:</strong> {EVENT_DATE}</p>
            <p style="margin:4px 0"><strong>Venue:</strong> {EVENT_VENUE}</p></div>
          <p>Show your E-Pass at the entrance for entry.</p></div></div></div>"""
    return _send_brevo(reg['email'], f"Your E-Pass for {ev['name']} - {reg['pass_id']}", html,
                       epass_b64, f"epass_{reg['pass_id']}.png")

def send_rejection_email(student, reason, ev_name):
    html = f"""<div style="font-family:Arial,sans-serif;background:#f4f4f4;padding:30px;">
      <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;">
        <div style="background:#0a0a1a;padding:30px;text-align:center;">
          <h1 style="color:#e94560;margin:0;">{ev_name}</h1></div>
        <div style="padding:30px;">
          <p>Hi <strong>{student['name']}</strong>,</p>
          <p>We could not verify your payment for <strong>{ev_name}</strong>:</p>
          <div style="background:#fff5f5;border-left:4px solid #e94560;padding:15px;margin:20px 0;">
            <p style="margin:0;color:#c0392b;">{reason}</p></div>
          <p>Contact us at iaffanmohammed7683@gmail.com for help.</p></div></div></div>"""
    return _send_brevo(student['email'], f"Registration Update - {ev_name}", html)


# ══════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html',
        event_name=EVENT_NAME, event_date=EVENT_DATE,
        event_venue=EVENT_VENUE, sub_events=SUB_EVENTS)

@app.route('/events/<slug>')
def subevent_register(slug):
    ev = SUB_EVENTS.get(slug)
    if not ev: return "Event not found", 404
    if ev.get('full'):
        return render_template('event_full.html', ev=ev, event_name=EVENT_NAME)
    return render_template('subevent_register.html',
        ev=ev, slug=slug, event_name=EVENT_NAME,
        event_date=EVENT_DATE, event_venue=EVENT_VENUE,
        upi_id=UPI_ID, account_name=ACCOUNT_NAME,
        bank_qr_b64=get_bank_qr_b64())

@app.route('/events/<slug>/submit', methods=['POST'])
def subevent_submit(slug):
    ev = SUB_EVENTS.get(slug)
    if not ev: return jsonify({'success':False,'error':'Invalid event.'}),404
    if ev.get('full'): return jsonify({'success':False,'error':'Registrations are full.'}),400
    name       = request.form.get('name','').strip()
    roll_no    = request.form.get('roll_no','').strip()
    branch     = request.form.get('branch','').strip()
    year       = request.form.get('year','').strip()
    email      = request.form.get('email','').strip()
    utr        = request.form.get('utr','').strip().upper()
    upi_sent   = request.form.get('upi_id','').strip()
    screenshot = request.files.get('screenshot')
    team_name  = request.form.get('team_name','').strip()
    members    = request.form.get('members','').strip()
    game_pref  = request.form.get('game_preference','').strip()
    if not utr:      return jsonify({'success':False,'error':'Please enter your UTR.'}),400
    if not upi_sent: return jsonify({'success':False,'error':'Please enter your UPI ID.'}),400
    if not screenshot or not screenshot.filename:
        return jsonify({'success':False,'error':'Please upload payment screenshot.'}),400
    if ev['type'] == 'team' and not team_name:
        return jsonify({'success':False,'error':'Please enter your team name.'}),400
    db = get_db()
    if db.table('subevent_registrations').select('pass_id').eq('utr',utr).eq('event_slug',slug).execute().data:
        return jsonify({'success':False,'error':'This UTR is already used for this event.'}),400
    try:
        ss_img = Image.open(io.BytesIO(screenshot.read())); ss_img.thumbnail((800,800),Image.LANCZOS)
        buf = io.BytesIO(); ss_img.save(buf,format='JPEG',quality=80)
        screenshot_b64 = base64.b64encode(buf.getvalue()).decode()
    except: screenshot_b64 = ''
    prefix  = ''.join(w[0] for w in ev['name'].split()).upper()
    pass_id = generate_pass_id(prefix)
    db.table('subevent_registrations').insert({
        'pass_id':pass_id,'event_slug':slug,'event_name':ev['name'],
        'name':name,'roll_no':roll_no,'branch':branch,'year':year,'email':email,
        'utr':utr,'upi_sent':upi_sent,'screenshot_b64':screenshot_b64,
        'team_name':team_name,'members':members,'game_preference':game_pref,
        'status':'pending','submitted_at':datetime.now().isoformat(),
    }).execute()
    return jsonify({'success':True,'pass_id':pass_id})

@app.route('/events/<slug>/status/<pass_id>')
def subevent_status(slug, pass_id):
    db  = get_db()
    res = db.table('subevent_registrations').select('status,reject_reason').eq('pass_id',pass_id).execute()
    if not res.data: return jsonify({'status':'not_found'}),404
    row = res.data[0]
    return jsonify({'status':row['status'],'reason':row.get('reject_reason','')})


# ── ADMIN ─────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    error = ''
    if request.method == 'POST':
        if check_admin_credentials(request.form.get('username',''), request.form.get('password','')):
            session.clear(); session['admin'] = True; session.permanent = True
            return redirect(url_for('admin_dashboard'))
        error = 'Invalid username or password.'
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.clear(); return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    def tag(rows, ev_name, ev_slug):
        for r in rows:
            r['_event_name'] = ev_name
            r['_event_slug'] = ev_slug
        return rows
    all_p, all_a, all_r = [], [], []
    for slug, ev in SUB_EVENTS.items():
        tbl = 'subevent_registrations'
        all_p += tag(db.table(tbl).select('*').eq('event_slug',slug).eq('status','pending').order('submitted_at',desc=True).execute().data,  ev['name'], slug)
        all_a += tag(db.table(tbl).select('*').eq('event_slug',slug).eq('status','approved').order('approved_at',desc=True).execute().data,  ev['name'], slug)
        all_r += tag(db.table(tbl).select('*').eq('event_slug',slug).eq('status','rejected').order('rejected_at',desc=True).execute().data,  ev['name'], slug)
    all_p.sort(key=lambda x: x.get('submitted_at',''), reverse=True)
    return render_template('admin.html',
        pending=all_p, approved=all_a, rejected=all_r,
        event_name=EVENT_NAME, our_upi=UPI_ID, sub_events=SUB_EVENTS)

@app.route('/admin/approve/<pass_id>', methods=['POST'])
@admin_required
def approve(pass_id):
    body = request.get_json() or {}
    slug = body.get('slug','')
    db   = get_db()
    res  = db.table('subevent_registrations').select('*').eq('pass_id',pass_id).execute()
    if not res.data: return jsonify({'success':False,'error':'Not found.'}),404
    row  = res.data[0]
    db.table('subevent_registrations').update({'status':'approved','approved_at':datetime.now().isoformat()}).eq('pass_id',pass_id).execute()
    ev         = SUB_EVENTS.get(slug or row.get('event_slug',''), {})
    email_sent = send_subevent_epass_email(row, ev) if ev else False
    return jsonify({'success':True,'email_sent':email_sent,'name':row['name']})

@app.route('/admin/reject/<pass_id>', methods=['POST'])
@admin_required
def reject(pass_id):
    body   = request.get_json() or {}
    reason = body.get('reason','Payment could not be verified.')
    slug   = body.get('slug','')
    db     = get_db()
    res    = db.table('subevent_registrations').select('*').eq('pass_id',pass_id).execute()
    if not res.data: return jsonify({'success':False,'error':'Not found.'}),404
    row = res.data[0]
    db.table('subevent_registrations').update({'status':'rejected','reject_reason':reason,'rejected_at':datetime.now().isoformat()}).eq('pass_id',pass_id).execute()
    ev_name = SUB_EVENTS.get(slug or row.get('event_slug',''), {}).get('name', EVENT_NAME)
    send_rejection_email(row, reason, ev_name)
    return jsonify({'success':True,'name':row['name']})


if __name__ == '__main__':
    os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)
    app.run(debug=True, port=5001)
