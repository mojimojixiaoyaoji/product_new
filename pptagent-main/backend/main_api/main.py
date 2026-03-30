import asyncio
import json
import re
import os
import dotenv
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Query, Request, Response, Form
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import httpx
import shutil
from typing import Optional
import time
import logging

dotenv.load_dotenv()

from outline_client import A2AOutlineClientWrapper
from content_client import A2AContentClientWrapper

logger = logging.getLogger(__name__)

# 加载统一环境配置
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    dotenv.load_dotenv(env_file)
else:
    dotenv.load_dotenv()

OUTLINE_API = os.environ.get("OUTLINE_API", f"http://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('OUTLINE_API_PORT', '10001')}")
CONTENT_API = os.environ.get("CONTENT_API", f"http://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('CONTENT_API_PORT', '10011')}")
app = FastAPI()

# Allow CORS for the frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AipptRequest(BaseModel):
    content: str
    language: str
    model: str
    stream: bool

async def stream_agent_response(prompt: str, language: str = "chinese"):
    """A generator that yields parts of the agent response."""
    outline_wrapper = A2AOutlineClientWrapper(session_id=uuid.uuid4().hex, agent_url=OUTLINE_API)
    async for chunk_data in outline_wrapper.generate(prompt, language=language):
        logger.info(f"生成大纲输出的chunk_data: {chunk_data}")
        if chunk_data["type"] == "text":
            yield chunk_data["text"]


@app.post("/tools/aippt_outline")
async def aippt_outline(request: AipptRequest):
    assert request.stream, "只支持流式的返回大纲"
    logger.info(f"前端*outline***=====>用户输入：{request.language}")
    return StreamingResponse(stream_agent_response(request.content, request.language), media_type="text/plain")


@app.post("/tools/aippt_outline_from_file")
async def aippt_outline_from_file(
    user_id: int|str = Form(...),
    file: UploadFile = File(None),  # 允许缺省，这样我们可以决定走 file 或 url
    url: str | None = Form(None),
    folder_id: int|str = Form(0),
    file_type: str | None = Form(None),
    language: str = Form("chinese"),  # 添加language参数，默认为chinese
):
    """
    对齐 personaldb 的 /upload/：
    - 必填: userId, fileId
    - 可选: folderId (默认0), fileType
    - file 与 url 互斥，至少一个
    """
    personaldb_api_url = os.getenv("PERSONAL_DB")
    if not personaldb_api_url:
        raise HTTPException(status_code=500, detail="PERSONAL_DB 未配置")

    # 互斥校验（与 personaldb 完全一致）
    has_file = file is not None
    has_url = bool(url and url.strip())

    # 生成 fileId（字符串更稳；personaldb 会 int()）
    file_id = str(int(time.time() * 1000))

    # 推断 fileType（当上传文件时且未显式传入）
    if has_file and not file_type:
        if file.filename and "." in file.filename:
            file_type = file.filename.rsplit(".", 1)[-1]
        else:
            file_type = "unknown"

    # 组装 multipart/form-data
    # 注意：即使是 url 分支，也仍用 multipart，personaldb 也能解析 form
    data = {
        "userId": str(user_id),
        "fileId": file_id,
        "folderId": str(folder_id),
    }
    if file_type:
        data["fileType"] = file_type
    if has_url:
        data["url"] = url.strip()

    files_payload = None
    if has_file:
        # 读取一次到内存，httpx 需要 (filename, bytes/obj, content_type)
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="文件内容为空")
        files_payload = {
            "file": (
                file.filename or "uploaded_file",
                file_bytes,
                file.content_type or "application/octet-stream",
            )
        }

    upload_url = f"{personaldb_api_url.rstrip('/')}/upload/"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                upload_url,
                data=data,
                files=files_payload,
                timeout=360.0,
            )
            # 不直接 raise，先打日志方便定位
            if resp.status_code >= 400:
                # 打印下游返回体，personaldb 对错误信息写得很清楚
                logger.info(f"[personaldb {resp.status_code}] {resp.text}")
                resp.raise_for_status()

            # personaldb 的处理函数最终会返回一个 JSON（你上游期望里要有 markdown_content）
            try:
                result = resp.json()
            except ValueError:
                raise HTTPException(status_code=502, detail=f"personaldb 返回的不是 JSON：{resp.text}")

            markdown_content = result.get("markdown_content")
            if markdown_content is None:
                raise HTTPException(status_code=500, detail="personaldb 响应缺少 'markdown_content'")
            logger.info(f"本地上传文件*outline***=====>：{ {'language': language} }")

            return StreamingResponse(stream_agent_response(markdown_content, language), media_type="text/plain")

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request to personaldb timed out.")
        except httpx.HTTPStatusError as exc:
            # 透传 personaldb 的错误详情，便于你在日志里看到具体字段问题
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Error connecting to personaldb: {exc}")


