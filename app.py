import os
import json
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, render_template
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

app = Flask(__name__)

# ========== الإعدادات ==========
TOKEN = os.environ.get("BOT_TOKEN", "ضع_التوكن_هنا")
PORT = int(os.environ.get("PORT", 5000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")  # سنضيفه لاحقاً من Railway

# ========== تحميل المصادر ==========
with open('sources.json', 'r', encoding='utf-8') as f:
    trusted_sources = json.load(f)

# ========== أيقونات المجالات ==========
domain_icons = {
    'health': '🏥', 'tech': '💻', 'academic': '📚', 'cooking': '🍳',
    'news': '📰', 'books': '📚', 'poetry': '🎭', 'dictionary': '📖',
    'ai': '🤖', 'ai_tools': '🛠️', 'youtube': '▶️', 'sports': '⚽',
    'animals': '🦁', 'games': '🎮', 'design': '🎨', 'religion': '🕌',
    'education': '🎓', 'jobs': '💼', 'shopping': '🛒', 'cars': '🚗',
    'travel': '✈️', 'general': '🌐'
}

# ========== أسماء المجالات بالعربي ==========
domain_names = {
    'health': 'الصحة', 'tech': 'تقنية', 'academic': 'أكاديمي', 'cooking': 'طبخ',
    'news': 'أخبار', 'books': 'كتب', 'poetry': 'شعر', 'dictionary': 'قاموس',
    'ai': 'ذكاء اصطناعي', 'ai_tools': 'أدوات ذكاء', 'youtube': 'يوتيوب', 'sports': 'رياضة',
    'animals': 'حيوانات', 'games': 'ألعاب', 'design': 'تصميم', 'religion': 'دين',
    'education': 'تعليم', 'jobs': 'وظائف', 'shopping': 'تسوق', 'cars': 'سيارات',
    'travel': 'سياحة', 'general': 'عام'
}

# ========== أدوات الذكاء الاصطناعي ==========
ai_direct_links = {
    'deepseek': {'title': 'DeepSeek - مساعد ذكاء اصطناعي', 'url': 'https://chat.deepseek.com', 'desc': 'اسأل DeepSeek مباشرة'},
    'chatgpt': {'title': 'ChatGPT - OpenAI', 'url': 'https://chat.openai.com', 'desc': 'اسأل ChatGPT مباشرة'},
    'gemini': {'title': 'Gemini - Google AI', 'url': 'https://gemini.google.com', 'desc': 'اسأل Gemini مباشرة'},
    'perplexity': {'title': 'Perplexity AI', 'url': 'https://perplexity.ai', 'desc': 'اسأل Perplexity مباشرة'},
    'claude': {'title': 'Claude - Anthropic', 'url': 'https://claude.ai', 'desc': 'اسأل Claude مباشرة'}
}

# ========== تصنيف المجال ==========
def classify_domain(query):
    q = query.lower()
    if any(w in q for w in ['مرض', 'علاج', 'طبيب', 'صحة', 'دواء', 'اعراض', 'الم', 'جراحة']): return 'health'
    elif any(w in q for w in ['كود', 'برمجة', 'هاتف', 'تقنية', 'تطبيق', 'برنامج', 'كمبيوتر']): return 'tech'
    elif any(w in q for w in ['كتاب', 'رواية', 'مؤلف', 'تحميل', 'pdf', 'مكتبة', 'قراءة']): return 'books'
    elif any(w in q for w in ['شعر', 'قصيدة', 'ديوان', 'شاعر', 'أدب', 'نثر', 'بلاغة']): return 'poetry'
    elif any(w in q for w in ['معنى', 'تعريف', 'قاموس', 'ترجمة', 'مرادف', 'ضد', 'لغة']): return 'dictionary'
    elif any(w in q for w in ['ذكاء', 'اصطناعي', 'ai', 'تعلم آلي', 'شبكة عصبية', 'deepseek', 'chatgpt']): return 'ai'
    elif any(w in q for w in ['فيديو', 'يوتيوب', 'youtube', 'مقطع']): return 'youtube'
    elif any(w in q for w in ['كرة', 'مباراة', 'دوري', 'هدف', 'رياضة', 'نادي', 'ملعب', 'بطولة']): return 'sports'
    elif any(w in q for w in ['حيوان', 'طائر', 'أسد', 'فيل', 'قطة', 'كلب', 'زواحف', 'سمك']): return 'animals'
    elif any(w in q for w in ['لعبة', 'العب', 'ألعاب', 'poki', 'تسلية', 'y8', 'friv']): return 'games'
    elif any(w in q for w in ['تصميم', 'ديكور', 'فكرة', 'إبداع', 'رسم', 'أزياء', 'موضة', 'شعار', 'جرافيك', 'pinterest']): return 'design'
    elif any(w in q for w in ['قرآن', 'حديث', 'فتوى', 'صلاة', 'حج', 'زكاة', 'دعاء', 'إسلام', 'دين']): return 'religion'
    elif any(w in q for w in ['دورة', 'منهج', 'امتحان', 'شهادة', 'جامعة', 'مدرسة', 'تعلم']): return 'education'
    elif any(w in q for w in ['توظيف', 'راتب', 'سيرة ذاتية', 'مقابلة', 'مهندس', 'وظيفة']): return 'jobs'
    elif any(w in q for w in ['سعر', 'شراء', 'خصم', 'منتج', 'توصيل', 'طلب', 'ماركة', 'تسوق']): return 'shopping'
    elif any(w in q for w in ['سيارة', 'مرسيدس', 'تويوتا', 'بيع سيارة', 'مواصفات']): return 'cars'
    elif any(w in q for w in ['سفر', 'فندق', 'حجز', 'تذكرة', 'سياحة', 'رحلة']): return 'travel'
    elif any(w in q for w in ['خبر', 'اخبار', 'عاجل', 'سياسة', 'اقتصاد', 'انتخابات']): return 'news'
    elif any(w in q for w in ['وصفة', 'طبخ', 'طعام', 'اكل', 'حلويات', 'عشاء', 'غداء']): return 'cooking'
    elif any(w in q for w in ['تاريخ', 'فلسفة', 'علم', 'فيزياء', 'كيمياء', 'رياضيات', 'بحث']): return 'academic'
    else: return 'general'

# ========== جلب النتائج ==========
def fetch_results(query, domain):
    sources = trusted_sources.get(domain, trusted_sources['general'])[:5]
    results = []
    for source in sources:
        try:
            url = f"https://html.duckduckgo.com/html/?q=site:{source}+{query}"
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; BaseetBot/1.0)'}
            response = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            for item in soup.select('.result')[:2]:
                title_tag = item.select_one('.result__title')
                snippet_tag = item.select_one('.result__snippet')
                link_tag = item.select_one('.result__url')
                if title_tag and link_tag:
                    title = title_tag.get_text(strip=True)
                    snippet = snippet_tag.get_text(strip=True)[:200] if snippet_tag else ''
                    link = link_tag.get('href', '')
                    if 'uddg=' in link:
                        link = link.split('uddg=')[-1].split('&')[0]
                    results.append({'title': title, 'summary': snippet, 'url': link, 'source': source})
        except Exception as e:
            print(f"خطأ من {source}: {e}")
            continue
    seen = set()
    unique = []
    for r in results:
        if r['url'] not in seen:
            seen.add(r['url'])
            unique.append(r)
    return unique[:10]

# ========== تخزين جلسات المستخدمين ==========
user_sessions = {}

# ========== بوت تيليغرام ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 افتح بسيط", web_app={"url": WEBHOOK_URL})],
        [InlineKeyboardButton("📖 ويكيبيديا", url="https://ar.wikipedia.org")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🍃 أهلاً بك في <b>بسِـــيط</b>\n"
        "محرك البحث الخفيف والسريع\n\n"
        "✍️ <b>اكتب كلمة البحث مباشرة</b> (25 حرف كحد أقصى)\n"
        "🔍 سأحلل طلبك وأعطيك أفضل 10 نتائج من مصادر موثوقة\n\n"
        "🛠️ <b>أدوات ذكاء اصطناعي:</b>\n"
        "DeepSeek | ChatGPT | Gemini | Perplexity\n\n"
        "📚 <b>مجالات البحث:</b> صحة، تقنية، كتب، شعر، قاموس، دين، تعليم، وظائف، تسوق، سيارات، سياحة، رياضة، حيوانات، ألعاب، تصميم، طبخ، أخبار، أكاديمي\n\n"
        "للبحث مجدداً: /start"
    )
    await update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()[:25]
    user_id = update.effective_user.id
    
    if len(query) < 2:
        await update.message.reply_text("⚠️ الرجاء كتابة كلمة بحث أطول (حرفين على الأقل)")
        return
    
    # التحقق من الروابط المباشرة لأدوات الذكاء الاصطناعي
    query_lower = query.lower()
    for key, info in ai_direct_links.items():
        if key in query_lower:
            text = (
                f"🛠️ <b>رابط مباشر</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📌 <b>{info['title']}</b>\n"
                f"💬 {info['desc']}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔗 <a href='{info['url']}'>افتح {key} ←</a>"
            )
            await update.message.reply_text(
                text, parse_mode='HTML', disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🔗 افتح {key}", url=info['url']),
                    InlineKeyboardButton("🔄 بحث جديد", callback_data="new_search")
                ]])
            )
            return
    
    # رسالة جاري البحث
    status_msg = await update.message.reply_text("🔍 جاري البحث في المصادر الموثوقة...")
    
    # تحليل وجلب
    domain = classify_domain(query)
    icon = domain_icons.get(domain, '🌐')
    domain_name = domain_names.get(domain, 'عام')
    results = fetch_results(query, domain)
    
    await status_msg.delete()
    
    if not results:
        await update.message.reply_text(
            f"🍃 لا توجد نتائج لـ <b>{query}</b>\n"
            f"المجال: {icon} {domain_name}\n"
            "جرب صياغة مختلفة أو كلمة أعم.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 بحث جديد", callback_data="new_search")
            ]])
        )
        return
    
    # تخزين الجلسة
    user_sessions[user_id] = {
        'results': results,
        'current': 0,
        'query': query,
        'domain': domain,
        'icon': icon
    }
    
    await show_result(update, context, user_id, 0)

