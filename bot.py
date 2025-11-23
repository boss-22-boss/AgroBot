"""
AGRO Bot - Безопасная версия для Render
Все секреты в переменных окружения, защита от утечек данных
"""

import os
import sys
import logging
import threading
import time
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== БЕЗОПАСНОЕ ЛОГИРОВАНИЕ ====================
class SecureFormatter(logging.Formatter):
    """Кастомный форматтер, который скрывает чувствительные данные"""
    
    def format(self, record):
        # Получаем оригинальное сообщение
        original = super().format(record)
        
        # Список чувствительных данных для замены
        sensitive_data = []
        
        # Добавляем токен бота
        if BOT_TOKEN and len(BOT_TOKEN) > 10:
            sensitive_data.append(BOT_TOKEN)
        
        # Добавляем ADMIN_SECRET
        if ADMIN_SECRET and len(ADMIN_SECRET) > 5:
            sensitive_data.append(ADMIN_SECRET)
        
        # Заменяем чувствительные данные на ***
        result = original
        for secret in sensitive_data:
            if secret in result:
                result = result.replace(secret, '***HIDDEN***')
        
        return result

# Настройка логирования с безопасным форматтером
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(SecureFormatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Отключаем логи библиотек, которые могут выводить чувствительные данные
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('telebot').setLevel(logging.WARNING)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '')
WEBAPP_URL = os.getenv('WEBAPP_URL', '')
RENDER_URL = os.getenv('RENDER_URL', '')
PORT = int(os.getenv('PORT', '10000'))
TRIGGER_HASHTAG = os.getenv('TRIGGER_HASHTAG', '#агрорф')

# 🔒 Секретный ключ для защиты служебных эндпоинтов
ADMIN_SECRET = os.getenv('ADMIN_SECRET', 'change_me_in_production')

# Проверка переменных (БЕЗ вывода значений!)
if not all([BOT_TOKEN, ADMIN_ID, CHANNEL_USERNAME, WEBAPP_URL, RENDER_URL]):
    logger.error("❌ Не все переменные окружения установлены!")
    logger.error("Проверьте: BOT_TOKEN, ADMIN_ID, CHANNEL_USERNAME, WEBAPP_URL, RENDER_URL")
    sys.exit(1)

# Проверка секретного ключа
if ADMIN_SECRET == 'change_me_in_production':
    logger.warning("⚠️ ADMIN_SECRET не установлен! Используйте надёжный ключ в production")

logger.info("=" * 70)
logger.info("✅ КОНФИГУРАЦИЯ ЗАГРУЖЕНА")
logger.info(f"📢 Канал: {CHANNEL_USERNAME}")
logger.info(f"🔐 Секретный ключ: {'✅ установлен' if ADMIN_SECRET != 'change_me_in_production' else '⚠️ по умолчанию'}")
logger.info("=" * 70)

# ==================== БОТ ====================
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Временное хранилище для пересланных сообщений
forwarded_messages = {}

def is_admin(message):
    """Проверка админа"""
    return message.from_user.id == ADMIN_ID

def create_markup():
    """Создание кнопки с ссылкой на WebApp"""
    markup = InlineKeyboardMarkup()
    info_button = InlineKeyboardButton(
        text="Каталог продукции",
        url=WEBAPP_URL
    )
    markup.row(info_button)
    return markup

def safe_log_user_info(message):
    """Безопасное логирование информации о пользователе"""
    # Логируем только факт взаимодействия, БЕЗ username и ID
    return "админ" if is_admin(message) else "неавторизованный пользователь"

# ==================== HANDLERS ====================

@bot.message_handler(func=lambda message: not is_admin(message))
def handle_unauthorized(message):
    """Удаляем сообщения от не-админов"""
    logger.warning("⚠️ Попытка неавторизованного доступа (детали скрыты)")
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

@bot.message_handler(commands=['start'])
def cmd_start(message):
    """Команда /start"""
    if not is_admin(message):
        return
    
    logger.info(f"🔔 /start от {safe_log_user_info(message)}")
    
    text = (
        f"✅ <b>Привет, админ!</b>\n\n"
        f"📋 <b>Как публиковать:</b>\n"
        f"1️⃣ Отправь пост (текст/фото/видео)\n"
        f"2️⃣ Добавь хэштег <code>{TRIGGER_HASHTAG}</code>\n"
        f"3️⃣ Пост опубликуется с кнопкой!\n\n"
        f"<b>Или:</b>\n"
        f"• Перешли сообщения в бот\n"
        f"• Они автоматически опубликуются в канале\n\n"
        f"📢 Канал: {CHANNEL_USERNAME}\n\n"
        f"<b>Команды:</b>\n"
        f"/start - Это сообщение\n"
        f"/status - Статус бота"
    )
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(commands=['status'])
def cmd_status(message):
    """Команда /status"""
    if not is_admin(message):
        return
    
    try:
        bot.get_chat(CHANNEL_USERNAME)
        channel_status = "✅ Подключён"
    except Exception as e:
        channel_status = f"❌ Ошибка подключения"
        logger.error(f"Ошибка проверки канала: {str(e)}")
    
    text = (
        f"🤖 <b>Статус бота</b>\n\n"
        f"<b>Канал:</b> {CHANNEL_USERNAME}\n"
        f"<b>Статус:</b> {channel_status}\n"
        f"<b>Триггер:</b> <code>{TRIGGER_HASHTAG}</code>\n\n"
        f"✅ Бот активен и готов к работе"
    )
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', disable_web_page_preview=True)