@app.post("/tools/convert_file")
async def convert_file(file: UploadFile = File(...)):
    """将 doc/docx/pdf 等文件转换为 markdown"""
    import tempfile
    from markitdown import MarkItDown

    if not file:
        raise HTTPException(status_code=400, detail="未提供文件")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 创建临时文件
    suffix = ""
    if file.filename and "." in file.filename:
        suffix = "." + file.filename.rsplit(".", 1)[-1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        md = MarkItDown()
        result = md.convert(tmp_path)
        # markitdown 返回 DocumentConverterResult，用 text_content 获取文本
        markdown_content = result.text_content if hasattr(result, 'text_content') else str(result)
        return {"markdown_content": markdown_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件转换失败: {str(e)}")
    finally:
        # 删除临时文件
        Path(tmp_path).unlink(missing_ok=True)


class AipptContentRequest(BaseModel):
    content: str
    language: str = "zh"  #默认中文
    sessionId: str = ""  # 当使用知识库时，需要根据用户的user_id查询对应的知识库
    generateFromUploadedFile: bool = False  # 是否从上传的文件中生成PPT内容
    generateFromWebSearch: bool = True  # 是否从网络搜索中生成PPT内容

async def stream_content_response(markdown_content: str, language, generateFromUploadedFile, generateFromWebSearch, user_id):
    match = re.search(r"(# .*)", markdown_content, flags=re.DOTALL)
    result = markdown_content[match.start():] if match else markdown_content
    logger.info(f"用户输入的markdown大纲是：{result}")

    content_wrapper = A2AContentClientWrapper(session_id=uuid.uuid4().hex, agent_url=CONTENT_API)

    search_engine = []
    if generateFromUploadedFile:
        search_engine.append("KnowledgeBaseSearch")
    if generateFromWebSearch:
        search_engine.append("DocumentSearch")

    metadata = {"user_id": user_id, "search_engine": search_engine, "language": language}
    logger.info(f"前端*内容**=====>metadata数据为：{metadata}")

    last_flush = asyncio.get_event_loop().time()

    async for chunk_data in content_wrapper.generate(user_question=result, metadata=metadata):
        logger.info(f"生成正文输出的chunk_data: {chunk_data}")

        # 心跳：每15秒发一次注释，避免某些代理断连接
        now = asyncio.get_event_loop().time()
        if now - last_flush > 10:
            yield b": keep-alive\n\n"
            last_flush = now

        if chunk_data.get("type") == "text":
            # 注意：每条 SSE 事件以空行结束
            payload = chunk_data["text"]
            yield f"data: {payload}\n\n".encode("utf-8")

    # 可选：显式结束信号（前端可据此收尾）
    yield b"data: [DONE]\n\n"

@app.post("/tools/aippt")
async def aippt_content(request: AipptContentRequest):
    markdown_content = request.content
    # 兼容旧字段名：如果 user_id 为空就用 sessionId
    user_id = getattr(request, "user_id", None) or getattr(request, "sessionId", None)

    async def event_generator():
        async for chunk in stream_content_response(
            markdown_content,
            language=request.language,
            generateFromUploadedFile=request.generateFromUploadedFile,
            generateFromWebSearch=request.generateFromWebSearch,
            user_id=user_id
        ):
            yield chunk

    # 关键：SSE 推荐这些头
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.get("/data/{filename}")
async def get_data(filename: str):
    # Check new templates directory first
    base_dir = get_templates_dir()
    new_path = base_dir / "templates" / filename
    if new_path.exists():
        return FileResponse(new_path)
    # Fallback to old template directory
    file_path = os.path.join("./template", filename)
    return FileResponse(file_path)

class AipptByIDRequest(BaseModel):
    id: str
    language: str = "chinese"  # 添加language字段，默认为chinese

async def aippt_file_id_streamer(id: str, language: str = "chinese"):
    """根据用户的已有的文件数据中的文件id来生成ppt
    id: 文件的id，例如论文的pmid
    """
    yield json.dumps({"type": "status", "message": "正在解析文件..."}, ensure_ascii=False) + '\n'
    paper_markdown = ""
    if not paper_markdown:
        yield json.dumps({"type": "status", "message": "没有找到该文章"}, ensure_ascii=False) + '\n'
        return
    personaldb_api_url = os.getenv("PERSONAL_DB")
    if not personaldb_api_url:
        raise HTTPException(status_code=500, detail="PERSONAL_DB 未配置")
    # 论文名称
    file_name = f"{id}.md"
    data = {
        "userId": id,
        "fileId": id,
        "folderId": 123,
        "fileType": "txt"
    }
    files = {"file": (file_name, paper_markdown, "text/plain")}
    upload_url = f"{personaldb_api_url.rstrip('/')}/upload/"
    response = httpx.post(upload_url, data=data, files=files, timeout=40.0)
    result = response.json()
    if not result.get("id"):
        yield json.dumps({"type": "status", "message": "论文向量化失败，请联系管理员"}, ensure_ascii=False) + '\n'
    yield json.dumps({"type": "status", "message": "正在生成大纲..."}, ensure_ascii=False) + '\n'
    outline = ""
    async for outline_trunk in stream_agent_response(paper_markdown, language):
        outline += outline_trunk
    yield json.dumps({"type": "status", "message": "大纲生成完毕，即将生成PPT..."}, ensure_ascii=False) + '\n'

    match = re.search(r"(# .*)", outline, flags=re.DOTALL)

    if match:
        result = outline[match.start():]
    else:
        result = outline
    logger.info(f"用户输入的markdown大纲是：{result}")
    content_wrapper = A2AContentClientWrapper(session_id=uuid.uuid4().hex, agent_url=CONTENT_API)
    # 传入不同的参数，使用不同的搜索,可以同时使用多个搜索
    search_engine = ["KnowledgeBaseSearch"]
    # 方便测试，这个已经在知识库中插入了对应的数据
    metadata = {"user_id": id, "search_engine": search_engine, "language": language}
    logger.info(f"aippt_by_id**=====>metadata数据为：{metadata}")
    async for chunk_data in content_wrapper.generate(user_question=result, metadata=metadata):
        logger.info(f"生成正文输出的chunk_data: {chunk_data}")
        if chunk_data["type"] == "text":
            slide = chunk_data["text"]
            yield slide + '\n'


@app.post("/tools/aippt_by_id")
async def aippt_by_id(request: AipptByIDRequest):
    return StreamingResponse(aippt_file_id_streamer(request.id, request.language), media_type="application/json; charset=utf-8")


@app.get("/files/{user_id}")
async def list_user_files(user_id: int):
    """
    列出指定用户的所有文件信息
    """
    personaldb_api_url = os.environ["PERSONAL_DB"]
    url = f"{personaldb_api_url}/files/{user_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Error connecting to personaldb: {exc}")
        except httpx.HTTPStatusError as exc:
            # 转发下游服务的错误
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)