async def show_result(update, context, user_id, index):
    session = user_sessions.get(user_id)
    if not session: return
    
    results = session['results']
    total = len(results)
    r = results[index]
    
    domain_name = domain_names.get(session['domain'], 'عام')
    
    text = (
        f"{session['icon']} <b>[{index+1}/{total}]</b> • {r['source']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>{r['title']}</b>\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"💬 {r['summary'] or 'لا يوجد ملخص'}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <a href='{r['url']}'>فتح الرابط ←</a>"
    )
    
    buttons = []
    nav_row = []
    if index > 0: nav_row.append(InlineKeyboardButton("◀️", callback_data=f"prev_{index}"))
    nav_row.append(InlineKeyboardButton(f"📋 {index+1}/{total}", callback_data="ignore"))
    if index < total - 1: nav_row.append(InlineKeyboardButton("▶️", callback_data=f"next_{index}"))
    buttons.append(nav_row)
    buttons.append([
        InlineKeyboardButton("🔄 بحث جديد", callback_data="new_search"),
        InlineKeyboardButton("🔗 فتح الرابط", url=r['url'])
    ])
    buttons.append([
        InlineKeyboardButton("🔍 افتح في التطبيق", web_app={"url": WEBHOOK_URL})
    ])
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)
    else:
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data
    
    if data == "new_search":
        session = user_sessions.get(user_id)
        if session:
            await query.edit_message_text(
                f"✍️ بحث جديد بدل: <b>{session['query']}</b>\nاكتب كلمة البحث الجديدة (25 حرف كحد أقصى).",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text("✍️ اكتب كلمة البحث الجديدة (25 حرف كحد أقصى).")
        return
    if data == "ignore": return
    if data.startswith("next_") or data.startswith("prev_"):
        session = user_sessions.get(user_id)
        if not session:
            await query.edit_message_text("⚠️ انتهت الجلسة. ابحث مجدداً: /start")
            return
        current = int(data.split("_")[1])
        new_index = current + 1 if data.startswith("next_") else current - 1
        if 0 <= new_index < len(session['results']):
            session['current'] = new_index
            await show_result(update, context, user_id, new_index)

# ========== تشغيل البوت ==========
def run_bot():
    app_bot = Application.builder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_bot.add_handler(CallbackQueryHandler(handle_callback))
    print("🤖 بوت بسِـــيط يعمل الآن...")
    app_bot.run_polling()

# ========== Flask Routes ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()[:25]
    if not query: return jsonify([])
    
    # أدوات AI مباشرة
    query_lower = query.lower()
    for key, info in ai_direct_links.items():
        if key in query_lower:
            return jsonify([{'title': info['title'], 'summary': info['desc'], 'url': info['url'], 'source': 'AI Tool'}])
    
    domain = classify_domain(query)
    results = fetch_results(query, domain)
    return jsonify(results)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'name': 'بسِـــيط - Baseet'})

# ========== تشغيل Flask + Bot معاً ==========
if __name__ == '__main__':
    # تشغيل البوت في خيط منفصل
    bot_thread = Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # تشغيل Flask
    app.run(host='0.0.0.0', port=PORT)
