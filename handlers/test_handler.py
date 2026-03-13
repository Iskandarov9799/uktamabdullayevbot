from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
import json, base64, zlib

from database.db import (is_registered, get_access_status, mark_free_used,
                         has_attestation, get_attestation_format,
                         get_questions, count_questions, save_test_result,
                         grant_attestation)
from keyboards.keyboards import (
    tarix_subjects_keyboard, tarix_category_keyboard,
    jahon_topics_keyboard, uzbekiston_topics_keyboard,
    grades_keyboard, difficulty_keyboard,
    retry_buy_keyboard, attestation_buy_keyboard,
    attestation_format_keyboard, miniapp_keyboard,
    main_menu_keyboard, attestation_subjects_keyboard
)
from config import config

router = Router()


def encode_questions(q_list, meta=None):
    payload = {'meta': meta or {}, 'questions': q_list}
    raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    return base64.urlsafe_b64encode(zlib.compress(raw.encode('utf-8'), level=9)).decode('ascii')

def questions_to_miniapp(questions):
    return [
        {"id": q.id, "t": q.question_text, "a": q.option_a, "b": q.option_b,
         "c": q.option_c, "d": q.option_d, "ok": q.correct_answer, "img": q.image_file_id or ""}
        for q in questions
    ]

def make_access_key(subject, category, subcategory=None, difficulty=None):
    return f"{subject}:{category}:{subcategory}:{difficulty}"

def get_subject_label(subject):
    return config.SUBJECTS.get(subject, subject)

def get_topic_label(subject, topic):
    topics = config.JAHON_TOPICS if subject == 'jahon' else config.UZBEKISTON_TOPICS
    return topics.get(topic, topic)

async def safe_edit(callback, text, reply_markup=None):
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        pass


# ══════════════════════════════════════════════
# MINIAPP LAUNCH
# ══════════════════════════════════════════════

async def launch_miniapp(callback, tid, subject, category,
                         subcategory=None, difficulty=None, is_attestation=False):
    if not await is_registered(tid):
        await callback.message.answer("❗ Avval ro'yxatdan o'ting — /start",
                                      reply_markup=main_menu_keyboard())
        await callback.answer()
        return

    cnt = await count_questions(subject=subject, category=category,
                                subcategory=subcategory, difficulty=difficulty,
                                is_attestation=is_attestation)
    if cnt == 0:
        await safe_edit(callback,
                        "❌ <b>Savollar topilmadi!</b>\n\n"
                        "Bu bo'limda hali savollar yo'q.\n"
                        "Admin tez orada qo'shadi 🙏")
        await callback.answer()
        return

    if not is_attestation:
        access_key = make_access_key(subject, category, subcategory, difficulty)
        status = await get_access_status(tid, access_key)
        if status == 'buy':
            await safe_edit(callback,
                            f"💳 <b>Bu test uchun to'lov talab qilinadi</b>\n\n"
                            f"💰 Narxi: <b>{config.PRICE_RETRY:,} so'm</b>",
                            reply_markup=retry_buy_keyboard(access_key))
            await callback.answer()
            return
    else:
        if not await has_attestation(tid, subject):
            await safe_edit(callback,
                            f"🎓 <b>Atestatsiya testi</b>\n\n"
                            f"💰 Narxi: <b>{config.PRICE_ATTESTATION:,} so'm</b> (bir martalik)",
                            reply_markup=attestation_buy_keyboard(subject))
            await callback.answer()
            return

    questions = await get_questions(
        subject=subject, category=category,
        subcategory=subcategory, difficulty=difficulty,
        is_attestation=is_attestation,
        count=config.ATTESTATION_COUNT if is_attestation else min(cnt, config.ATTESTATION_COUNT)
    )

    if not is_attestation:
        await mark_free_used(tid, make_access_key(subject, category, subcategory, difficulty))

    meta = {
        'subject': subject, 'category': category,
        'subcategory': subcategory, 'difficulty': difficulty,
        'is_attestation': is_attestation, 'solution_url': config.SOLUTION_URL,
    }
    encoded = encode_questions(questions_to_miniapp(questions), meta)
    url = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"

    DIFF = {'easy': '🟢 Oson', 'medium': "🟡 O'rta", 'hard': '🔴 Qiyin'}
    diff_label = DIFF.get(difficulty, '') if difficulty else ''
    sub_label  = get_topic_label(subject, subcategory) if subcategory else (subcategory or '')
    subj_label = get_subject_label(subject)

    await callback.message.answer(
        f"{subj_label} — <b>{sub_label or category}</b>"
        f"{' · ' + diff_label if diff_label else ''}\n\n"
        f"📝 Savollar soni: <b>{len(questions)} ta</b>\n\n"
        f"Testni boshlashga tayyor bo'lsangiz, tugmani bosing 👇",
        reply_markup=miniapp_keyboard(url),
        parse_mode="HTML"
    )
    await callback.answer()


# ══════════════════════════════════════════════
# 1. TARIX tugmasi → fan tanlash
# ══════════════════════════════════════════════

