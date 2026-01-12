"""
RAG Stage - Document indexing and querying
"""
import os
import re
import base64
import logging
import asyncio
import aiohttp
import urllib.parse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from ...utils import save_json
from ..paths import get_rag_checkpoint

logger = logging.getLogger(__name__)


def _get_image_mime_type(image_path: str) -> str:
    """Get MIME type for image file based on extension"""
    ext = Path(image_path).suffix.lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff',
    }
    return mime_types.get(ext, 'image/jpeg')  # Default to jpeg


def _encode_image_to_base64(image_path: str) -> str:
    """Encode image file to base64 string"""
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string
    except Exception as e:
        logger.error(f"Failed to encode image {image_path}: {e}")
        return ""


async def _download_image(session: aiohttp.ClientSession, url: str, save_dir: Path, idx: int) -> Optional[str]:
    """下载外网图片到本地"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                # 从URL解析文件扩展名
                parsed_url = urllib.parse.urlparse(url)
                ext = Path(parsed_url.path).suffix.lower() or '.jpg'
                if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif']:
                    ext = '.jpg'
                
                filename = f"image_{idx}{ext}"
                save_path = save_dir / filename
                
                content = await response.read()
                with open(save_path, 'wb') as f:
                    f.write(content)
                
                logger.debug(f"Downloaded image: {url} -> {save_path}")
                return str(save_path.resolve())
    except Exception as e:
        logger.warning(f"Failed to download image {url}: {e}")
    return None


async def _download_images_from_md(md_content: str, save_dir: Path) -> Dict[str, str]:
    """从MD内容中提取外网图片URL并下载到本地，返回URL到本地路径的映射"""
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # 匹配Markdown图片语法中的URL (http/https)
    pattern = r'!\[.*?\]\((https?://[^\s\)]+\.(?:jpg|jpeg|png|gif|bmp|webp|tiff|tif)[^\)]*)\)'
    matches = list(re.finditer(pattern, md_content, re.IGNORECASE))
    
    if not matches:
        logger.info("No external images found in markdown")
        return {}
    
    logger.info(f"Found {len(matches)} external images to download")
    url_to_local = {}
    unique_urls = []
    
    # 收集唯一URL
    for match in matches:
        url = match.group(1)
        if url not in url_to_local and url not in unique_urls:
            unique_urls.append(url)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for idx, url in enumerate(unique_urls):
            tasks.append(_download_image(session, url, save_dir, idx))
        
        results = await asyncio.gather(*tasks)
        for url, local_path in zip(unique_urls, results):
            if local_path:
                url_to_local[url] = local_path
    
    logger.info(f"Successfully downloaded {len(url_to_local)} images")
    return url_to_local


def _create_content_list_from_md(md_content: str, url_to_local: Dict[str, str], md_base_path: str) -> List[Dict]:
    """从MD内容创建content_list，将图片引用替换为本地路径"""
    content_list = []
    page_idx = 0
    
    # 匹配所有图片语法（包括外网和本地）
    pattern = r'!\[.*?\]\((.*?\.(?:jpg|jpeg|png|gif|bmp|webp|tiff|tif)[^\)]*)\)'
    
    last_pos = 0
    for match in re.finditer(pattern, md_content, re.IGNORECASE):
        # 添加图像前的文本
        if match.start() > last_pos:
            text_content = md_content[last_pos:match.start()].strip()
            if text_content:
                content_list.append({
                    "type": "text",
                    "text": text_content,
                    "page_idx": page_idx
                })
        
        # 处理图像路径
        img_path = match.group(1).strip()
        
        # 优先使用已下载的外网图片
        if img_path in url_to_local:
            local_path = url_to_local[img_path]
        elif img_path.startswith(('http://', 'https://')):
            # 外网图片但下载失败，跳过
            logger.warning(f"Skipping undownloaded image: {img_path}")
            last_pos = match.end()
            continue
        else:
            # 本地相对路径
            if not Path(img_path).is_absolute():
                local_path = str((Path(md_base_path) / img_path).resolve())
            else:
                local_path = img_path
        
        # 检查文件是否存在
        if Path(local_path).exists():
            content_list.append({
                "type": "image",
                "img_path": local_path,
                "page_idx": page_idx
            })
            page_idx += 1
        else:
            logger.warning(f"Image not found: {local_path}")
        
        last_pos = match.end()
    
    # 添加剩余文本
    if last_pos < len(md_content):
        remaining_text = md_content[last_pos:].strip()
        if remaining_text:
            content_list.append({
                "type": "text",
                "text": remaining_text,
                "page_idx": page_idx
            })
    
    return content_list


def _replace_images_with_base64(markdown_content: str, url_to_local: Dict[str, str],) -> Tuple[List, int]:
    """
    将 markdown 中的图像引用替换为 base64 编码图像，保持位置
    
    Args:
        markdown_content: Markdown text content
        url_to_local: images_base_map
    """
    content_parts = []
    last_pos = 0
    image_count = 0
    
    # Match both markdown image syntax and MinerU format
    # Pattern captures the full match and the image path
    pattern = r'(!\[.*?\]\((.*?\.(?:jpg|jpeg|png|gif|bmp|webp|tiff|tif))\)|Image Path:\s*([^\r\n]*?\.(?:jpg|jpeg|png|gif|bmp|webp|tiff|tif)))'
    
    for match in re.finditer(pattern, markdown_content, re.IGNORECASE | re.DOTALL):
        # Add text before this image
        if match.start() > last_pos:
            text_part = markdown_content[last_pos:match.start()]
            if text_part.strip():
                content_parts.append({
                    "type": "text",
                    "text": text_part
                })
        
        # Extract image path (from either group 2 or 3)
        image_path = match.group(2) if match.group(2) else match.group(3)
        image_path = image_path.strip()
        
        # Handle relative paths
        # if not Path(image_path).is_absolute():
        #     image_path = str(Path(markdown_base_path) / image_path)

        local_image_path = url_to_local.get(image_path, image_path)
        
        # Try to encode image
        if Path(local_image_path).exists():
            base64_str = _encode_image_to_base64(local_image_path)
            if base64_str:
                mime_type = _get_image_mime_type(local_image_path)
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_str}"
                    }
                })
                image_count += 1
                logger.debug(f"Embedded image at position {match.start()}: {local_image_path}")
            else:
                # If encoding fails, keep original text
                content_parts.append({
                    "type": "text",
                    "text": match.group(0)
                })
        else:
            logger.warning(f"Image not found: {local_image_path}")
            # Keep original text reference
            content_parts.append({
                "type": "text",
                "text": match.group(0)
            })
        
        last_pos = match.end()
    
    # Add remaining text after last image
    if last_pos < len(markdown_content):
        remaining_text = markdown_content[last_pos:]
        if remaining_text.strip():
            content_parts.append({
                "type": "text",
                "text": remaining_text
            })
    
    return content_parts, image_count


async def _run_fast_queries_by_category(
    client,
    markdown_content: str,
    markdown_paths: List[str],
    queries_by_category: Dict[str, List[str]],
    url_to_local: Dict[str, str],
    model: str = "gpt-4o",
    max_concurrency: int = 10,
) -> Dict[str, List[Dict]]:
    """
    Fast mode: Direct GPT-4o queries with markdown content and images in original positions
    
    Args:
        client: OpenAI client
        markdown_content: Complete markdown text
        markdown_paths: List of markdown file paths
        queries_by_category: Queries organized by category
        model: Model to use
        max_concurrency: Max concurrent queries
    """
    # Process all markdown files and embed images at original positions
    logger.info("Processing markdown files and embedding images...")
    
    all_content_parts = []
    total_images = 0
    
    for md_path in markdown_paths:
        md_filename_without_ext = Path(md_path).stem

        # Add document separator if multiple files
        if len(markdown_paths) > 1:
            all_content_parts.append({
                "type": "text",
                "text": f"\n\n=== {Path(md_path).name} ===\n\n"
            })

        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace images with base64 at original positions
        content_parts, img_count = _replace_images_with_base64(content, url_to_local)
        all_content_parts.extend(content_parts)
        total_images += img_count

        logger.info(f"  {Path(md_path).name}: embedded {img_count} images")

    logger.info(f"Total embedded images: {total_images}")
    
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def query_one(category: str, idx: int, query: str):
        async with semaphore:
            try:
                system_prompt = "You are an expert at analyzing academic papers. Answer based on the provided content."
                
                # Build message content
                messages = [
                    {"role": "system", "content": system_prompt}
                ]
                
                # Build user message: document first, then query at the end
                user_content = [
                    {
                        "type": "text",
                        "text": "# Document Content\n\n"
                    }
                ]
                
                # Add all content parts (text and images in original order)
                user_content.extend(all_content_parts)
                
                # Add query at the end
                user_content.append({
                    "type": "text",
                    "text": f"""