@bot.message_handler(content_types=[
    'text', 'photo', 'video', 'document', 
    'audio', 'voice', 'video_note', 'animation', 'sticker'
])
def handle_all_messages(message):
    """Обработка всех сообщений"""
    if not is_admin(message):
        return
    
    user_id = message.from_user.id
    
    # ==================== ПЕРЕСЛАННЫЕ СООБЩЕНИЯ ====================
    if message.forward_date or message.forward_from or message.forward_from_chat:
        logger.info(f"📨 Получено пересланное сообщение от {safe_log_user_info(message)}")
        
        # Инициализируем буфер
        if user_id not in forwarded_messages:
            forwarded_messages[user_id] = []
        
        # Добавляем в буфер
        forwarded_messages[user_id].append(message)
        
        # Удаляем из чата с ботом
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        
        # Запускаем обработку группы
        def process_forwarded_group():
            time.sleep(1)  # Ждём 1 секунду
            
            if user_id in forwarded_messages and forwarded_messages[user_id]:
                messages_to_send = forwarded_messages[user_id].copy()
                forwarded_messages[user_id] = []
                
                sent_message_ids = []
                
                try:
                    # Пересылаем все
                    for msg in messages_to_send:
                        sent_msg = bot.forward_message(
                            chat_id=CHANNEL_USERNAME,
                            from_chat_id=msg.chat.id,
                            message_id=msg.message_id
                        )
                        sent_message_ids.append(sent_msg.message_id)
                    
                    logger.info(f"✅ Переслано {len(sent_message_ids)} сообщений в канал")
                    
                    # Добавляем кнопку к последнему
                    if sent_message_ids:
                        last_msg_id = sent_message_ids[-1]
                        try:
                            bot.edit_message_reply_markup(
                                chat_id=CHANNEL_USERNAME,
                                message_id=last_msg_id,
                                reply_markup=create_markup()
                            )
                            logger.info("✅ Кнопка добавлена к последнему сообщению")
                        except Exception as e:
                            logger.warning(f"⚠️ Не удалось добавить кнопку, отправляю отдельно")
                            # Отправляем отдельно
                            bot.send_message(
                                chat_id=CHANNEL_USERNAME,
                                text="👆 Смотрите выше",
                                reply_markup=create_markup()
                            )
                
                except Exception as e:
                    logger.error(f"❌ Ошибка пересылки сообщений")
        
        # Запускаем в отдельном потоке
        threading.Thread(target=process_forwarded_group, daemon=True).start()
    
    # ==================== ОБЫЧНЫЕ СООБЩЕНИЯ С ХЭШТЕГОМ ====================
    else:
        caption = message.caption if message.caption else ""
        text = message.text if message.text else ""
        full_text = (caption + text).lower()
        
        if TRIGGER_HASHTAG.lower() in full_text:
            logger.info(f"📤 Публикация поста с хэштегом {TRIGGER_HASHTAG}")
            
            try:
                # Копируем в канал
                sent_msg = bot.copy_message(
                    chat_id=CHANNEL_USERNAME,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    disable_notification=True
                )
                
                logger.info(f"✅ Пост скопирован в канал")
                
                # Добавляем кнопку
                try:
                    bot.edit_message_reply_markup(
                        chat_id=CHANNEL_USERNAME,
                        message_id=sent_msg.message_id,
                        reply_markup=create_markup()
                    )
                    logger.info("✅ Кнопка добавлена к посту")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось добавить кнопку, отправляю отдельно")
                    # Отправляем отдельно
                    bot.send_message(
                        chat_id=CHANNEL_USERNAME,
                        text="👆 Смотрите пост выше",
                        reply_markup=create_markup()
                    )
                
                # Удаляем оригинал
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                except:
                    pass
                
                # Уведомление
                success_msg = bot.send_message(
                    message.chat.id,
                    "✅ <b>Пост опубликован!</b>",
                    parse_mode='HTML'
                )
                
                # Удаляем уведомление через 3 секунды
                def delete_notification():
                    time.sleep(3)
                    try:
                        bot.delete_message(success_msg.chat.id, success_msg.message_id)
                    except:
                        pass
                
                threading.Thread(target=delete_notification, daemon=True).start()
                
            except Exception as e:
                logger.error(f"❌ Ошибка публикации поста")
                bot.send_message(
                    message.chat.id,
                    f"❌ <b>Ошибка публикации</b>\nПопробуйте ещё раз",
                    parse_mode='HTML'
                )

# ==================== FLASK ДЛЯ RENDER ====================
app = Flask(__name__)
webhook_count = 0

