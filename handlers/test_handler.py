from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.db import (
    is_registered, get_access_status, mark_free_used,
    has_attestation, get_attestation_format,
    get_questions, count_questions
)
from keyboards.keyboards import (
    tarix_category_keyboard, tarix_topics_keyboard,
    grades_keyboard, difficulty_keyboard,
    retry_buy_keyboard, attestation_buy_keyboard,
    attestation_format_keyboard, miniapp_keyboard,
    main_menu_keyboard
)
from config import config

router = Router()

import json, base64, zlib

def encode_questions(q_list: list, meta: dict = None) -> str:
    payload = {'meta': meta or {}, 'questions': q_list}
    raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    compressed = zlib.compress(raw.encode('utf-8'), level=9)
    return base64.urlsafe_b64encode(compressed).decode('ascii')

def questions_to_miniapp(questions: list) -> list:
    return [
        {
            "id":  q.id,
            "t":   q.question_text,
            "a":   q.option_a,
            "b":   q.option_b,
            "c":   q.option_c,
            "d":   q.option_d,
            "ok":  q.correct_answer,
            "img": q.image_file_id or ""
        }
        for q in questions
    ]

def make_access_key(subject, category, subcategory=None, difficulty=None):
    return f"{subject}:{category}:{subcategory}:{difficulty}"

async def safe_edit(callback: CallbackQuery, text: str, reply_markup=None):
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        pass

async def launch_miniapp(callback: CallbackQuery, tid: int,
                         subject: str, category: str,
                         subcategory: str = None, difficulty: str = None,
                         is_attestation: bool = False):
    """Savollarni yuklash va Mini App ni ochish"""
    if not await is_registered(tid):
        await callback.message.answer(
            "❗ Avval ro'yxatdan o'ting — /start",
            reply_markup=main_menu_keyboard()
        )
        await callback.answer()
        return

    cnt = await count_questions(
        subject=subject, category=category,
        subcategory=subcategory, difficulty=difficulty,
        is_attestation=is_attestation
    )

    if cnt == 0:
        await safe_edit(callback,
            f"❌ <b>Savollar topilmadi!</b>\n\n"
            f"Bu bo'limda hali savollar yo'q.\n"
            f"Admin tez orada qo'shadi 🙏"
        )
        await callback.answer()
        return

    # Bepul / to'lov tekshirish
    if not is_attestation:
        access_key = make_access_key(subject, category, subcategory, difficulty)
        status = await get_access_status(tid, access_key)

        if status == 'buy':
            await safe_edit(callback,
                f"💳 <b>Bu test uchun to'lov talab qilinadi</b>\n\n"
                f"💰 Narxi: <b>{config.PRICE_RETRY:,} so'm</b>\n\n"
                f"To'lov qilganingizdan so'ng test ishlashingiz mumkin.",
                reply_markup=retry_buy_keyboard(access_key)
            )
            await callback.answer()
            return
    else:
        if not await has_attestation(tid, subject):
            await safe_edit(callback,
                f"🎓 <b>Atestatsiya testi</b>\n\n"
                f"💰 Narxi: <b>{config.PRICE_ATTESTATION:,} so'm</b> (bir martalik)",
                reply_markup=attestation_buy_keyboard(subject)
            )
            await callback.answer()
            return

    # Savollarni yuklash
    questions = await get_questions(
        subject=subject, category=category,
        subcategory=subcategory, difficulty=difficulty,
        is_attestation=is_attestation,
        count=config.ATTESTATION_COUNT if is_attestation else min(cnt, config.ATTESTATION_COUNT)
    )

    if not is_attestation:
        access_key = make_access_key(subject, category, subcategory, difficulty)
        await mark_free_used(tid, access_key)

    meta = {
        'subject':        subject,
        'category':       category,
        'subcategory':    subcategory,
        'difficulty':     difficulty,
        'is_attestation': is_attestation,
        'solution_url':   config.SOLUTION_URL,
    }

    encoded = encode_questions(questions_to_miniapp(questions), meta)
    url = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"

    SUBJ  = {'tarix': '📜 Tarix'}
    DIFF  = {'easy': '🟢 Oson', 'medium': "🟡 O'rta", 'hard': '🔴 Qiyin'}
    TOPIC = config.TARIX_TOPICS

    subj_label = SUBJ.get(subject, subject)
    diff_label = DIFF.get(difficulty, '') if difficulty else ''
    sub_label  = TOPIC.get(subcategory, subcategory) if subcategory else (subcategory or '')

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
# TARIX — asosiy handler
# ══════════════════════════════════════════════