# Question

{query}

Please provide a detailed answer based on the content and images above."""
                })
                
                messages.append({
                    "role": "user",
                    "content": user_content
                })
                
                # Call OpenAI API
                response = await asyncio.to_thread(
                    lambda: client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.3,
                    )
                )
                
                answer = response.choices[0].message.content
                
                return (category, idx, {
                    "query": query,
                    "answer": answer,
                    "mode": "fast_direct_with_vision",
                    "success": True,
                })
            except Exception as e:
                logger.error(f"Query failed: {query[:50]}... Error: {e}")
                return (category, idx, {
                    "query": query,
                    "answer": None,
                    "mode": "fast_direct_with_vision",
                    "success": False,
                    "error": str(e),
                })
    
    # Create all tasks
    tasks = []
    for category, queries in queries_by_category.items():
        for idx, query in enumerate(queries):
            tasks.append(query_one(category, idx, query))
    
    # Execute concurrently
    all_results = await asyncio.gather(*tasks)
    
    # Group by category
    results_by_category = {cat: [] for cat in queries_by_category.keys()}
    for category, idx, result in all_results:
        results_by_category[category].append((idx, result))
    
    # Restore order
    for category in results_by_category:
        results_by_category[category].sort(key=lambda x: x[0])
        results_by_category[category] = [r for _, r in results_by_category[category]]
    
    return results_by_category


async def run_rag_stage(base_dir: Path, config: Dict) -> Dict:
    """Stage 1: Index document and run RAG queries.
    
    Args:
        base_dir: Base directory for this document/project
        config: Pipeline configuration with input_path (file or directory)
    
    Note:
        RAGClient handles both single files and directories automatically.
        Multiple files will share the same RAG storage for unified content extraction.
    """
    # Get input path from config
    input_path = config.get("input_path")
    if not input_path:
        raise ValueError("Missing input_path in config")
    
    content_type = config.get("content_type", "paper")
    fast_mode = config.get("fast_mode", True)
    path = Path(input_path)
    
    # Determine storage directory
    output_dir = base_dir / "rag_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ========== FAST MODE: Parse only, no indexing ==========
    if fast_mode:
        logger.info("Running in FAST mode (parse only, no indexing)")

        from paper2slides.rag import RAG_PAPER_QUERIES

        # Check PARSER_ENABLED to determine parsing method
        parser_enabled = os.getenv("PARSER_ENABLED", "true").lower() == "true"
        is_md_file = path.is_file() and path.suffix.lower() == '.md'

        if not parser_enabled and is_md_file:
            # ===== PARSER DISABLED: Skip MinerU, process MD file directly =====
            logger.info(f"PARSER_ENABLED=False, processing MD file directly: {path.name}")

            # Read MD content
            with open(path, 'r', encoding='utf-8') as f:
                md_content = f.read()

            # Download external images
            images_dir = output_dir / "downloaded_images"
            url_to_local = await _download_images_from_md(md_content, images_dir)

            # Build content_list (for potential future use)
            insert_content_list = _create_content_list_from_md(
                md_content,
                url_to_local,
                str(path.parent)
            )
            logger.info(f"  Built content_list with {len(insert_content_list)} items")

            # Use original MD path
            markdown_paths = [str(path)]
            logger.info(f"  Found {len(markdown_paths)} markdown file(s)")
        else:
            # ===== PARSER ENABLED: Use MinerU BatchParser =====
            from paper2slides.raganything.batch_parser import BatchParser

            # Parse documents to generate markdown
            batch_parser = BatchParser(
                parser_type="mineru",
                max_workers=4,
                show_progress=True,
                skip_installation_check=True,
            )

            if path.is_file():
                logger.info(f"Parsing file: {path.name}")
            else:
                logger.info(f"Parsing directory: {path.name}")

            parse_result = batch_parser.process_batch(
                file_paths=[input_path],
                output_dir=str(output_dir),
                parse_method="auto",
                recursive=True,
            )

            logger.info(f"  Parsing completed: {len(parse_result.successful_files)} successful")

            # Collect markdown files
            md_files = list(output_dir.rglob("*.md"))
            markdown_paths = [str(f) for f in md_files]

            if not markdown_paths:
                raise ValueError("No markdown files generated")

            logger.info(f"  Found {len(markdown_paths)} markdown file(s)")
        
        # Use OpenAI to query markdown content directly
        logger.info("")
        logger.info(f"Running queries with GPT-4o and images ({content_type})...")
        
        from openai import OpenAI

        api_key = os.getenv("RAG_LLM_API_KEY", "")
        base_url = os.getenv("RAG_LLM_BASE_URL")
        model = os.getenv("LLM_MODEL")
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        # Execute queries (direct GPT-4o with images in original positions)
        if content_type == "paper":
            rag_results = await _run_fast_queries_by_category(
                client=client,
                markdown_content="",  # Not used anymore, content is processed inside
                markdown_paths=markdown_paths,
                queries_by_category=RAG_PAPER_QUERIES,
                model=model,
                url_to_local=url_to_local
            )
        else:
            raise ValueError("Fast mode currently only supports content_type='paper'")
        
        total = sum(len(r) for r in rag_results.values())
        logger.info(f"  Completed {total} queries")

    # ========== NORMAL MODE: Full RAG pipeline ==========
    else:
        from paper2slides.rag import RAGClient, RAG_PAPER_QUERIES, RAG_QUERY_MODES
        from paper2slides.rag.query import get_general_overview, generate_general_queries
        from paper2slides.rag.config import RAGConfig
        
        storage_dir = base_dir / "rag_storage"
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Create RAGClient with unified storage
        rag_config = RAGConfig.with_paths(
            storage_dir=str(storage_dir),
            output_dir=str(output_dir)
        )
        
        # Check PARSER_ENABLED to determine indexing method
        parser_enabled = os.getenv("PARSER_ENABLED", "true").lower() == "true"
        
        async with RAGClient(config=rag_config) as rag:
            # Check if input is a pre-parsed MD file and parser is disabled
            is_md_file = path.is_file() and path.suffix.lower() == '.md'
            
            if not parser_enabled and is_md_file:
                # ===== PARSER DISABLED: Skip MinerU, manually build content_list =====
                logger.info(f"PARSER_ENABLED=False, processing MD file directly: {path.name}")
                
                # Read MD content
                with open(path, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                # Download external images
                images_dir = output_dir / "downloaded_images"
                url_to_local = await _download_images_from_md(md_content, images_dir)
                
                # Build content_list
                content_list = _create_content_list_from_md(
                    md_content, 
                    url_to_local, 
                    str(path.parent)
                )
                logger.info(f"  Built content_list with {len(content_list)} items")
                
                # Insert content_list directly (skip MinerU parsing)
                processor = rag._get_rag()
                await processor.insert_content_list(
                    content_list=content_list,
                    file_path=str(path),
                    display_stats=True
                )
                logger.info(f"  Content list inserted, indexing complete")
                
                # Use original MD path
                markdown_paths = [str(path)]
            else:
                # ===== PARSER ENABLED: Original logic with MinerU =====
                if path.is_file():
                    logger.info(f"Indexing file: {path.name}")
                else:
                    logger.info(f"Indexing directory: {path.name}")
                
                batch_result = await rag.index_batch(
                    file_paths=[input_path],
                    output_dir=str(output_dir),
                    recursive=True,
                    show_progress=True
                )
                
                logger.info(f"  Indexing completed: {batch_result.get('successful_rag_files', 0)} successful, {batch_result.get('failed_rag_files', 0)} failed")
                
                # Collect markdown paths from parser outputs
                md_files = list(output_dir.rglob("*.md"))
                markdown_paths = [str(f) for f in md_files]
            
            if markdown_paths:
                logger.info(f"  Found {len(markdown_paths)} markdown file(s)")
            
            logger.info("")
            logger.info(f"Running RAG queries ({content_type})...")
            
            if content_type == "paper":
                rag_results = await rag.batch_query_by_category(
                    queries_by_category=RAG_PAPER_QUERIES,
                    modes_by_category=RAG_QUERY_MODES,
                )
            else:
                logger.info("  Getting document overview...")
                overview = await get_general_overview(rag, mode="mix")
                logger.info("  Generating queries from overview...")
                queries = generate_general_queries(rag, overview, count=12)
                logger.info(f"  Executing {len(queries)} queries...")
                query_results = await rag.batch_query(queries, mode="mix")
                rag_results = {"content": query_results}
            
            total = sum(len(r) for r in rag_results.values())
            logger.info(f"  Completed {total} queries")
    
    # Save result to mode-specific directory
    result = {
        "rag_results": rag_results,
        "markdown_paths": markdown_paths,
        "input_path": input_path,
        "content_type": content_type,
        "mode": "fast" if fast_mode else "normal",
    }
    
    # Ensure mode directory exists
    checkpoint_path = get_rag_checkpoint(base_dir, config)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    
    save_json(checkpoint_path, result)
    logger.info(f"  Saved: {checkpoint_path}")
    return result
