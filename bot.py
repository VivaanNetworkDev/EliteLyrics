# Copyright ©️ 2023 Siddhartha Abhimanyu. All Rights Reserved
# You are free to use this code in any of your project, but you MUST include the following in your README.md (Copy & paste)
# ##Credits - [EliteLyrics](https://github.com/VivaanNetworkDev/EliteLyrics)

# Read GNU General Public License v3.0: [https://github.com/VivaanNetworkDev/EliteLyrics/blob/mai/LICENSE](https://github.com/VivaanNetworkDev/EliteLyrics/blob/mai/LICENSE)
# Don't forget to follow github.com/VivaanNetworkDev because I am doing these things for free and open source
# Star, fork, enjoy!

import os
import requests
from bs4 import BeautifulSoup
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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})


def search_azlyrics(song_name):
    """
    Search and scrape lyrics from AZLyrics.com (no authentication, very reliable)
    """
    try:
        print(f"Searching AZLyrics for: {song_name}")
        
        # Search on AZLyrics
        search_url = "https://www.azlyrics.com/search.php"
        params = {'q': song_name}
        
        response = session.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the first song result
        song_link = soup.find('a', href=lambda x: x and x.startswith('/lyrics/'))
        
        if not song_link:
            return None
        
        song_url = 'https://www.azlyrics.com' + song_link['href']
        song_title = song_link.text.strip()
        
        # Extract artist from the link context
        song_text = song_link.text.split(' - ')
        if len(song_text) >= 2:
            artist = song_text[0].strip()
            title = song_text[1].strip()
        else:
            artist = 'Unknown'
            title = song_title
        
        print(f"Found: {artist} - {title}")
        
        # Get the actual lyrics page
        lyrics_response = session.get(song_url, timeout=10)
        lyrics_response.raise_for_status()
        
        lyrics_soup = BeautifulSoup(lyrics_response.content, 'html.parser')
        
        # Find lyrics div (AZLyrics uses specific structure)
        lyrics_div = lyrics_soup.find('div', class_='col-xs-12 col-lg-8')
        
        if not lyrics_div:
            # Alternative search for lyrics
            all_divs = lyrics_soup.find_all('div')
            for div in all_divs:
                text = div.get_text()
                if len(text) > 500 and 'ad' not in text.lower():
                    lyrics_text = text.strip()
                    if lyrics_text and len(lyrics_text) > 100:
                        return {
                            'title': title,
                            'artist': artist,
                            'lyrics': lyrics_text
                        }
            return None
        
        # Extract text and clean it
        lyrics_text = lyrics_div.get_text(separator='\n')
        lyrics_text = '\n'.join([line.strip() for line in lyrics_text.split('\n') if line.strip()])
        
        # Remove common ad text
        lyrics_text = lyrics_text.replace('[ad]', '').replace('[Ad]', '')
        lyrics_text = '\n'.join([line for line in lyrics_text.split('\n') if line.strip()])
        
        if lyrics_text and len(lyrics_text) > 50:
            return {
                'title': title,
                'artist': artist,
                'lyrics': lyrics_text
            }
        
        return None
    
    except Exception as e:
        print(f"AZLyrics Error: {str(e)}")
        return None


def search_genius_scrape(song_name):
    """
    Scrape lyrics from Genius.com directly (bypasses API)
    """
    try:
        print(f"Searching Genius (scrape) for: {song_name}")
        
        # Use Google to find Genius URL
        search_url = "https://www.google.com/search"
        params = {'q': f'site:genius.com {song_name} lyrics'}
        
        response = session.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find Genius link
        genius_link = None
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if 'genius.com' in href and 'lyrics' in href:
                genius_link = href
                break
        
        if not genius_link:
            return None
        
        print(f"Found Genius URL: {genius_link}")
        
        # Clean URL
        if '/url?q=' in genius_link:
            genius_link = genius_link.split('/url?q=')[1].split('&')[0]
        
        # Get the lyrics page
        lyrics_response = session.get(genius_link, timeout=10)
        lyrics_response.raise_for_status()
        
        lyrics_soup = BeautifulSoup(lyrics_response.content, 'html.parser')
        
        # Extract title and artist
        h1 = lyrics_soup.find('h1')
        if h1:
            title_text = h1.get_text().strip()
        else:
            title_text = song_name
        
        # Extract lyrics
        lyrics_divs = lyrics_soup.find_all('div', {'data-lyrics-container': 'true'})
        
        if lyrics_divs:
            lyrics_text = '\n'.join([div.get_text(separator='\n') for div in lyrics_divs])
            return {
                'title': title_text.split(' by ')[0] if ' by ' in title_text else title_text,
                'artist': title_text.split(' by ')[-1] if ' by ' in title_text else 'Unknown',
                'lyrics': lyrics_text
            }
        
        return None
    
    except Exception as e:
        print(f"Genius Scrape Error: {str(e)}")
        return None


def get_lyrics(song_name):
    """
    Get lyrics using web scraping
    """
    if not song_name or song_name.strip() == "":
        return None
    
    song_name = song_name.strip()
    
    print(f"\n🔍 Attempting to fetch lyrics for: {song_name}")
    
    # Try AZLyrics first (most reliable, no auth needed)
    result = search_azlyrics(song_name)
    if result:
        print(f"✅ Found on AZLyrics!")
        return result
    
    # Try Genius scraping
    result = search_genius_scrape(song_name)
    if result:
        print(f"✅ Found on Genius!")
        return result
    
    print(f"❌ No lyrics found")
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
