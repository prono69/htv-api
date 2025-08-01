from typing import Optional
from fastapi import FastAPI, HTTPException
import httpx
import random
import string

app = FastAPI()

# Utility function to generate random hex strings
def random_hex(length=32):
    return ''.join(random.choices(string.hexdigits, k=length))

# Fetch JSON from the given URL with required headers
async def jsongen(url):
    headers = {
        "X-Signature-Version": "web2",
        "X-Signature": random_hex(),
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {e}")

# Route to fetch trending videos
@app.get("/trending/{time}")
async def get_trending(
    time: str,
    page: Optional[int] = 0,
    order_by: Optional[str] = None,
    ordering: Optional[str] = None,
    limit: Optional[int] = None  # New optional limit parameter
):
    # Base URL without optional params
    trending_url = f"https://hanime.tv/api/v8/browse-trending?time={time}&page={page}"
    
    # Add optional params if they are provided
    if order_by:
        trending_url += f"&order_by={order_by}"
    if ordering:
        trending_url += f"&ordering={ordering}"
    
    urldata = await jsongen(trending_url)
    
    # Get all results or apply limit if specified
    hentai_videos = urldata["hentai_videos"]
    if limit is not None:
        hentai_videos = hentai_videos[:limit]
    
    jsondata = [
        {
            "id": x["id"],
            "name": x["name"],
            "slug": x["slug"],
            "monthly_rank": x["monthly_rank"],
            "cover_url": x["cover_url"],
            "views": x["views"],
            "link": f"/watch/{x['slug']}",
        }
        for x in hentai_videos
    ]
    
    # Build next_page URL with all current parameters
    next_page_params = f"page={page + 1}"
    if order_by:
        next_page_params += f"&order_by={order_by}"
    if ordering:
        next_page_params += f"&ordering={ordering}"
    if limit:
        next_page_params += f"&limit={limit}"
    
    next_page = f"/trending/{time}?{next_page_params}"
    
    return {
        "creator": "EYEPATCH",
        "api_version": "1.2",
        "results": jsondata,
        "next_page": next_page,
    }

# Route to fetch video details
@app.get("/watch/{slug}")
async def get_video(slug: str):
    video_api_url = f"https://hanime.tv/api/v8/video?id={slug}"
    video_data = await jsongen(video_api_url)
    tags = [
        {"name": t["text"], "link": f"/hentai-tags/{t['text']}/0"}
        for t in video_data["hentai_tags"]
    ]
    streams = [
        {"width": s["width"], "height": s["height"], "size_mbs": s["filesize_mbs"], "url": s["url"]}
        for s in video_data["videos_manifest"]["servers"][0]["streams"]
    ]
    episodes = [
        {
            "id": e["id"],
            "name": e["name"],
            "slug": e["slug"],
            "cover_url": e["cover_url"],
            "views": e["views"],
            "link": f"/watch/{e['slug']}",
        }
        for e in video_data["hentai_franchise_hentai_videos"]
    ]
    jsondata = {
        "id": video_data["hentai_video"]["id"],
        "name": video_data["hentai_video"]["name"],
        "description": video_data["hentai_video"]["description"],
        "poster_url": video_data["hentai_video"]["poster_url"],
        "cover_url": video_data["hentai_video"]["cover_url"],
        "views": video_data["hentai_video"]["views"],
        "streams": streams,
        "tags": tags,
        "episodes": episodes,
    }
    return {
        "creator": "EYEPATCH",
        "api_version": "1.2",
        "results": [jsondata],
    }

# Route to fetch browse data
@app.get("/browse/{type}")
async def get_browse(type: str):
    browse_url = "https://hanime.tv/api/v8/browse"
    data = await jsongen(browse_url)
    jsondata = data[type]
    if type == "hentai_tags":
        jsondata = [{"name": x["text"], "url": f"/hentai-tags/{x['text']}/0"} for x in jsondata]
    elif type == "brands":
        jsondata = [{"name": x["name"], "url": f"/brands/{x['slug']}/0"} for x in jsondata]
    return {
        "creator": "EYEPATCH",
        "api_version": "1.2",
        "results": jsondata,
    }

# Route to fetch tags
@app.get("/tags")
async def get_tags():
    browse_url = "https://hanime.tv/api/v8/browse"
    data = await jsongen(browse_url)
    jsondata = [{"name": x["text"], "url": f"/tags/{x['text']}/0"} for x in data["hentai_tags"]]
    return {
        "creator": "EYEPATCH",
        "api_version": "1.2",
        "results": jsondata,
    }

# Route to fetch browse videos
@app.get("/{type}/{category}")
async def get_browse_videos(type: str, category: str, page: Optional[int] = 0):
    browse_url = f"https://hanime.tv/api/v8/browse/{type}/{category}?page={page}&order_by=views&ordering=desc"
    browsedata = await jsongen(browse_url)
    jsondata = [
        {
            "id": x["id"],
            "name": x["name"],
            "slug": x["slug"],
            "cover_url": x["cover_url"],
            "views": x["views"],
            "link": f"/watch/{x['slug']}",
        }
        for x in browsedata["hentai_videos"]
    ]
    next_page = f"/{type}/{category}?{page + 1}"
    return {
        "creator": "EYEPATCH",
        "api_version": "1.2",
        "results": jsondata,
        "next_page": next_page,
    }

# Root route
@app.get("/")
async def root():
    return {
        "creator": "EYEPATCH",
        "api_version": "1.2",
        "message": "Welcome to Hanime API 👀",
    }

# Custom error handler
@app.exception_handler(Exception)
async def custom_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "creator": "EYEPATCH",
            "api_version": "1.2",
            "error": "Something went wrong",
            "details": str(exc),
        },
    )
    