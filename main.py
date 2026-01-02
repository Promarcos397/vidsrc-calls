from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import gzip
from models import vidsrctoget, vidsrcmeget, info, fetch
from io import BytesIO
from fastapi.responses import StreamingResponse

# --- Cloudflare Imports ---
from js import Response as CfResponse
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/')
async def index():
    return await info()

@app.get('/vidsrc/{dbid}')
async def vidsrc(dbid:str, s:int=None, e:int=None):
    if dbid:
        return {
            "status": 200,
            "info": "success",
            "sources": await vidsrctoget(dbid, s, e)
        }
    else:
        raise HTTPException(status_code=404, detail=f"Invalid id: {dbid}")

@app.get('/vsrcme/{dbid}')
async def vsrcme(dbid:str = '', s:int=None, e:int=None, l:str='eng'):
    if dbid:
        return {
            "status": 200,
            "info": "success",
            "sources": await vidsrcmeget(dbid, s, e)
        }
    else:
        raise HTTPException(status_code=404, detail=f"Invalid id: {dbid}")

@app.get('/streams/{dbid}')
async def streams(dbid:str = '', s:int=None, e:int=None, l:str='eng'):
    if dbid:
        # Note: Ensure vidsrcmeget and vidsrctoget return lists so they can be added
        return {
            "status": 200,
            "info": "success",
            "sources": await vidsrcmeget(dbid, s, e) + await vidsrctoget(dbid, s, e)
        }
    else:
        raise HTTPException(status_code=404, detail=f"Invalid id: {dbid}")
    
@app.get("/subs")
async def subs(url: str):
    try:
        response = await fetch(url)
        # Decompress gzip
        with gzip.open(BytesIO(response.content), 'rt', encoding='utf-8') as f:
            subtitle_content = f.read()
            
        # Cloudflare Note: StreamingResponse acts differently in Workers.
        # Since you are reading the whole file into memory anyway (f.read()), 
        # it is safer to return a direct response here for stability.
        return StreamingResponse(
            iter([subtitle_content]), 
            media_type="application/octet-stream", 
            headers={"Content-Disposition": "attachment; filename=subtitle.srt"}
        )

    except Exception as e:
        # Log error for debugging
        print(f"Error in subs: {e}")
        raise HTTPException(status_code=500, detail="Error fetching subtitle")

# ==============================================================================
# CLOUDFLARE WORKER ENTRY POINT (THE BRIDGE)
# ==============================================================================
async def on_fetch(request, env):
    import asgi
    return await asgi.fetch(app, request, env)
