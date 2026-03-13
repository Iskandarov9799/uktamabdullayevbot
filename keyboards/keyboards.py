from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                            InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo)
from config import config

def phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamimni ulashish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📜 Tarix")],
            [KeyboardButton(text="🎓 Atestatsiya")],
            [KeyboardButton(text="📊 Natijalarim"), KeyboardButton(text="🏆 Reyting")],
            [KeyboardButton(text="👤 Profil"),       KeyboardButton(text="ℹ️ Yordam")],
        ],
        resize_keyboard=True
    )

def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="payment:cancel")
    ]])

def back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Orqaga")]],
        resize_keyboard=True
    )

def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Kutayotgan to'lovlar")],
            [KeyboardButton(text="👥 Foydalanuvchilar"),  KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="📢 Broadcast"),          KeyboardButton(text="➕ Savol qo'shish")],
            [KeyboardButton(text="📋 Savollar"),           KeyboardButton(text="📥 Excel eksport")],
            [KeyboardButton(text="📤 Excel import"),       KeyboardButton(text="🗑 Savollarni o'chirish")],
            [KeyboardButton(text="🔙 Orqaga")],
        ],
        resize_keyboard=True
    )

def skip_image_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ Rasmisiz davom etish")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True
    )

# ── Asosiy: fan tanlash ────────────────────────────────────
def tarix_subjects_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌍 Jahon tarixi",        callback_data="tarix:sub:jahon")],
        [InlineKeyboardButton(text="🇺🇿 O'zbekiston tarixi", callback_data="tarix:sub:uzbekiston")],
    ])

# ── Kategoriya ─────────────────────────────────────────────
def tarix_category_keyboard(subject: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Mavzulashtirilgan", callback_data=f"tarix:cat:{subject}:mavzu")],
        [InlineKeyboardButton(text="🏫 Sinflar bo'yicha",  callback_data=f"tarix:cat:{subject}:sinf")],
        [InlineKeyboardButton(text="🔀 Aralash test",      callback_data=f"tarix:cat:{subject}:aralash")],
        [InlineKeyboardButton(text="🎓 Atestatsiya",       callback_data=f"tarix:cat:{subject}:attestation")],
        [InlineKeyboardButton(text="🔙 Orqaga",            callback_data="tarix:back:subjects")],
    ])

# ── Mavzular ───────────────────────────────────────────────
def jahon_topics_keyboard():
    buttons = []
    for key, label in config.JAHON_TOPICS.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"tarix:topic:jahon:{key}")])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="tarix:back:cat:jahon")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def uzbekiston_topics_keyboard():
    buttons = []
    for key, label in config.UZBEKISTON_TOPICS.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"tarix:topic:uzbekiston:{key}")])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="tarix:back:cat:uzbekiston")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ── Sinflar ────────────────────────────────────────────────
def grades_keyboard(subject: str):
    grades = config.JAHON_GRADES if subject == 'jahon' else config.UZBEKISTON_GRADES
    buttons, row = [], []
    for key, label in grades.items():
        row.append(InlineKeyboardButton(text=label, callback_data=f"tarix:grade:{subject}:{key}"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"tarix:back:cat:{subject}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ── Qiyinlik ───────────────────────────────────────────────
def difficulty_keyboard(subject: str, category: str, subcategory: str = None):
    sub = subcategory or ''
    if category == 'aralash':
        back_data = f"tarix:back:cat:{subject}"
    else:
        back_data = f"tarix:back:topic:{subject}:{category}:{sub}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Oson",   callback_data=f"tarix:diff:{subject}:{category}:{sub}:easy")],
        [InlineKeyboardButton(text="🟡 O'rta",  callback_data=f"tarix:diff:{subject}:{category}:{sub}:medium")],
        [InlineKeyboardButton(text="🔴 Qiyin",  callback_data=f"tarix:diff:{subject}:{category}:{sub}:hard")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=back_data)],
    ])

# ── Mini App ───────────────────────────────────────────────
def miniapp_keyboard(url: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🚀 Testni boshlash", web_app=WebAppInfo(url=url))
    ]])

# ── To'lov ─────────────────────────────────────────────────
def retry_buy_keyboard(access_key: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 {config.PRICE_RETRY:,} so'm to'lash", callback_data=f"buy:retry:{access_key}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="payment:cancel")],
    ])

def attestation_buy_keyboard(subject: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 {config.PRICE_ATTESTATION:,} so'm to'lash", callback_data=f"buy:attestation:{subject}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="payment:cancel")],
    ])

def attestation_format_keyboard(subject: str = ''):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Mini App", callback_data=f"attest:format:miniapp:{subject}")],
        [InlineKeyboardButton(text="📄 PDF",      callback_data=f"attest:format:pdf:{subject}")],
    ])

def payment_confirm_keyboard(purchase_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_pay:{purchase_id}"),
        InlineKeyboardButton(text="❌ Rad etish",  callback_data=f"reject_pay:{purchase_id}"),
    ]])

# ── Atestatsiya (asosiy menyu) ─────────────────────────────
def attestation_subjects_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌍 Jahon tarixi",        callback_data="attest:sub:jahon")],
        [InlineKeyboardButton(text="🇺🇿 O'zbekiston tarixi", callback_data="attest:sub:uzbekiston")],
    ])

# ── Admin: savol qo'shish ──────────────────────────────────
def subject_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌍 Jahon tarixi",        callback_data="addq:subject:jahon")],
        [InlineKeyboardButton(text="🇺🇿 O'zbekiston tarixi", callback_data="addq:subject:uzbekiston")],
        [InlineKeyboardButton(text="❌ Bekor",               callback_data="addq:cancel")],
    ])

def addq_category_keyboard(subject: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Mavzulashtirilgan", callback_data="addq:cat:mavzu")],
        [InlineKeyboardButton(text="🏫 Sinflar",           callback_data="addq:cat:sinf")],
        [InlineKeyboardButton(text="🔀 Aralash",           callback_data="addq:cat:aralash")],
        [InlineKeyboardButton(text="🎓 Atestatsiya",       callback_data="addq:cat:attestation")],
        [InlineKeyboardButton(text="❌ Bekor",             callback_data="addq:cancel")],
    ])

def addq_topic_keyboard(subject: str):
    topics = config.JAHON_TOPICS if subject == 'jahon' else config.UZBEKISTON_TOPICS
    buttons = []
    for key, label in topics.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"addq:topic:{key}")])
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def addq_grade_keyboard(subject: str):
    grades = config.JAHON_GRADES if subject == 'jahon' else config.UZBEKISTON_GRADES
    buttons, row = [], []
    for key, label in grades.items():
        row.append(InlineKeyboardButton(text=label, callback_data=f"addq:grade:{key}"))
        if len(row) == 3: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def addq_difficulty_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Oson",  callback_data="addq:diff:easy")],
        [InlineKeyboardButton(text="🟡 O'rta", callback_data="addq:diff:medium")],
        [InlineKeyboardButton(text="🔴 Qiyin", callback_data="addq:diff:hard")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")],
    ])

def correct_answer_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="A", callback_data="addq:correct:A"),
            InlineKeyboardButton(text="B", callback_data="addq:correct:B"),
            InlineKeyboardButton(text="C", callback_data="addq:correct:C"),
            InlineKeyboardButton(text="D", callback_data="addq:correct:D"),
        ],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")],
    ])