@router.message(F.text == "📜 Tarix")
async def tarix_menu(message: Message, state: FSMContext):
    tid = message.from_user.id
    if not await is_registered(tid):
        await message.answer("❗ Avval ro'yxatdan o'ting — /start")
        return
    await message.answer(
        "📜 <b>Tarix</b>\n\nQaysi turdagi testni ishlaysiz?",
        reply_markup=tarix_category_keyboard(),
        parse_mode="HTML"
    )

# Kategoriya tanlash
@router.callback_query(F.data.startswith("tarix:cat:"))
async def tarix_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[2]
    tid = callback.from_user.id
    await state.update_data(subject='tarix', category=category)

    if category == 'mavzu':
        await safe_edit(callback,
            "📌 <b>Mavzuni tanlang:</b>",
            reply_markup=tarix_topics_keyboard()
        )
    elif category == 'sinf':
        await safe_edit(callback,
            "🏫 <b>Sinfni tanlang:</b>",
            reply_markup=grades_keyboard('tarix')
        )
    elif category == 'aralash':
        await safe_edit(callback,
            "🔀 <b>Aralash test</b>\n\nQiyinlik darajasini tanlang:",
            reply_markup=difficulty_keyboard('tarix', 'aralash')
        )
    elif category == 'attestation':
        if not await has_attestation(tid, 'tarix'):
            await safe_edit(callback,
                f"🎓 <b>Atestatsiya testi</b>\n\n"
                f"💰 Narxi: <b>{config.PRICE_ATTESTATION:,} so'm</b> (bir martalik)",
                reply_markup=attestation_buy_keyboard('tarix')
            )
        else:
            fmt = await get_attestation_format(tid, 'tarix')
            if fmt == 'pdf':
                await callback.message.answer("📄 PDF versiya hozircha tayyorlanmoqda.")
            else:
                await launch_miniapp(callback, tid,
                    'tarix', 'attestation', is_attestation=True)
            return
    await callback.answer()

# Mavzu tanlash
@router.callback_query(F.data.regexp(r'^tarix:topic:[^:]+$'))
async def tarix_topic(callback: CallbackQuery, state: FSMContext):
    topic = callback.data.split(":")[2]
    await state.update_data(subcategory=topic)
    await safe_edit(callback,
        f"🎯 <b>{config.TARIX_TOPICS.get(topic, topic)}</b>\n\nQiyinlik darajasini tanlang:",
        reply_markup=difficulty_keyboard('tarix', 'mavzu', topic)
    )
    await callback.answer()

# Sinf tanlash
@router.callback_query(F.data.regexp(r'^tarix:grade:\d+$'))
async def tarix_grade(callback: CallbackQuery, state: FSMContext):
    grade = callback.data.split(":")[2]
    await state.update_data(subcategory=grade)
    await safe_edit(callback,
        f"🏫 <b>{config.GRADES.get(grade, grade)}</b>\n\nQiyinlik darajasini tanlang:",
        reply_markup=difficulty_keyboard('tarix', 'sinf', grade)
    )
    await callback.answer()

