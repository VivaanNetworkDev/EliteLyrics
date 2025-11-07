# Copyright ©️ 2023 Siddhartha Abhimanyu. All Rights Reserved
# You are free to use this code in any of your project, but you MUST include the following in your README.md (Copy & paste)
# ##Credits - [EliteLyrics](https://github.com/VivaanNetworkDev/EliteLyrics)

# Read GNU General Public License v3.0: [https://github.com/VivaanNetworkDev/EliteLyrics/blob/mai/LICENSE](https://github.com/VivaanNetworkDev/EliteLyrics/blob/mai/LICENSE)
# Don't forget to follow github.com/VivaanNetworkDev because I am doing these things for free and open source
# Star, fork, enjoy!

import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from pyrogram.errors import MessageTooLong
from config import Config

bot = Client(
    "bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# Store lyrics data globally
TITLE = None
ARTISTE = None
TEXT = None

# Session for requests with timeout
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})


def search_musixmatch(song_name):
    """
    Search lyrics using Musixmatch API (fast, reliable, no authentication needed)
    """
    try:
        print(f"Searching Musixmatch for: {song_name}")
        
        # Musixmatch search endpoint
        url = "https://www.musixmatch.com/ws/1.1/track.search"
        params = {
            'q_track': song_name,
            'apikey': '523e41434d2e32383833373731616666666666666666363966613662666536',  # Public API key
            'format': 'json',
            's_track_rating': 'desc'
        }
        
        response = session.get(url, params=params, timeout=8)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('message', {}).get('body', {}).get('track_list'):
            track = data['message']['body']['track_list'][0]['track']
            
            title = track.get('track_name', 'Unknown')
            artist = track.get('artist_name', 'Unknown')
            
            # Get full lyrics
            track_id = track.get('track_id')
            if track_id:
                lyrics_url = "https://www.musixmatch.com/ws/1.1/track.lyrics.get"
                lyrics_params = {
                    'track_id': track_id,
                    'apikey': '523e41434d2e32383833373731616666666666666666363966613662666536'
                }
                
                lyrics_response = session.get(lyrics_url, params=lyrics_params, timeout=8)
                if lyrics_response.status_code == 200:
                    lyrics_data = lyrics_response.json()
                    if lyrics_data.get('message', {}).get('body', {}).get('lyrics'):
                        lyrics_text = lyrics_data['message']['body']['lyrics']['lyrics_body']
                        
                        return {
                            'title': title,
                            'artist': artist,
                            'lyrics': lyrics_text
                        }
        
        return None
    
    except Exception as e:
        print(f"Musixmatch Error: {str(e)}")
        return None


def search_azlyrics_api(song_name):
    """
    Search using a free lyrics API that works well
    """
    try:
        print(f"Searching Lyrics API for: {song_name}")
        
        # Using lyrics-api.com (completely free, no auth needed)
        url = f"https://api.lyrics-api.com/search"
        params = {
            'query': song_name,
            'limit': 1
        }
        
        response = session.get(url, params=params, timeout=8)
        response.raise_for_status()
        
        data = response.json()
        
        if data and len(data) > 0:
            song = data[0]
            title = song.get('title', 'Unknown')
            artist = song.get('artist', 'Unknown')
            lyrics = song.get('lyrics', '')
            
            if lyrics:
                return {
                    'title': title,
                    'artist': artist,
                    'lyrics': lyrics
                }
        
        return None
    
    except Exception as e:
        print(f"Lyrics API Error: {str(e)}")
        return None


def search_song_lyrics(song_name):
    """
    Try alternative API
    """
    try:
        print(f"Searching song-lyrics.com for: {song_name}")
        
        # Clean song name for URL
        clean_name = song_name.lower().replace(' ', '-')
        url = f"https://song-lyrics-api.herokuapp.com/?song={song_name}"
        
        response = session.get(url, timeout=8)
        response.raise_for_status()
        
        data = response.json()
        
        if data and 'lyrics' in data:
            return {
                'title': song_name,
                'artist': data.get('artist', 'Unknown'),
                'lyrics': data['lyrics']
            }
        
        return None
    
    except Exception as e:
        print(f"Song Lyrics API Error: {str(e)}")
        return None