@router.message(F.text == "📜 Tarix")
async def tarix_menu(message: Message, state: FSMContext):
    if not await is_registered(message.from_user.id):
        await message.answer("❗ Avval ro'yxatdan o'ting — /start")
        return
    await message.answer(
        "📜 <b>Tarix</b>\n\nQaysi bo'limni tanlaysiz?",
        reply_markup=tarix_subjects_keyboard(),
        parse_mode="HTML"
    )

# ══════════════════════════════════════════════
# 2. Fan tanlash → kategoriya
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("tarix:sub:"))
async def tarix_subject(callback: CallbackQuery, state: FSMContext):
    subject = callback.data.split(":")[2]
    await state.update_data(subject=subject)
    label = get_subject_label(subject)
    await safe_edit(callback,
                    f"<b>{label}</b>\n\nQaysi turdagi testni ishlaysiz?",
                    reply_markup=tarix_category_keyboard(subject))
    await callback.answer()

# ══════════════════════════════════════════════
# 3. Kategoriya tanlash
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("tarix:cat:"))
async def tarix_category(callback: CallbackQuery, state: FSMContext):
    parts    = callback.data.split(":")
    subject  = parts[2]
    category = parts[3]
    tid      = callback.from_user.id
    await state.update_data(subject=subject, category=category)

    if category == 'mavzu':
        kb = jahon_topics_keyboard() if subject == 'jahon' else uzbekiston_topics_keyboard()
        await safe_edit(callback, "📌 <b>Mavzuni tanlang:</b>", reply_markup=kb)

    elif category == 'sinf':
        await safe_edit(callback, "🏫 <b>Sinfni tanlang:</b>",
                        reply_markup=grades_keyboard(subject))

    elif category == 'aralash':
        await safe_edit(callback,
                        "🔀 <b>Aralash test</b>\n\nQiyinlik darajasini tanlang:",
                        reply_markup=difficulty_keyboard(subject, 'aralash'))

    elif category == 'attestation':
        if not await has_attestation(tid, subject):
            await safe_edit(callback,
                            f"🎓 <b>Atestatsiya testi</b>\n\n"
                            f"💰 Narxi: <b>{config.PRICE_ATTESTATION:,} so'm</b> (bir martalik)",
                            reply_markup=attestation_buy_keyboard(subject))
        else:
            fmt = await get_attestation_format(tid, subject)
            if fmt == 'pdf':
                await callback.message.answer("📄 PDF versiya hozircha tayyorlanmoqda.")
            else:
                await launch_miniapp(callback, tid, subject, 'attestation', is_attestation=True)
            return

    await callback.answer()

# ══════════════════════════════════════════════
# 4. Mavzu tanlash → qiyinlik
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("tarix:topic:"))
async def tarix_topic(callback: CallbackQuery, state: FSMContext):
    parts   = callback.data.split(":")
    subject = parts[2]
    topic   = parts[3]
    await state.update_data(subject=subject, subcategory=topic)
    label = get_topic_label(subject, topic)
    await safe_edit(callback,
                    f"🎯 <b>{label}</b>\n\nQiyinlik darajasini tanlang:",
                    reply_markup=difficulty_keyboard(subject, 'mavzu', topic))
    await callback.answer()

# ══════════════════════════════════════════════
# 5. Sinf tanlash → qiyinlik
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("tarix:grade:"))
async def tarix_grade(callback: CallbackQuery, state: FSMContext):
    parts   = callback.data.split(":")
    subject = parts[2]
    grade   = parts[3]
    await state.update_data(subject=subject, subcategory=grade)
    grades = config.JAHON_GRADES if subject == 'jahon' else config.UZBEKISTON_GRADES
    await safe_edit(callback,
                    f"🏫 <b>{grades.get(grade, grade)}</b>\n\nQiyinlik darajasini tanlang:",
                    reply_markup=difficulty_keyboard(subject, 'sinf', grade))
    await callback.answer()

# ══════════════════════════════════════════════
# 6. Qiyinlik → launch
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("tarix:diff:"))
async def tarix_difficulty(callback: CallbackQuery, state: FSMContext):
    parts       = callback.data.split(":")
    subject     = parts[2]
    category    = parts[3]
    subcategory = parts[4] if parts[4] else None
    difficulty  = parts[5]
    await launch_miniapp(callback, callback.from_user.id,
                         subject=subject, category=category,
                         subcategory=subcategory, difficulty=difficulty)