@app.get("/proxy")
async def proxy(request: Request, url: str = Query(..., description="Target absolute URL")):
    """
    透明代理上游资源，转发部分请求头，透传关键响应头，并允许前端同源访问。
    适合图片/音视频等二进制内容。
    """
    HEADERS_TO_FORWARD = {"Range", "User-Agent"}  # 需要时可扩展
    HEADERS_TO_COPY = {
        "Content-Type",
        "Content-Length",
        "Content-Disposition",
        "Accept-Ranges",
        "ETag",
        "Last-Modified",
        "Cache-Control",
        "Expires",
    }
    forward_headers = {}
    for h in HEADERS_TO_FORWARD:
        v = request.headers.get(h)
        if v:
            forward_headers[h] = v

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            upstream = await client.get(url, headers=forward_headers)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Upstream fetch error: {e!s}")

    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail="Upstream error")

    headers = {}
    for h in HEADERS_TO_COPY:
        if h in upstream.headers:
            headers[h] = upstream.headers[h]

    # 允许被前端同源读取
    headers["Access-Control-Allow-Origin"] = "*"
    # 给静态资源加简单缓存（按需调整）
    headers.setdefault("Cache-Control", "public, max-age=86400")

    return StreamingResponse(
        upstream.aiter_bytes(),
        status_code=upstream.status_code,
        headers=headers,
        media_type=upstream.headers.get("Content-Type"),
    )