def get_lyrics(song_name):
    """
    Get lyrics using multiple sources as fallback
    """
    if not song_name or song_name.strip() == "":
        return None
    
    song_name = song_name.strip()
    
    # Try multiple APIs in order of reliability
    print(f"\n🔍 Attempting to fetch lyrics for: {song_name}")
    
    # First try: Musixmatch (fastest, most reliable)
    result = search_musixmatch(song_name)
    if result:
        print(f"✅ Found on Musixmatch!")
        return result
    
    # Second try: Lyrics API
    result = search_azlyrics_api(song_name)
    if result:
        print(f"✅ Found on Lyrics API!")
        return result
    
    # Third try: Song Lyrics API
    result = search_song_lyrics(song_name)
    if result:
        print(f"✅ Found on Song Lyrics API!")
        return result
    
    print(f"❌ No lyrics found on any API")
    return None


@bot.on_message(filters.command("start") & filters.private)
async def start(bot, message):
    await bot.send_message(
        message.chat.id,
        f"Hello **{message.from_user.first_name}**!!\n\n"
        f"Welcome to Elite Lyrics Bot 🎵\n\n"
        f"You can get lyrics of any song using this bot. "
        f"Just send the name of the song you want to search.\n\n"
        f"Examples:\n"
        f"• `tu mera koi na`\n"
        f"• `Blinding Lights`\n"
        f"• `Bohemian Rhapsody`\n\n"
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
            result = get_lyrics(song_name)
            
            if result is None:
                await m.edit_text(
                    "❌ Oops! No results found.\n\n"
                    "Try:\n"
                    "• Using the correct spelling\n"
                    "• A more famous song\n"
                    "• Searching again in a moment"
                )
                return
            
            TITLE = result['title']
            ARTISTE = result['artist']
            TEXT = result['lyrics']
            
            # Prepare the response
            response_text = f"🎶 **Song:** {TITLE}\n🎙️ **Artist:** {ARTISTE}\n\n`{TEXT}`"
            
            # Try to send as message first
            try:
                await m.edit_text(
                    response_text,
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("🔍 Search another...", switch_inline_query_current_chat="")
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
                
                await m.edit_text("📄 Lyrics sent as a text file (message too long)")
                
                await bot.send_document(
                    message.chat.id,
                    document=file_path,
                    caption=f"🎶 **{TITLE}** by **{ARTISTE}**"
                )
                
                # Clean up
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        except Exception as e:
            print(f"Error searching for lyrics: {str(e)}")
            await m.edit_text(f"❌ Error occurred\n\nPlease try again later")
    
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        await message.reply(f"❌ An error occurred. Please try again.")


@bot.on_inline_query()
async def inlinequery(client, inline_query):
    answer = []
    
    try:
        if inline_query.query == "":
            await inline_query.answer(
                results=[
                    InlineQueryResultArticle(
                        title="🔍 Search for lyrics...",
                        description="Type a song name to search",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton("🔍 Search...", switch_inline_query_current_chat="")
                                ]
                            ]
                        ),
                        input_message_content=InputTextMessageContent(
                            "💬 Search for lyrics inline!"
                        )
                    )
                ]
            )
        else:
            search_query = inline_query.query.strip()
            print(f"\n📱 Inline search: {search_query}")
            
            try:
                result = get_lyrics(search_query)
                
                if result is None:
                    await inline_query.answer(
                        results=[
                            InlineQueryResultArticle(
                                title="❌ No results",
                                description=f"Could not find '{search_query}'",
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
                display_text = INLINE_TEXT[:800] + "..." if len(INLINE_TEXT) > 800 else INLINE_TEXT
                response_text = f"**🎶 {INLINE_TITLE}**\n\n🎙️ {INLINE_ARTISTE}\n\n`{display_text}`"
                
                answer.append(
                    InlineQueryResultArticle(
                        title=INLINE_TITLE,
                        description=INLINE_ARTISTE,
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton("🔍 Search again", switch_inline_query_current_chat="")
                                ]
                            ]
                        ),
                        input_message_content=InputTextMessageContent(response_text)
                    )
                )
            
            except Exception as e:
                print(f"Inline search error: {str(e)}")
                await inline_query.answer(
                    results=[
                        InlineQueryResultArticle(
                            title="❌ Error",
                            description="Could not fetch lyrics",
                            input_message_content=InputTextMessageContent(
                                "❌ Error: Could not fetch lyrics. Try again."
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