# ══════════════════════════════════════════════
# ORQAGA QAYTISH
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("tarix:back:"))
async def tarix_back(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    step  = parts[2]

    if step == 'subjects':
        await safe_edit(callback,
                        "📜 <b>Tarix</b>\n\nQaysi bo'limni tanlaysiz?",
                        reply_markup=tarix_subjects_keyboard())

    elif step == 'cat':
        subject = parts[3]
        label   = get_subject_label(subject)
        await safe_edit(callback,
                        f"<b>{label}</b>\n\nQaysi turdagi testni ishlaysiz?",
                        reply_markup=tarix_category_keyboard(subject))

    elif step == 'topic':
        subject  = parts[3]
        category = parts[4]
        if category == 'mavzu':
            kb = jahon_topics_keyboard() if subject == 'jahon' else uzbekiston_topics_keyboard()
            await safe_edit(callback, "📌 <b>Mavzuni tanlang:</b>", reply_markup=kb)
        elif category == 'sinf':
            await safe_edit(callback, "🏫 <b>Sinfni tanlang:</b>",
                            reply_markup=grades_keyboard(subject))

    await callback.answer()

# ══════════════════════════════════════════════
# ATESTATSIYA (asosiy menyu)
# ══════════════════════════════════════════════

@router.message(F.text == "🎓 Atestatsiya")
async def attestation_menu(message: Message):
    if not await is_registered(message.from_user.id):
        await message.answer("❗ Avval ro'yxatdan o'ting — /start")
        return
    await message.answer(
        "🎓 <b>Atestatsiya</b>\n\nQaysi fan bo'yicha?",
        reply_markup=attestation_subjects_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("attest:sub:"))
async def attestation_subject(callback: CallbackQuery):
    subject = callback.data.split(":")[2]
    tid     = callback.from_user.id
    label   = get_subject_label(subject)

    if await has_attestation(tid, subject):
        fmt = await get_attestation_format(tid, subject)
        if fmt == 'pdf':
            await callback.message.edit_text("📄 PDF versiya hozircha tayyorlanmoqda.")
        else:
            cnt = await count_questions(subject=subject, is_attestation=True)
            if cnt == 0:
                await callback.message.edit_text("❌ Atestatsiya savollari hali qo'shilmagan.")
                await callback.answer()
                return
            questions = await get_questions(subject=subject, is_attestation=True,
                                            count=config.ATTESTATION_COUNT)
            meta = {'subject': subject, 'category': 'attestation',
                    'is_attestation': True, 'solution_url': config.SOLUTION_URL}
            encoded = encode_questions(questions_to_miniapp(questions), meta)
            url = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"
            await callback.message.answer(
                f"🎓 <b>{label} — Atestatsiya</b>\n\n📝 Savollar: <b>{len(questions)} ta</b>",
                reply_markup=miniapp_keyboard(url),
                parse_mode="HTML"
            )
    else:
        await callback.message.edit_text(
            f"🎓 <b>{label} — Atestatsiya</b>\n\n"
            f"Bu test bir martalik sotib olinadi.\n"
            f"💰 Narxi: <b>{config.PRICE_ATTESTATION:,} so'm</b>",
            reply_markup=attestation_buy_keyboard(subject),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("attest:format:"))
async def attestation_format(callback: CallbackQuery):
    parts   = callback.data.split(":")
    fmt     = parts[2]
    subject = parts[3] if len(parts) > 3 else 'jahon'
    tid     = callback.from_user.id
    label   = get_subject_label(subject)
    await grant_attestation(tid, subject, fmt)

    if fmt == 'pdf':
        await callback.message.edit_text("📄 PDF versiya hozircha tayyorlanmoqda.")
    else:
        cnt = await count_questions(subject=subject, is_attestation=True)
        if cnt == 0:
            await callback.message.edit_text("❌ Atestatsiya savollari hali qo'shilmagan.")
            await callback.answer()
            return
        questions = await get_questions(subject=subject, is_attestation=True,
                                        count=config.ATTESTATION_COUNT)
        meta = {'subject': subject, 'category': 'attestation',
                'is_attestation': True, 'solution_url': config.SOLUTION_URL}
        encoded = encode_questions(questions_to_miniapp(questions), meta)
        url = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"
        await callback.message.answer(
            f"🎓 <b>{label} — Atestatsiya</b>\n\n📝 Savollar: <b>{len(questions)} ta</b>",
            reply_markup=miniapp_keyboard(url),
            parse_mode="HTML"
        )
    await callback.answer()

# ══════════════════════════════════════════════
# NATIJA (Mini App dan)
# ══════════════════════════════════════════════

@router.message(F.web_app_data)
async def webapp_result(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        await save_test_result(
            telegram_id    = message.from_user.id,
            subject        = data.get('subject', 'jahon'),
            category       = data.get('category', 'aralash'),
            subcategory    = data.get('subcategory'),
            difficulty     = data.get('difficulty'),
            is_attestation = data.get('is_attestation', False),
            correct        = data.get('correct', 0),
            wrong          = data.get('wrong', 0),
            skipped        = data.get('skip', 0),
        )
        pct     = data.get('score', 0)
        correct = data.get('correct', 0)
        total   = data.get('total', 0)
        if pct >= 90:   emoji, baho = "🏆", "A'lo (5)"
        elif pct >= 70: emoji, baho = "🎉", "Yaxshi (4)"
        elif pct >= 50: emoji, baho = "📚", "Qoniqarli (3)"
        else:           emoji, baho = "😔", "Qoniqarsiz (2)"
        await message.answer(
            f"{emoji} <b>Test yakunlandi!</b>\n\n"
            f"✅ To'g'ri: <b>{correct}</b> / {total}\n"
            f"📊 Natija: <b>{pct}%</b>\n"
            f"📝 Baho: <b>{baho}</b>",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Natijani saqlashda xato: {e}")