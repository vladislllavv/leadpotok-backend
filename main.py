# Добавь импорты в начало
from parsers.vk_parser import VKParser
from parsers.vk_ai_filter import VKAIFilter

# ... (существующий код)

@app.post("/api/admin/parse/vk")
async def trigger_vk_parse(x_admin_key: str = Header(None)):
    """Запускает парсинг VK групп"""
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Неверный ключ")
    
    async def run_vk_parser():
        try:
            parser = VKParser()
            ai_filter = VKAIFilter()
            
            leads = await parser.parse_all_groups()
            
            db = next(get_db())
            new_leads_count = 0
            
            for lead in leads:
                # AI фильтрация
                is_valid, score = ai_filter.filter_lead(lead)
                
                if not is_valid or score < 60:
                    print(f"⚠️ Отфильтровано (score: {score})")
                    continue
                
                # Проверяем дубли
                if not is_duplicate(db, lead.get('phone', ''), lead.get('company', '')):
                    # Добавляем score в reason
                    lead['reason'] = f"[Score: {score}/100] {lead['reason']}"
                    lead['hot_level'] = 'hot' if score >= 80 else 'warm'
                    
                    add_lead(db, **lead)
                    new_leads_count += 1
                    
                    # 🔔 ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ В TELEGRAM
                    if score >= 80:  # Только очень горячие
                        await send_telegram_notification(lead, score)
            
            db.close()
            print(f"✅ VK парсинг завершён. Добавлено: {new_leads_count}")
            
        except Exception as e:
            print(f"❌ Ошибка VK парсинга: {e}")
    
    asyncio.create_task(run_vk_parser())
    return {"status": "started", "message": "VK парсинг запущен"}

# Функция отправки уведомлений
async def send_telegram_notification(lead: dict, score: int):
    """Отправляет уведомление в Telegram о новой заявке"""
    try:
        from aiogram import Bot
        
        bot_token = os.getenv("BOT_TOKEN")
        admin_id = os.getenv("ADMIN_ID")
        
        if not bot_token or not admin_id:
            return
        
        bot = Bot(token=bot_token)
        
        message = f"""
🔥 <b>НОВАЯ ЗАЯВКА ИЗ VK!</b> (Score: {score}/100)

📝 <b>Текст:</b>
{lead['reason'][:300]}

📞 <b>Контакты:</b>
{lead.get('phone', 'Нет телефона')}
{lead.get('contact', 'Нет Telegram')}

🔗 <a href="{lead['source'].replace('vk:', 'https://')}">Открыть пост</a>
        """.strip()
        
        await bot.send_message(
            chat_id=admin_id,
            text=message,
            parse_mode='HTML'
        )
        
        await bot.session.close()
        
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")
