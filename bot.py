# Copyright ©️ 2023 Siddhartha Abhimanyu. All Rights Reserved
# You are free to use this code in any of your project, but you MUST include the following in your README.md (Copy & paste)
# ##Credits - [EliteLyrics](https://github.com/VivaanNetworkDev/EliteLyrics)

# Read GNU General Public License v3.0: [https://github.com/VivaanNetworkDev/EliteLyrics/blob/mai/LICENSE](https://github.com/VivaanNetworkDev/EliteLyrics/blob/mai/LICENSE)
# Don't forget to follow github.com/VivaanNetworkDev because I am doing these things for free and open source
# Star, fork, enjoy!

import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from requests.exceptions import Timeout, HTTPError
from pyrogram.errors import MessageTooLong
from config import Config

# Import cloudscraper BEFORE lyricsgenius
import cloudscraper
import lyricsgenius
from lyricsgenius.api.base import BaseEndpoint

# Monkey patch lyricsgenius to use cloudscraper for requests
original_make_request = BaseEndpoint._make_request

def patched_make_request(self, path, params_=None, public_api=False):
    """Patched version of _make_request that handles Cloudflare"""
    scraper = cloudscraper.create_scraper()
    
    url = "https://api.genius.com" + path if public_api else path
    
    try:
        response = scraper.get(
            url,
            params=params_,
            timeout=10,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        
        if response.status_code not in [200, 204]:
            raise AssertionError(
                f"Unexpected response status code: {response.status_code}. "
                f"Expected 200 or 204. Response body: {response.text[:500]}"
            )
        
        return response.json() if response.text else {}
    
    except Exception as e:
        raise Exception(f"Request failed: {str(e)}")

# Apply the monkey patch
BaseEndpoint._make_request = patched_make_request

bot = Client(
    "bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# Initialize Genius normally
GENIUS = lyricsgenius.Genius(Config.TOKEN, timeout=10)

# Store lyrics data globally
TITLE = None
ARTISTE = None
TEXT = None


@bot.on_message(filters.command("start") & filters.private)
async def start(bot, message):
    await bot.send_message(
        message.chat.id,
        f"Hello **{message.from_user.first_name}**!!\n\n"
        f"Welcome to Elite Lyrics Bot 🎵\n\n"
        f"You can get lyrics of any song which is on @EliteLyricsBot using this bot. "
        f"Just send the name of the song that you want to get lyrics for.\n\n"
        f"This is quite simple!",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔍 Search inline...", switch_inline_query_current_chat="")
                ]
            ]
        )
    )


@bot.on_message(filters.text & filters.private)
async def lyric_get(bot, message):
    global TITLE, ARTISTE, TEXT
    
    try:
        m = await message.reply("🔍 Searching...")
        song_name = message.text.strip()
        
        if not song_name:
            await m.edit_text("❌ Please provide a song name")
            return
        
        try:
            print(f"Searching for: {song_name}")
            LYRICS = GENIUS.search_song(song_name)
            
            if LYRICS is None:
                await m.edit_text("❌ Oops!\nNo results found for this song.")
                return
            
            TITLE = LYRICS.title
            ARTISTE = LYRICS.artist
            TEXT = LYRICS.lyrics
            
            # Prepare the response
            response_text = f"🎶 **Song Name:** {TITLE}\n🎙️ **Artist:** {ARTISTE}\n\n`{TEXT}`"
            
            # Try to send as message first
            try:
                await m.edit_text(
                    response_text,
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("🔍 Search again...", switch_inline_query_current_chat="")
                            ]
                        ]
                    )
                )
            except MessageTooLong:
                # If message is too long, send as file
                os.makedirs('downloads', exist_ok=True)
                file_path = f'downloads/{TITLE}.txt'
                
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(f'{TITLE}\n{ARTISTE}\n\n{TEXT}')
                
                await m.edit_text("📄 Lyrics sent as a text file (too long to display)")
                
                await bot.send_document(
                    message.chat.id,
                    document=file_path,
                    caption=f"🎶 **{TITLE}**\n🎙️ **{ARTISTE}**"
                )
                
                # Clean up
                os.remove(file_path)
        
        except Exception as e:
            print(f"Error searching for lyrics: {str(e)}")
            await m.edit_text(f"❌ Error: Could not fetch lyrics\n\nDetails: {str(e)[:100]}")
    
    except Timeout:
        await message.reply("⏱️ Request timed out. Please try again.")
    except HTTPError as https_e:
        print(f"HTTP Error: {https_e}")
        await message.reply(f"❌ HTTP Error occurred: {str(https_e)[:100]}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        await message.reply(f"❌ An unexpected error occurred: {str(e)[:100]}")


@bot.on_inline_query()
async def inlinequery(client, inline_query):
    answer = []
    
    try:
        if inline_query.query == "":
            await inline_query.answer(
                results=[
                    InlineQueryResultArticle(
                        title="🔍 Search for lyrics...",
                        description="Type a song name to search for lyrics",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton("🔍 Search for lyrics...", switch_inline_query_current_chat="")
                                ]
                            ]
                        ),
                        input_message_content=InputTextMessageContent(
                            "💬 Search for lyrics inline using this bot!"
                        )
                    )
                ]
            )
        else:
            search_query = inline_query.query.strip()
            print(f"Inline search for: {search_query}")
            
            try:
                INLINE_LYRICS = GENIUS.search_song(search_query)
                
                if INLINE_LYRICS is None:
                    await inline_query.answer(
                        results=[
                            InlineQueryResultArticle(
                                title="❌ No results found",
                                description=f"Could not find lyrics for '{search_query}'",
                                input_message_content=InputTextMessageContent(
                                    f"❌ No lyrics found for '{search_query}'"
                                )
                            )
                        ]
                    )
                    return
                
                INLINE_TITLE = INLINE_LYRICS.title
                INLINE_ARTISTE = INLINE_LYRICS.artist
                INLINE_TEXT = INLINE_LYRICS.lyrics
                
                # Truncate if too long
                display_text = INLINE_TEXT[:1000] + "..." if len(INLINE_TEXT) > 1000 else INLINE_TEXT
                response_text = f"**🎶 Lyrics Result**\n\n🎶 **Song:** {INLINE_TITLE}\n🎙️ **Artist:** {INLINE_ARTISTE}\n\n`{display_text}`"
                
                answer.append(
                    InlineQueryResultArticle(
                        title=INLINE_TITLE,
                        description=f"by {INLINE_ARTISTE}",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton("❌ Wrong result?", switch_inline_query_current_chat=search_query),
                                    InlineKeyboardButton("🔍 Search again", switch_inline_query_current_chat="")
                                ]
                            ]
                        ),
                        input_message_content=InputTextMessageContent(response_text)
                    )
                )
            
            except Exception as e:
                print(f"Error in inline search: {str(e)}")
                await inline_query.answer(
                    results=[
                        InlineQueryResultArticle(
                            title="❌ Error occurred",
                            description=f"Could not fetch lyrics",
                            input_message_content=InputTextMessageContent(
                                f"❌ Error: Could not fetch lyrics. Try again later."
                            )
                        )
                    ]
                )
                return
        
        await inline_query.answer(results=answer, cache_time=1)
    
    except Exception as e:
        print(f"Inline query error: {str(e)}")


if __name__ == "__main__":
    print("🎵 Elite Lyrics Bot is starting...")
    bot.run()