# Qiyinlik tanlash → Mini App ochish
@router.callback_query(F.data.startswith("tarix:diff:"))
async def tarix_difficulty(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    # tarix:diff:category:subcategory:difficulty
    category   = parts[2]
    subcategory = parts[3] if parts[3] else None
    difficulty  = parts[4]
    tid = callback.from_user.id

    await launch_miniapp(
        callback, tid,
        subject='tarix',
        category=category,
        subcategory=subcategory,
        difficulty=difficulty
    )

# ══════════════════════════════════════════════
# ATESTATSIYA
# ══════════════════════════════════════════════

@router.message(F.text == "🎓 Atestatsiya")
async def attestation_menu(message: Message):
    tid = message.from_user.id
    if not await is_registered(tid):
        await message.answer("❗ Avval ro'yxatdan o'ting — /start")
        return

    if await has_attestation(tid, 'tarix'):
        fmt = await get_attestation_format(tid, 'tarix')
        if fmt == 'pdf':
            await message.answer("📄 PDF versiya hozircha tayyorlanmoqda.")
        else:
            cnt = await count_questions(subject='tarix', is_attestation=True)
            if cnt == 0:
                await message.answer("❌ Atestatsiya savollari hali qo'shilmagan.")
                return
            questions = await get_questions(
                subject='tarix', is_attestation=True,
                count=config.ATTESTATION_COUNT
            )
            meta = {
                'subject': 'tarix', 'category': 'attestation',
                'is_attestation': True, 'solution_url': config.SOLUTION_URL,
            }
            encoded = encode_questions(questions_to_miniapp(questions), meta)
            url = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"
            await message.answer(
                f"🎓 <b>Atestatsiya testi</b>\n\n"
                f"📝 Savollar: <b>{len(questions)} ta</b>",
                reply_markup=miniapp_keyboard(url),
                parse_mode="HTML"
            )
    else:
        await message.answer(
            f"🎓 <b>Atestatsiya testi</b>\n\n"
            f"Bu test bir martalik sotib olinadi.\n"
            f"💰 Narxi: <b>{config.PRICE_ATTESTATION:,} so'm</b>",
            reply_markup=attestation_buy_keyboard('tarix'),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("attest:format:"))
async def attestation_format(callback: CallbackQuery):
    fmt = callback.data.split(":")[2]
    tid = callback.from_user.id
    if fmt == 'pdf':
        await callback.message.edit_text("📄 PDF versiya hozircha tayyorlanmoqda.")
    else:
        cnt = await count_questions(subject='tarix', is_attestation=True)
        if cnt == 0:
            await callback.message.edit_text("❌ Atestatsiya savollari hali qo'shilmagan.")
            await callback.answer()
            return
        questions = await get_questions(
            subject='tarix', is_attestation=True,
            count=config.ATTESTATION_COUNT
        )
        meta = {
            'subject': 'tarix', 'category': 'attestation',
            'is_attestation': True, 'solution_url': config.SOLUTION_URL,
        }
        encoded = encode_questions(questions_to_miniapp(questions), meta)
        url = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"
        await callback.message.answer(
            f"🎓 <b>Atestatsiya testi</b>\n\n📝 Savollar: <b>{len(questions)} ta</b>",
            reply_markup=miniapp_keyboard(url),
            parse_mode="HTML"
        )
    await callback.answer()

# ══════════════════════════════════════════════
# NATIJA QABUL QILISH (Mini App dan)
# ══════════════════════════════════════════════

from aiogram.types import Message as TgMessage
from database.db import save_test_result

@router.message(F.web_app_data)
async def webapp_result(message: TgMessage):
    try:
        data = json.loads(message.web_app_data.data)
        tid  = message.from_user.id

        await save_test_result(
            telegram_id    = tid,
            subject        = data.get('subject', 'tarix'),
            category       = data.get('category', 'aralash'),
            subcategory    = data.get('subcategory'),
            difficulty     = data.get('difficulty'),
            is_attestation = data.get('is_attestation', False),
            total          = data.get('total', 0),
            correct        = data.get('correct', 0),
            wrong          = data.get('wrong', 0),
            skipped        = data.get('skip', 0),
            score          = data.get('score', 0),
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