# ============== Admin Template Management API ==============
import uuid

def verify_passkey(x_passkey: str = Header(...)):
    """Verify passkey from request header"""
    expected_passkey = os.environ.get("ADMIN_PASSKEY", "Allin123")
    if x_passkey != expected_passkey:
        raise HTTPException(status_code=401, detail="Invalid passkey")

def get_templates_dir() -> Path:
    """Get templates directory path"""
    base_dir = Path(os.environ.get("TEMPLATES_DIR", "/mnt/shared-data/ppt-templates-covers"))
    templates_dir = base_dir / "templates"
    covers_dir = base_dir / "covers"
    templates_dir.mkdir(parents=True, exist_ok=True)
    covers_dir.mkdir(parents=True, exist_ok=True)
    return base_dir

def get_templates_list_path() -> Path:
    """Get path to templates list JSON file"""
    base_dir = get_templates_dir()
    return base_dir / "admin_templates_list.json"

def load_templates_list() -> list:
    """Load templates list from JSON file"""
    list_path = get_templates_list_path()
    if list_path.exists():
        with open(list_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_templates_list(templates_list: list):
    """Save templates list to JSON file"""
    list_path = get_templates_list_path()
    with open(list_path, "w", encoding="utf-8") as f:
        json.dump(templates_list, f, ensure_ascii=False, indent=2)

def find_cover_ext(base_dir: Path, template_id: str) -> str:
    """Find existing cover extension for a template"""
    for ext in ["jpg", "png", "webp", "jpeg"]:
        if (base_dir / "covers" / f"{template_id}.{ext}").exists():
            return ext
    return ""

@app.get("/admin/templates")
def list_templates(x_passkey: str = Header(...)):
    """List all templates with cover URLs"""
    verify_passkey(x_passkey)
    base_dir = get_templates_dir()
    templates_list = load_templates_list()

    templates = []
    for item in templates_list:
        template_id = item["json_filename"].split(".")[0]
        cover_ext = find_cover_ext(base_dir, template_id)
        cover_url = f"/api/admin/covers/{template_id}" if cover_ext else ""

        templates.append({
            "id": template_id,
            "name": item["name"],
            "cover": cover_url,
            "json_filename": item["json_filename"],
            "cover_filename": item.get("cover_filename", ""),
            "created_at": item.get("created_at", ""),
            "updated_at": item.get("updated_at", "")
        })

    return {"data": templates}

@app.post("/admin/templates")
async def create_template(
    x_passkey: str = Header(...),
    name: str = Form(...),
    template_file: UploadFile = File(...),
    cover_file: Optional[UploadFile] = File(None)
):
    """Create a new template"""
    verify_passkey(x_passkey)
    base_dir = get_templates_dir()

    # Generate UUID-based ID
    template_id = uuid.uuid4().hex
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    # Get file extension
    json_ext = Path(template_file.filename).suffix.lower() if template_file.filename else ".json"
    json_filename = f"{template_id}{json_ext}"

    # Save template JSON
    template_content = await template_file.read()
    try:
        template_data = json.loads(template_content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON template file")

    template_data["created_at"] = now
    template_data["updated_at"] = now
    if "name" not in template_data:
        template_data["name"] = name

    template_path = base_dir / "templates" / json_filename
    with open(template_path, "w", encoding="utf-8") as f:
        json.dump(template_data, f, ensure_ascii=False, indent=2)

    # Save cover image if provided
    cover_filename = ""
    if cover_file:
        ext = Path(cover_file.filename).suffix.lower() if cover_file.filename else ".jpg"
        if ext == ".jpeg":
            ext = ".jpg"
        cover_filename = f"{template_id}{ext}"
        cover_path = base_dir / "covers" / cover_filename
        with open(cover_path, "wb") as f:
            f.write(await cover_file.read())

    # Update templates list
    templates_list = load_templates_list()
    templates_list.append({
        "json_filename": json_filename,
        "name": name,
        "cover_filename": cover_filename,
        "created_at": now,
        "updated_at": now
    })
    save_templates_list(templates_list)

    return {"id": template_id, "name": name, "message": "Template created successfully"}

@app.get("/admin/templates/{template_id}")
def get_template(template_id: str, x_passkey: str = Header(...)):
    """Get a single template"""
    verify_passkey(x_passkey)
    base_dir = get_templates_dir()
    templates_list = load_templates_list()

    # Find the template in list
    item = None
    for t in templates_list:
        if t["json_filename"].split(".")[0] == template_id:
            item = t
            break

    if not item:
        raise HTTPException(status_code=404, detail="Template not found")

    template_path = base_dir / "templates" / item["json_filename"]
    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.put("/admin/templates/{template_id}")
async def update_template(
    template_id: str,
    x_passkey: str = Header(...),
    name: Optional[str] = Form(None),
    template_file: Optional[UploadFile] = File(None),
    cover_file: Optional[UploadFile] = File(None)
):
    """Update a template - generates new UUID filename to avoid caching issues"""
    verify_passkey(x_passkey)
    base_dir = get_templates_dir()
    templates_list = load_templates_list()

    # Find the template in list
    item_index = None
    item = None
    for i, t in enumerate(templates_list):
        if t["json_filename"].split(".")[0] == template_id:
            item_index = i
            item = t
            break

    if item is None:
        raise HTTPException(status_code=404, detail="Template not found")

    # Store old filenames for deletion
    old_json_filename = item["json_filename"]
    old_cover_filename = item.get("cover_filename", "")
    old_template_path = base_dir / "templates" / old_json_filename

    # Generate new UUID for updated files
    new_template_id = uuid.uuid4().hex
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    # Load template data - validate before deleting old files
    template_data = {}
    if template_file:
        content = await template_file.read()
        try:
            template_data = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON template file")
    else:
        # No new file - load existing data
        if not old_template_path.exists():
            raise HTTPException(status_code=404, detail="Template file not found")
        with open(old_template_path, "r", encoding="utf-8") as f:
            template_data = json.load(f)

    # Update name if provided
    if name:
        template_data["name"] = name

    template_data["updated_at"] = now

    # Save new JSON file with new UUID
    json_ext = ".json"
    new_json_filename = f"{new_template_id}{json_ext}"
    new_template_path = base_dir / "templates" / new_json_filename
    with open(new_template_path, "w", encoding="utf-8") as f:
        json.dump(template_data, f, ensure_ascii=False, indent=2)

    # Delete old JSON only after new file is successfully written
    if template_file:
        # New file uploaded - delete old after new is written
        if old_template_path.exists():
            old_template_path.unlink()
    else:
        # No new file - we re-saved with new name, delete old one
        if old_template_path.exists():
            old_template_path.unlink()

    # Handle cover file
    new_cover_filename = ""
    if cover_file:
        ext = Path(cover_file.filename).suffix.lower() if cover_file.filename else ".jpg"
        if ext == ".jpeg":
            ext = ".jpg"
        new_cover_filename = f"{new_template_id}{ext}"
        cover_path = base_dir / "covers" / new_cover_filename
        with open(cover_path, "wb") as f:
            f.write(await cover_file.read())
        # Delete old cover only after new cover is successfully written
        if old_cover_filename:
            old_cover_path = base_dir / "covers" / old_cover_filename
            if old_cover_path.exists():
                old_cover_path.unlink()
    else:
        # No new cover - copy old cover to new location if it existed
        if old_cover_filename:
            old_ext = Path(old_cover_filename).suffix.lower()
            if old_ext == ".jpeg":
                old_ext = ".jpg"
            new_cover_filename = f"{new_template_id}{old_ext}"
            old_cover_path = base_dir / "covers" / old_cover_filename
            new_cover_path = base_dir / "covers" / new_cover_filename
            if old_cover_path.exists():
                import shutil
                shutil.copy(old_cover_path, new_cover_path)
                old_cover_path.unlink()  # Delete old cover after copying

    # Remove old item and add new entry in templates_list
    templates_list.pop(item_index)
    templates_list.append({
        "json_filename": new_json_filename,
        "name": name or template_data.get("name", item["name"]),
        "cover_filename": new_cover_filename,
        "created_at": item.get("created_at", now),
        "updated_at": now
    })
    save_templates_list(templates_list)

    return {"id": new_template_id, "name": name or template_data.get("name", item["name"]), "message": "Template updated successfully"}

@app.delete("/admin/templates/{template_id}")
def delete_template(template_id: str, x_passkey: str = Header(...)):
    """Delete a template"""
    verify_passkey(x_passkey)
    base_dir = get_templates_dir()
    templates_list = load_templates_list()

    # Find and remove from list
    item = None
    for i, t in enumerate(templates_list):
        if t["json_filename"].split(".")[0] == template_id:
            item = t
            templates_list.pop(i)
            break

    if item is None:
        raise HTTPException(status_code=404, detail="Template not found")

    # Delete template JSON
    template_path = base_dir / "templates" / item["json_filename"]
    if template_path.exists():
        template_path.unlink()

    # Delete cover image
    cover_filename = item.get("cover_filename", "")
    if cover_filename:
        cover_path = base_dir / "covers" / cover_filename
        if cover_path.exists():
            cover_path.unlink()

    save_templates_list(templates_list)
    return {"message": "Template deleted successfully"}

@app.get("/admin/covers/{template_id}")
def get_cover_image(template_id: str, request: Request):
    """Serve cover images"""
    base_dir = get_templates_dir()

    for ext in ["jpg", "png", "webp", "jpeg"]:
        cover_path = base_dir / "covers" / f"{template_id}.{ext}"
        if cover_path.exists():
            return FileResponse(cover_path)

    raise HTTPException(status_code=404, detail="Cover not found")

# ============== Replace original /templates endpoint ==============

@app.get("/templates")
def get_templates_public():
    """Public endpoint to list all templates (no passkey required)"""
    # Static hardcoded templates
    templates = [
        { "name": "红色通用", "id": "template_1", "cover": "/api/data/template_1.jpg" },
        { "name": "蓝色通用", "id": "template_2", "cover": "/api/data/template_2.jpg" },
        { "name": "紫色通用", "id": "template_3", "cover": "/api/data/template_3.jpg" },
        { "name": "莫兰迪配色", "id": "template_4", "cover": "/api/data/template_4.jpg" },
    ]

    # Add dynamic templates from shared storage
    base_dir = get_templates_dir()
    templates_list = load_templates_list()

    for item in templates_list:
        template_id = item["json_filename"].split(".")[0]
        cover_filename = item.get("cover_filename", "")
        cover_url = f"/api/admin/covers/{template_id}" if cover_filename else ""

        templates.append({
            "id": template_id,
            "name": item["name"],
            "cover": cover_url
        })

    return {"data": templates}

@app.get("/healthz")
def healthz():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("MAIN_API_PORT", "6800"))
    uvicorn.run(app, host=host, port=port)
