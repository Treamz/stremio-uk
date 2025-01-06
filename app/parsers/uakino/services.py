from bs4 import BeautifulSoup
from app.schemas import Preview, Series, Stream, Videos
from .settings import settings

import aiohttp
import json
from .utils import extract_numbers, parse_true_id, parse_first_number_from_data_id
import re
from datetime import datetime

headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
        "Referer": "https://uakino.me/"
    }

async def get_session():
    async with aiohttp.ClientSession() as session:
        yield session


async def get_previews_metadata(response_data, type_) -> dict[str, list[Preview]]:
    previews_metadata = {"metas": []}
    soup = BeautifulSoup(response_data, "html.parser")
    for item in soup.find_all("div", class_="movie-item"):
        previews_metadata["metas"].append(
            Preview(
                id=item.find("a", class_="movie-title")["href"].split("/")[-1].split(".")[0],
                type=type_,
                name=f"{item.find('a', class_='movie-title').text} ${(item.find('div', class_='full-season').text if item.find('div', class_='full-season') else '')}",
                genres=[],
                poster=f"https://uakino.me{item.find('img')['src']}",
                description=item.find("span", class_="desc-about-text").text,
            )
        )

    return previews_metadata


async def get_series_metadata(
    id: str, response_text: str, videos: list[Videos], type_title: str
) -> dict[str, Series]:
    soup = BeautifulSoup(response_text, "html.parser")
    full_info = soup.find("div", class_="full-text").find_all("span")
    return {
        "meta": Series(
            id=f"{id}",
            type=type_title,
            name=soup.find("h1").find("span", class_="solototle").text,
            poster = f"{settings.main_url}{soup.select_one('.film-poster img').get('src')}",
            genres = [tag.text.strip() for tag in soup.select('[itemprop="genre"] a')],
            description=soup.find("div", class_="full-text").text,
            director=[],
            runtime="",
            background= f"{settings.main_url}{soup.select_one('.film-poster img').get('src')}",
            videos=videos,
        )
    }


async def get_videos(
    id: str, response_text: str, session: aiohttp.ClientSession
) -> list[Videos]:
    videos = []

    soup = BeautifulSoup(response_text, "html.parser")
    iframe_element = soup.select_one(".box.full-text.visible iframe")

    if iframe_element and "src" in iframe_element.attrs:
        iframe_src = iframe_element["src"]
        async with session.get(iframe_src) as response:
                if "/vod/" in soup.select_one(".box.full-text.visible iframe")["src"]:
                    plr_soup = BeautifulSoup(await response.text(), "html.parser")
                    videos.append(
                        Videos(
                            id=f'{id}',
                            title=soup.find("div", class_="alltitle").find("span").text,
                            thumbnail = soup.select_one(".film-poster img").get('src'),
                            released=None,
                            season=None,
                            episode=None,
                        )
                    )
                else:
                    plr_soup = BeautifulSoup(await response.text(), "html.parser")
                    script_tag = plr_soup.body.find("script")
                    # Regex to extract the `file` value
                    file_match = re.search(r'file:\s*\'(\[.*?\])\'', script_tag.string, re.DOTALL)
                    if not file_match:
                        raise ValueError("File content not found in the script.")

                    # Extracted file content as a JSON string
                    file_content = file_match.group(1)
        #             plr_json = json.loads(plr_soup.body.find("script", type="text/javascript").text.split("file: '")[1].split("',")[0])

                    try:
                        plr_json = json.loads(file_match.group(1))
                    except json.JSONDecodeError as e:
                        raise ValueError("Failed to parse JSON data from the file field.") from e

                    seen_titles = set()
                    for dub in plr_json:
                        for season in dub["folder"]:
                            for episode in season["folder"]:
                                if episode["title"] not in seen_titles:
                                    seen_titles.add(episode["title"])
                                    videos.append(
                                        Videos(
                                            id=f'{id}/{season["title"]}/{episode["title"]}',
                                            title=episode["title"],
                                            thumbnail=episode["poster"],
                                            released=None,
                                            season=extract_numbers(season["title"])[0],
                                            episode=extract_numbers(episode["title"])[0],
                                        )
                                    )
    else:
        true_id = parse_true_id(id)
        playlist_url = f"{settings.main_url}/engine/ajax/playlists.php?news_id={true_id}&xfield=playlist&time={int(datetime.now().timestamp() * 1000)}"
        async with session.get(
                playlist_url,
                headers={
                    "Referer": "https://uakino.me",
                    "X-Requested-With": "XMLHttpRequest",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:126.0) Gecko/20100101 Firefox/126.0",
                },
        ) as response:
            playlist_data = await response.json()
            if not playlist_data.get("success"):
                raise ValueError("Failed to fetch TV playlist.")

            playlist_html = playlist_data["response"]
            playlist_soup = BeautifulSoup(playlist_html, "html.parser")
            print(playlist_soup)
            for episode in playlist_soup.select("div.playlists-videos li"):
                title = episode.text.strip()
                season = parse_first_number_from_data_id(episode)
                episode_numbers = extract_numbers(title)
                episode_number = episode_numbers[
                    0] if episode_numbers else None  # Fallback to None if no numbers are found

                file_url = episode["data-file"]
                videos.append(
                    Videos(
                        id=f'{id}/{title}',
                        title=title,
                        thumbnail=None,  # Thumbnail not provided in the example response
                        released=None,
                        season=1,  # Extract season if provided
                        episode=episode_number,
                    )
                )
    return videos


