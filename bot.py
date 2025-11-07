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

# Session for requests
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})


def search_lyrics_api(artist, song):
    """
    Search lyrics using LyricsOVH API (no Cloudflare blocking)
    """
    try:
        print(f"Searching LyricsOVH for: {artist} - {song}")
        url = f"https://api.lyrics.ovh/v1/{artist}/{song}"
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'lyrics' in data and data['lyrics']:
            return {
                'title': song,
                'artist': artist,
                'lyrics': data['lyrics']
            }
        return None
    
    except Exception as e:
        print(f"LyricsOVH Error: {str(e)}")
        return None


def parse_song_input(song_name):
    """
    Parse song name to extract artist and song
    Format: "artist - song" or just "song"
    """
    if ' - ' in song_name:
        parts = song_name.split(' - ', 1)
        return parts[0].strip(), parts[1].strip()
    else:
        # Try to search with just the song name
        return "", song_name.strip()


def search_lyrics_genius_api(song_name):
    """
    Try Genius API with proper token if available
    """
    try:
        if not hasattr(Config, 'TOKEN') or not Config.TOKEN:
            return None
        
        print(f"Searching Genius API for: {song_name}")
        
        headers = {
            'Authorization': f'Bearer {Config.TOKEN}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = "https://api.genius.com/search"
        params = {'q': song_name}
        
        response = session.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data['response']['hits']:
            hit = data['response']['hits'][0]
            return {
                'title': hit['result']['title'],
                'artist': hit['result']['primary_artist']['name'],
                'lyrics': "Full lyrics available at: " + hit['result']['url']  # Can't scrape due to Cloudflare
            }
        return None
    
    except Exception as e:
        print(f"Genius API Error: {str(e)}")
        return None


def get_lyrics(song_name):
    """
    Get lyrics using multiple sources as fallback
    """
    # Try parsing artist - song format
    artist, song = parse_song_input(song_name)
    
    # First try: LyricsOVH (most reliable, no Cloudflare)
    if artist:
        result = search_lyrics_api(artist, song)
        if result:
            return result
    
    # Try just the song name with common artists
    result = search_lyrics_api("", song)
    if result:
        return result
    
    # Second try: Genius API with token
    result = search_lyrics_genius_api(song_name)
    if result:
        return result
    
    return None


@bot.on_message(filters.command("start") & filters.private)
async def start(bot, message):
    await bot.send_message(
        message.chat.id,
        f"Hello **{message.from_user.first_name}**!!\n\n"
        f"Welcome to Elite Lyrics Bot 🎵\n\n"
        f"You can get lyrics of any song using this bot. "
        f"Send the song name or format: **Artist - Song Name**\n\n"
        f"Examples:\n"
        f"• `tu mera koi na`\n"
        f"• `The Weeknd - Blinding Lights`\n\n"
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
                    "❌ Oops!\n"
                    "No results found for this song.\n\n"
                    "Try:\n"
                    "• Using correct spelling\n"
                    "• Format: **Artist - Song Name**"
                )
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
                if os.path.exists(file_path):
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
                result = get_lyrics(search_query)
                
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
                            description="Could not fetch lyrics",
                            input_message_content=InputTextMessageContent(
                                "❌ Error: Could not fetch lyrics. Try again later."
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
