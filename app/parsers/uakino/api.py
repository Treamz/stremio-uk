from fastapi import Depends, APIRouter
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from app.schemas import Manifest, Catalogs, Preview, Series, Stream
from urllib.parse import urlencode

from .settings import settings
from .services import (
    get_session,
    get_previews_metadata,
    get_series_metadata,
    get_videos,
    get_streams,
)

import aiohttp

from .utils import extract_id

router = APIRouter(prefix="/uakino")

headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
            "Referer": "https://uakino.me/"
    }

@router.get("/clear-cache")
async def clear_cache():
    await FastAPICache.clear()
    return {"message": "Cache cleared successfully"}

@router.get("/manifest.json", tags=[settings.name])
@cache()
def addon_manifest() -> Manifest:
    manifest = Manifest(
        id="ua.treamz.stremio.uakino",
        version="1.0.0",
        logo=f"https://www.google.com/s2/favicons?domain={settings.main_url}&sz=128",
        name="UAKino",
        description="Мета проекту «UAKino» - популяризація української мови, демонстрація її різнобарвності та сучасності. Ми плануємо робити це через ретрансляцію якісного кіно, мультфільмів, телесеріалів та різноманітних телешоу в якісному українському перекладі. Тож, у добрий шлях дорогі конфіденти!.",
        types=["movie", "series"],
        catalogs=[
            Catalogs(
                type=item[1],
                id=f"uakino_{item[2]}",
                name=f"{item[0]}/Uakino",
                extra=[
                    {"name": "skip", "isRequired": False},
                    # {"genres": "anime"}
                ],
            )
            for item in [
                ["Фільми", "movie", "films"],
                ["Серіали", "series", "series"],
                ["Мультфильми", "movie", "cartoon"],
                ["Мультсериали", "series", "cartoon-series"],
                ["Аніме", "series", "anime"],
            ]
        ],
        resources=[
            "catalog",
            "meta",
            # {
            #     "name": "meta",
            #     "types": ["movie", "series", "cartoon", "anime"],
            #     "idPrefixes": ["uakino_"]
            # },
            "stream",
#             "subtitles"
        ],
        idPrefixes=['uakino_'],
    )

    # Search Catalog
    manifest.catalogs.append(
        Catalogs(
            type="series",
            id=f"uakino_search",
            name=f"UAKino Search",
            extra=[{"name": "search", "isRequired": True}],
        )
    )
    # manifest.catalogs[1].extra.append({"name": "search", "isRequired": True})

    return manifest


# Catalog
@router.get("/catalog/{type_}/uakino_{value}.json", tags=[settings.name])
@cache(expire=24 * 60)
async def addon_catalog(
    type_: str,
    value: str,
    session: aiohttp.ClientSession = Depends(get_session),
) -> dict[str, list[Preview]]:
    if value == "anime":
        value = "animeukr"
    if value == "cartoon":
        value = "cartoon/f/p.cat=23/sort=date;desc/"
    if value == "cartoon-series":
        value = "cartoon/cartoonseries"
    print(f"{settings.main_url}/{value}")
    async with session.get(f"{settings.main_url}/{value}",headers=headers) as response:
        return await get_previews_metadata(await response.text(), type_)


# Pagination
@router.get(
    "/catalog/{type_}/uakino_{value}/skip={skip}.json", tags=[settings.name]
)
@cache(expire=24 * 60)
async def addon_catalog_skip(
    type_: str,
    value: str,
    skip: int,
    session: aiohttp.ClientSession = Depends(get_session),
) -> dict[str, list[Preview]]:
    async with session.get(f"{settings.main_url}/{value}/page/{int(skip / 24) + 1}/") as response:
        return await get_previews_metadata(await response.text(), type_)


# Custom Metadata
@router.get("/meta/{type_}/{id}.json", tags=[settings.name])
@cache(expire=24 * 60)
async def addon_meta(
    id: str, type_: str, session: aiohttp.ClientSession = Depends(get_session)
) -> dict[str, Series]:
    real_id = extract_id(id)
    async with session.get(f"{settings.main_url}/{real_id}.html",headers=headers) as response:
        series_metadata = await get_series_metadata(
            real_id,
            await response.text(),
            await get_videos(real_id, await response.text(), session),
            type_,
        )

    return series_metadata


# Series
@router.get("/stream/{type_}/{id}/{season}/{episode}.json", tags=[settings.name])
@router.get("/stream/{type_}/{id}/{episode}.json", tags=[settings.name])
@router.get("/stream/{type_}/{id}.json", tags=[settings.name])
@cache(expire=24 * 60)
async def addon_stream(
    id: str, season: str = None, episode: str = None, session: aiohttp.ClientSession = Depends(get_session)
) -> dict[str, list[Stream]]:
    print(f"{settings.main_url}/{id}.html")
    async with session.get(f"{settings.main_url}/{id}.html",headers=headers) as response:
        streams = await get_streams(id, season, episode, session, await response.text())
    return streams


# Search
@router.get(
    "/catalog/series/uakino_search/search={query}.json", tags=[settings.name]
)
@cache(expire=24 * 60)
async def addon_search(
    query: str,
    session: aiohttp.ClientSession = Depends(get_session),
) -> dict[str, list[Preview]]:
    query_params = {
        "do": "search",
        "subaction": "search",
        "story": query,
    }
    url = f"{settings.main_url}?{urlencode(query_params)}"
    async with session.post(f"{settings.main_url}", data={"do": "search", "subaction": "search", "story": query}, headers=headers) as response:
        response_data = await response.text()

    return await get_previews_metadata(response_data, "series")