def check_admin_access():
    """🔒 Проверка доступа к служебным эндпоинтам"""
    secret = request.args.get('secret')
    if secret != ADMIN_SECRET:
        logger.warning("⚠️ Попытка несанкционированного доступа к служебному эндпоинту")
        return False
    return True

@app.route('/')
def index():
    """Главная страница"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AGRO Bot</title>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #43a047 0%, #1b5e20 100%);
                color: white;
            }}
            .container {{
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            }}
            h1 {{ 
                margin: 0 0 20px 0; 
                font-size: 2em;
            }}
            .status {{ 
                color: #81c784; 
                font-weight: bold; 
                font-size: 1.2em; 
            }}
            .info {{
                background: rgba(255,255,255,0.05);
                padding: 15px;
                border-radius: 10px;
                margin: 15px 0;
            }}
            .info p {{
                margin: 8px 0;
            }}
            a {{ 
                color: #a5d6a7; 
                text-decoration: none; 
                transition: color 0.3s;
            }}
            a:hover {{
                color: #c8e6c9;
            }}
            .footer {{
                font-size: 0.9em; 
                opacity: 0.7; 
                margin-top: 20px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌾 AGRO Bot</h1>
            <p class="status">✅ Бот работает</p>
            <div class="info">
                <p><strong>📢 Канал:</strong> {CHANNEL_USERNAME}</p>
                <p><strong>📱 Каталог:</strong> <a href="{WEBAPP_URL}" target="_blank">Открыть</a></p>
                <p><strong>📊 Webhook вызовов:</strong> {webhook_count}</p>
            </div>
            <p>
                <a href="/health">Health Check</a>
            </p>
            <p class="footer">
                🔒 Все служебные эндпоинты защищены
            </p>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    """Health check для UptimeRobot"""
    return jsonify({
        'status': 'ok', 
        'webhook_calls': webhook_count,
        'service': 'agrobot'
    }), 200

@app.route('/webhook_info')
def webhook_info():
    """🔒 Информация о webhook - ЗАЩИЩЕНО!"""
    if not check_admin_access():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        info = bot.get_webhook_info()
        
        return jsonify({
            'url': '***HIDDEN***',  # Никогда не показываем URL
            'pending_updates': info.pending_update_count,
            'allowed_updates': info.allowed_updates,
            'last_error_date': info.last_error_date,
            'last_error_message': info.last_error_message if info.last_error_message else None
        })
    except Exception as e:
        logger.error(f"❌ Ошибка получения информации о webhook")
        return jsonify({'error': 'Internal error'}), 500

@app.route('/set_webhook')
def set_webhook_route():
    """🔒 Установка webhook - ЗАЩИЩЕНО!"""
    if not check_admin_access():
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        webhook_url = f"{RENDER_URL.rstrip('/')}/{BOT_TOKEN}"
        
        # Удаляем старый
        bot.remove_webhook()
        logger.info("🗑️ Старый webhook удалён")
        
        # Устанавливаем новый
        bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=["message", "channel_post"]
        )
        
        logger.info("✅ Webhook установлен")
        
        info = bot.get_webhook_info()
        
        return jsonify({
            'status': 'success',
            'webhook_url': '***HIDDEN***',
            'allowed_updates': info.allowed_updates
        })
        
    except Exception as e:
        logger.error("❌ Ошибка установки webhook")
        return jsonify({'error': 'Internal error'}), 500

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    """🔒 Обработка webhook от Telegram"""
    global webhook_count
    webhook_count += 1
    
    try:
        # Проверка content-type
        if request.headers.get('content-type') != 'application/json':
            logger.warning("⚠️ Неверный content-type webhook запроса")
            return 'Invalid content type', 403
        
        json_string = request.get_data().decode('utf-8')
        logger.info(f"📥 Webhook #{webhook_count} получен")
        
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        
        logger.info(f"✅ Webhook #{webhook_count} обработан")
        return '', 200
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки webhook")
        return '', 500

# ==================== STARTUP ====================
@app.before_request
def setup_webhook_once():
    """Автоматическая установка webhook при первом запросе"""
    if not hasattr(app, 'webhook_initialized'):
        try:
            webhook_url = f"{RENDER_URL.rstrip('/')}/{BOT_TOKEN}"
            
            logger.info("=" * 70)
            logger.info("🔄 УСТАНОВКА WEBHOOK...")
            logger.info("=" * 70)
            
            bot.remove_webhook()
            logger.info("🗑️ Старый webhook удалён")
            
            bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True,
                allowed_updates=["message", "channel_post"]
            )
            
            logger.info("✅ Webhook успешно установлен")
            logger.info(f"📋 Allowed updates: message, channel_post")
            
            app.webhook_initialized = True
            
            logger.info("=" * 70)
            logger.info("✅ БОТ ГОТОВ К РАБОТЕ!")
            logger.info("=" * 70)
            
        except Exception as e:
            logger.error("❌ Ошибка установки webhook при старте")

# ==================== MAIN ====================
if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🚀 ЗАПУСК AGRO BOT")
    logger.info("=" * 70)
    
    app.run(host='0.0.0.0', port=PORT, debug=False)