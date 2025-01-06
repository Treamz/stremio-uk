from fastapi import Depends, APIRouter
from fastapi_cache.decorator import cache
from app.schemas import Manifest, Catalogs, Preview, Series, Stream

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

router = APIRouter(prefix="/eneyida")


@router.get("/manifest.json", tags=[settings.name])
@cache()
def addon_manifest() -> Manifest:
    manifest = Manifest(
        id="ua.cakestwix.stremio.eneyida",
        version="1.1.0",
        logo=f"https://www.google.com/s2/favicons?domain={settings.main_url}&sz=128",
        name="Eneyida",
        description="Мета проекту «Енеїда» - популяризація української мови, демонстрація її різнобарвності та сучасності. Ми плануємо робити це через ретрансляцію якісного кіно, мультфільмів, телесеріалів та різноманітних телешоу в якісному українському перекладі. Тож, у добрий шлях дорогі конфіденти!.",
        types=["movie", "series"],
        catalogs=[
            Catalogs(
                type=item[1],
                id=f"eneyida_{item[2]}",
                name=f"{item[0]}/Eneyida",
                extra=[
                        { "name": "skip", "isRequired": False },
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
            "stream",
#             "subtitles"
        ],
         idPrefixes=['eneyida_'],

    )

    # Search Catalog
    manifest.catalogs.append(
        Catalogs(
            type="series",
            id=f"eneyida_search",
            name=f"Eneyida Search",
            extra=[{"name": "search", "isRequired": True}],
        )
    )
    # manifest.catalogs[1].extra.append({"name": "search", "isRequired": True})

    return manifest


# Catalog
@router.get("/catalog/{type_}/eneyida_{value}.json", tags=[settings.name])
@cache(expire=24 * 60)
async def addon_catalog(
    type_: str,
    value: str,
    session: aiohttp.ClientSession = Depends(get_session),
) -> dict[str, list[Preview]]:
    print("HELLO")
    print(f"{settings.main_url}/{value}")
    async with session.get(f"{settings.main_url}/{value}") as response:
        return await get_previews_metadata(await response.text(), type_)


# Pagination
@router.get(
    "/catalog/{type_}/eneyida_{value}/skip={skip}.json", tags=[settings.name]
)
@cache(expire=24 * 60)
async def addon_catalog_skip(
    type_: str,
    value: str,
    skip: int,
    session: aiohttp.ClientSession = Depends(get_session),
) -> dict[str, list[Preview]]:
    print("SKIPP")
    async with session.get(f"{settings.main_url}/{value}/page/{int(skip / 24) + 1}/") as response:
        return await get_previews_metadata(await response.text(), type_)


# Custom Metadata
@router.get("/meta/{type_}/{id}.json", tags=[settings.name])
@cache(expire=24 * 60)
async def addon_meta(
    id: str, type_: str, session: aiohttp.ClientSession = Depends(get_session)
) -> dict[str, Series]:
    real_id = extract_id(id)
    async with session.get(f"{settings.main_url}/{real_id}.html") as response:
        series_metadata = await get_series_metadata(
            real_id,
            await response.text(),
            await get_videos(real_id, await response.text(), session),
            type_,
        )

    return series_metadata


# Series
@router.get("/stream/{type_}/{id}/{season}/{episode}.json", tags=[settings.name])
@router.get("/stream/{type_}/{id}.json", tags=[settings.name])
@cache(expire=24 * 60)
async def addon_stream(
    id: str, season: str = None, episode: str = None, session: aiohttp.ClientSession = Depends(get_session)
) -> dict[str, list[Stream]]:
    real_id = extract_id(id)
    print(f"{settings.main_url}/{real_id}.html")
    async with session.get(f"{settings.main_url}/{real_id}.html") as response:
        streams = await get_streams(real_id, season, episode, session, await response.text())
    return streams


# Search
@router.get(
    "/catalog/series/eneyida_search/search={query}.json", tags=[settings.name]
)
@cache(expire=24 * 60)
async def addon_search(
    query: str,
    session: aiohttp.ClientSession = Depends(get_session),
) -> dict[str, list[Preview]]:
    async with session.post(f"{settings.main_url}", data={"do": "search", "subaction": "search", "story": query}) as response:
        response_data = await response.text()

    return await get_previews_metadata(response_data, "series")
