from pydantic import BaseModel
from typing import List, Optional
from typing import List, Union, Dict


class Preview(BaseModel):
    id: str
    type: str
    name: str
    genres: list[str]
    poster: Optional[str] = None
    description: str


class Stream(BaseModel):
    name: str
    url: str | list[str] | None


class Videos(BaseModel):
    id: str
    title: str
    thumbnail: Optional[str] = None
    released: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    streams: Optional[list[Stream]] = None



class Series(Preview):
    director: list[str]
    runtime: Optional[str] = None
    background: str
    videos: list[Videos]



class Catalogs(BaseModel):
    type: str
    id: str
    name: str
    extra: list[dict]


class Manifest(BaseModel):
    id: str
    version: str
    logo: str
    name: str
    description: str
    types: list[str]
    catalogs: list[Catalogs]
    resources: List[Union[str, Dict[str, Union[str, List[str]]]]]
    idPrefixes: list[str]