async def get_streams(
    id: str, season_param: str, episode_param: str, session: aiohttp.ClientSession, response_text
) -> dict[str, list[Stream]]:
    streams = {"streams": []}

    soup = BeautifulSoup(response_text, "html.parser")
    iframe_element = soup.select_one(".box.full-text.visible iframe")

    if iframe_element and "src" in iframe_element.attrs:
        iframe_src = iframe_element["src"]
        iframe_src = iframe_element["src"]
        async with session.get(iframe_src) as response:
            plr_soup = BeautifulSoup(await response.text(), "html.parser")
            if "/vod/" in soup.select_one(".box.full-text.visible iframe")["src"]:
                script_tag = plr_soup.body.find("script")
                if not script_tag:
                    raise ValueError("Script tag with Playerjs initialization not found.")
                file_url_match = re.search(r'file:\s*"(.*?)"', script_tag.text)
                if not file_url_match:
                    raise ValueError("File URL not found in the script.")

                plr_url = file_url_match.group(1)
                streams["streams"].append(
                    Stream(
                        name="Фільм",
                        url=plr_url,
                    )
                )
            else:
                script_tag = plr_soup.body.find("script")
                if not script_tag:
                    raise ValueError("Script tag with Playerjs initialization not found.")
                file_match = re.search(r'file:\s*\'(\[.*?\])\'', script_tag.string, re.DOTALL)
                if not file_match:
                    raise ValueError("File URL not found in the script.")

                #             plr_json = file_match.group(1)
                #             print(plr_json)

                plr_json = json.loads(file_match.group(1))
                for dub in plr_json:
                    for season in dub["folder"]:
                        if season["title"] == season_param:
                            for episode in season["folder"]:
                                if episode["title"] == episode_param:
                                    streams["streams"].append(
                                        Stream(
                                            name=dub["title"],
                                            url=episode["file"],
                                        )
                                    )
    else:
        true_id = parse_true_id(id)
        playlist_url = f"{settings.main_url}/engine/ajax/playlists.php?news_id={true_id}&xfield=playlist&time={int(datetime.now().timestamp() * 1000)}"
        async with session.get(
                playlist_url,
                headers={
                    "Referer": "https://uakino.me",
                    "X-Requested-With": "XMLHttpRequest",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:126.0) Gecko/20100101 Firefox/126.0",
                },
        ) as response:
            playlist_data = await response.json()
            if not playlist_data.get("success"):
                raise ValueError("Failed to fetch TV playlist.")

            playlist_html = playlist_data["response"]
            playlist_soup = BeautifulSoup(playlist_html, "html.parser")
            for episode in playlist_soup.select("div.playlists-videos li"):
                title = episode.text.strip()
                season = parse_first_number_from_data_id(episode)
                episode_numbers = extract_numbers(title)
                episode_number = episode_numbers[
                    0] if episode_numbers else None  # Fallback to None if no numbers are found
                if title == episode_param:
                    # file_url = episode["data-file"]
                    print(episode)
                    file_url = await ashdi_parser(session, episode["data-file"])
                    voice_title = episode["data-voice"]
                    print(voice_title)
                    streams["streams"].append(
                        Stream(
                            name=voice_title,
                            url=file_url,
                        )
                    )


    print(streams)
    return streams

async def ashdi_parser(session: aiohttp.ClientSession, iframe_src: str) -> str:
    """
      Parses the iframe source URL to extract the `file` URL from a script tag.

      :param session: An aiohttp.ClientSession instance.
      :param iframe_src: The URL of the iframe to fetch and parse.
      :return: Extracted `file` URL as a string.
    """
    async with session.get(f"https:{iframe_src}") as response:
        plr_soup = BeautifulSoup(await response.text(), "html.parser")
        script_tag = plr_soup.body.find("script")
        file_url_match = re.search(r'file:\s*"(.*?)"', script_tag.text)
        return file_url_match.group(1)

