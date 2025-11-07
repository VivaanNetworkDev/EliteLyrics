# Copyright ©️ 2023 Siddhartha Abhimanyu. All Rights Reserved
# You are free to use this code in any of your project, but you MUST include the following in your README.md (Copy & paste)
# ##Credits - [EliteLyrics](https://github.com/VivaanNetworkDev/EliteLyrics)

# Read GNU General Public License v3.0: [https://github.com/VivaanNetworkDev/EliteLyrics/blob/mai/LICENSE](https://github.com/VivaanNetworkDev/EliteLyrics/blob/mai/LICENSE)
# Don't forget to follow github.com/VivaanNetworkDev because I am doing these things for free and open source
# Star, fork, enjoy!

import os
import json
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from pyrogram.errors import MessageTooLong
from config import Config
import cloudscraper

bot = Client(
    "bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# Initialize cloudscraper session
scraper = cloudscraper.create_scraper()

# Store lyrics data globally
TITLE = None
ARTISTE = None
TEXT = None


def get_lyrics_from_genius(song_name):
    """
    Fetch lyrics directly from Genius.com using cloudscraper to bypass Cloudflare
    """
    try:
        # Search for the song
        search_url = "https://genius.com/api/search/multi"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        params = {
            'q': song_name
        }
        
        print(f"Searching for: {song_name}")
        search_response = scraper.get(search_url, params=params, headers=headers, timeout=10)
        search_response.raise_for_status()
        
        search_data = search_response.json()
        
        # Extract song information from search results
        if 'response' not in search_data or 'hits' not in search_data['response']:
            return None
        
        hits = search_data['response']['hits']
        if not hits:
            return None
        
        # Get the first result
        first_hit = hits[0]
        if 'result' not in first_hit:
            return None
        
        song_data = first_hit['result']
        song_url = song_data.get('url')
        
        if not song_url:
            return None
        
        print(f"Found song URL: {song_url}")
        
        # Fetch the lyrics page
        page_response = scraper.get(song_url, headers=headers, timeout=10)
        page_response.raise_for_status()
        
        # Extract lyrics from the page using regex
        # Look for the JSON-LD structured data
        json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
        json_ld_matches = re.findall(json_ld_pattern, page_response.text, re.DOTALL)
        
        lyrics_text = None
        
        # Try to extract from JSON-LD first
        for match in json_ld_matches:
            try:
                data = json.loads(match)
                if 'text' in data:
                    lyrics_text = data['text']
                    break
            except json.JSONDecodeError:
                continue
        
        # If not found in JSON-LD, extract from page content
        if not lyrics_text:
            # Extract lyrics div content
            lyrics_pattern = r'<div[^>]*data-lyrics-container[^>]*>(.*?)</div>'
            matches = re.findall(lyrics_pattern, page_response.text, re.DOTALL)
            
            if matches:
                # Clean up HTML tags
                lyrics_html = ''.join(matches)
                lyrics_text = re.sub(r'<[^>]+>', '', lyrics_html)
                lyrics_text = re.sub(r'&nbsp;', ' ', lyrics_text)
                lyrics_text = re.sub(r'&#x27;', "'", lyrics_text)
        
        # Extract song title and artist
        title_pattern = r'"trackName":"([^"]+)"'
        artist_pattern = r'"byArtist":"name":"([^"]+)"'
        
        title_match = re.search(title_pattern, page_response.text)
        artist_match = re.search(artist_pattern, page_response.text)
        
        title = title_match.group(1) if title_match else song_data.get('title', 'Unknown')
        artist = artist_match.group(1) if artist_match else song_data.get('primary_artist', {}).get('name', 'Unknown')
        
        if lyrics_text:
            # Clean up the lyrics
            lyrics_text = lyrics_text.strip()
            return {
                'title': title,
                'artist': artist,
                'lyrics': lyrics_text
            }
        
        return None
    
    except Exception as e:
        print(f"Error fetching lyrics: {str(e)}")
        return None


@bot.on_message(filters.command("start") & filters.private)
async def start(bot, message):
    await bot.send_message(
        message.chat.id,
        f"Hello **{message.from_user.first_name}**!!\n\n"
        f"Welcome to Elite Lyrics Bot 🎵\n\n"
        f"You can get lyrics of any song using this bot. "
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
            result = get_lyrics_from_genius(song_name)
            
            if result is None:
                await m.edit_text("❌ Oops!\nNo results found for this song.")
                return
            
            TITLE = result['title']
            ARTISTE = result['artist']
            TEXT = result['lyrics']
            
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
                result = get_lyrics_from_genius(search_query)
                
                if result is None:
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
                
                INLINE_TITLE = result['title']
                INLINE_ARTISTE = result['artist']
                INLINE_TEXT = result['lyrics']
                
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
