"""
Image Generator

Generate poster/slides images from ContentPlan.
"""
import os
import json
import base64
import time
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import requests
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import GenerationInput
from .content_planner import ContentPlan, Section
from ..prompts.image_generation import (
    STYLE_PROCESS_PROMPT,
    FORMAT_POSTER,
    FORMAT_SLIDE,
    POSTER_STYLE_HINTS,
    SLIDE_STYLE_HINTS,
    SLIDE_LAYOUTS_ACADEMIC,
    SLIDE_LAYOUTS_DORAEMON,
    SLIDE_LAYOUTS_DEFAULT,
    SLIDE_COMMON_STYLE_RULES,
    POSTER_COMMON_STYLE_RULES,
    VISUALIZATION_HINTS,
    CONSISTENCY_HINT,
    SLIDE_FIGURE_HINT,
    POSTER_FIGURE_HINT,
)


@dataclass
class GeneratedImage:
    """Generated image result."""
    section_id: str
    image_data: bytes
    mime_type: str


@dataclass
class ProcessedStyle:
    """Processed custom style from LLM."""
    style_name: str       # e.g., "Cyberpunk sci-fi style with high-tech aesthetic"
    color_tone: str       # e.g., "dark background with neon accents"
    special_elements: str # e.g., "Characters appear as guides" or ""
    decorations: str      # e.g., "subtle grid pattern" or ""
    valid: bool
    error: Optional[str] = None


def process_custom_style(client: OpenAI, user_style: str, model: str = None) -> ProcessedStyle:
    """Process user's custom style request with LLM."""
    model = model or os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": STYLE_PROCESS_PROMPT.format(user_style=user_style)}],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Received empty content from OpenAI API")
        result = json.loads(content)
        return ProcessedStyle(
            style_name=result.get("style_name", ""),
            color_tone=result.get("color_tone", ""),
            special_elements=result.get("special_elements", ""),
            decorations=result.get("decorations", ""),
            valid=result.get("valid", False),
            error=result.get("error"),
        )
    except Exception as e:
        return ProcessedStyle(style_name="", color_tone="", special_elements="", decorations="", valid=False, error=str(e))


class ImageGenerator:
    """Generate poster/slides images from ContentPlan."""
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        response_mime_type: Optional[str] = None,
        google_api_base_url: Optional[str] = None,
    ):
        self.provider = (provider or os.getenv("IMAGE_GEN_PROVIDER", "openrouter")).lower()
        self.api_key = api_key or os.getenv("IMAGE_GEN_API_KEY", "")
        self.base_url = base_url or os.getenv("IMAGE_GEN_BASE_URL", "https://openrouter.ai/api/v1")
        self.google_api_base_url = (google_api_base_url or os.getenv("GOOGLE_GENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")).rstrip("/")
        self.response_mime_type = response_mime_type or os.getenv("IMAGE_GEN_RESPONSE_MIME_TYPE", "text/plain")
        self.model = model or os.getenv("IMAGE_GEN_MODEL")
        
        if not self.model:
            if self.provider == "google":
                # Official Gemini API image-capable default
                self.model = "models/gemini-1.5-flash"
            elif self.provider == "dmxapi":
                self.model = "nano-banana-2"
            elif self.provider == "doubao":
                self.model = "doubao-seedream-4-5-251128"
            else:
                self.model = "google/gemini-3-pro-image-preview"
        
        if self.provider in ("openrouter", "doubao"):
            # doubao uses OpenAI SDK with custom base_url
            if self.provider == "doubao" and not base_url:
                self.base_url = "https://ark.cn-beijing.volces.com/api/v3"
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        elif self.provider in ("google", "dmxapi"):
            self.client = None
        else:
            raise ValueError(f"Unsupported image generation provider: {self.provider}")
    
    def generate(
        self,
        plan: ContentPlan,
        gen_input: GenerationInput,
        max_workers: int = 1,
        save_callback = None,
    ) -> List[GeneratedImage]:
        """
        Generate images from ContentPlan.
        
        Args:
            plan: ContentPlan from ContentPlanner
            gen_input: GenerationInput with config and origin
            max_workers: Maximum parallel workers for slides (3rd+ slides run in parallel)
            save_callback: Optional callback function(generated_image, index, total) called after each image
        
        Returns:
            List of GeneratedImage (1 for poster, N for slides)
        """
        figure_images = self._load_figure_images(plan, gen_input.origin.base_path)
        style_name = gen_input.config.style.value
        custom_style = gen_input.config.custom_style
        
        # Process custom style with LLM if needed
        processed_style = None
        if style_name == "custom" and custom_style:
            processed_style = process_custom_style(self.client, custom_style)
            if not processed_style.valid:
                raise ValueError(f"Invalid custom style: {processed_style.error}")
        
        all_sections_md = self._format_sections_markdown(plan)
        all_images = self._filter_images(plan.sections, figure_images)
        
        if plan.output_type == "poster":
            result = self._generate_poster(style_name, processed_style, all_sections_md, all_images)
            if save_callback and result:
                save_callback(result[0], 0, 1)
            return result
        else:
            return self._generate_slides(plan, style_name, processed_style, all_sections_md, figure_images, max_workers, save_callback)
    
    def _generate_poster(self, style_name, processed_style: Optional[ProcessedStyle], sections_md, images) -> List[GeneratedImage]:
        """Generate 1 poster image."""
        prompt = self._build_poster_prompt(
            format_prefix=FORMAT_POSTER,
            style_name=style_name,
            processed_style=processed_style,
            sections_md=sections_md,
        )
        
        image_data, mime_type = self._call_model(prompt, images)
        return [GeneratedImage(section_id="poster", image_data=image_data, mime_type=mime_type)]
    
    def _generate_slides(self, plan, style_name, processed_style: Optional[ProcessedStyle], all_sections_md, figure_images, max_workers: int, save_callback=None) -> List[GeneratedImage]:
        """Generate N slide images (slides 1-2 sequential, 3+ parallel)."""
        results = []
        total = len(plan.sections)
        
        # Select layout rules based on style
        if style_name == "custom":
            layouts = SLIDE_LAYOUTS_DEFAULT
        elif style_name == "doraemon":
            layouts = SLIDE_LAYOUTS_DORAEMON
        else:
            layouts = SLIDE_LAYOUTS_ACADEMIC
        
        style_ref_image = None  # Store 2nd slide as reference for all subsequent slides
        
        # Generate first 2 slides sequentially (slide 1: no ref, slide 2: becomes ref)
        for i in range(min(2, total)):
            section = plan.sections[i]
            section_md = self._format_single_section_markdown(section, plan)
            layout_rule = layouts.get(section.section_type, layouts["content"])
            
            prompt = self._build_slide_prompt(
                style_name=style_name,
                processed_style=processed_style,
                sections_md=section_md,
                layout_rule=layout_rule,
                slide_info=f"Slide {i+1} of {total}",
                context_md=all_sections_md,
            )
            
            section_images = self._filter_images([section], figure_images)
            reference_images = []
            if style_ref_image:
                reference_images.append(style_ref_image)
            reference_images.extend(section_images)
            
            image_data, mime_type = self._call_model(prompt, reference_images)
            
            # Save 2nd slide (i=1) as style reference
            if i == 1:
                style_ref_image = {
                    "figure_id": "Reference Slide",
                    "caption": "STRICTLY MAINTAIN: same background color, same accent color, same font style, same chart/icon style. Keep visual consistency.",
                    "base64": base64.b64encode(image_data).decode("utf-8"),
                    "mime_type": mime_type,
                }
            
            generated_img = GeneratedImage(section_id=section.id, image_data=image_data, mime_type=mime_type)
            results.append(generated_img)
            
            # Save immediately if callback provided
            if save_callback:
                save_callback(generated_img, i, total)
        
        # Generate remaining slides in parallel (from 3rd onwards)
        if total > 2:
            results_dict = {}
            
            def generate_single(i, section):
                section_md = self._format_single_section_markdown(section, plan)
                layout_rule = layouts.get(section.section_type, layouts["content"])
                
                prompt = self._build_slide_prompt(
                    style_name=style_name,
                    processed_style=processed_style,
                    sections_md=section_md,
                    layout_rule=layout_rule,
                    slide_info=f"Slide {i+1} of {total}",
                    context_md=all_sections_md,
                )
                
                section_images = self._filter_images([section], figure_images)
                reference_images = [style_ref_image] if style_ref_image else []
                reference_images.extend(section_images)
                
                image_data, mime_type = self._call_model(prompt, reference_images)
                return i, GeneratedImage(section_id=section.id, image_data=image_data, mime_type=mime_type)
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(generate_single, i, plan.sections[i]): i
                    for i in range(2, total)
                }
                
                for future in as_completed(futures):
                    idx, generated_img = future.result()
                    results_dict[idx] = generated_img
                    
                    # Save immediately if callback provided
                    if save_callback:
                        save_callback(generated_img, idx, total)
            
            # Append in order
            for i in range(2, total):
                results.append(results_dict[i])
        
        return results
    
    def _format_custom_style_for_poster(self, ps: ProcessedStyle) -> str:
        """Format ProcessedStyle into style hints string for poster."""
        parts = [
            ps.style_name + ".",
            "English text only.",
            "Use ROUNDED sans-serif fonts for ALL text.",
            "Characters should react to or interact with the content, with appropriate poses/actions and sizes - not just decoration."
            f"LIMITED COLOR PALETTE (3-4 colors max): {ps.color_tone}.",
            POSTER_COMMON_STYLE_RULES,
        ]
        if ps.special_elements:
            parts.append(ps.special_elements + ".")
        return " ".join(parts)
    
    def _format_custom_style_for_slide(self, ps: ProcessedStyle) -> str:
        """Format ProcessedStyle into style hints string for slide."""
        parts = [
            ps.style_name + ".",
            "English text only.",
            "Use ROUNDED sans-serif fonts for ALL text.",
            "Characters should react to or interact with the content, with appropriate poses/actions and sizes - not just decoration.",
            f"LIMITED COLOR PALETTE (3-4 colors max): {ps.color_tone}.",
            SLIDE_COMMON_STYLE_RULES,
        ]
        if ps.special_elements:
            parts.append(ps.special_elements + ".")
        return " ".join(parts)
    
    def _build_poster_prompt(self, format_prefix, style_name, processed_style: Optional[ProcessedStyle], sections_md) -> str:
        """Build prompt for poster."""
        parts = [format_prefix]
        
        if style_name == "custom" and processed_style:
            parts.append(f"Style: {self._format_custom_style_for_poster(processed_style)}")
            if processed_style.decorations:
                parts.append(f"Decorations: {processed_style.decorations}")
        else:
            parts.append(POSTER_STYLE_HINTS.get(style_name, POSTER_STYLE_HINTS["academic"]))
            # print("Skip Build Default Prompt.")
        
        parts.append(VISUALIZATION_HINTS)
        parts.append(POSTER_FIGURE_HINT)
        # gang_prompt = """
        # 风格定义
        # [战略与调性] 一张 Swiss Style 的技术解构插图。旨在传达“绝对的理性、精密工程美学与秩序”。画面必须冷静、客观，像是一份封存的手绘档案。
        #
        # 空间与技法
        # 采用严格的正交视图 (Orthographic View)。 所有组件必须按照"隐形"网格系统严谨排列。风格为硬边矢量线稿，强调线条的几何准确性，线条粗细均等。
        #
        # 视觉渲染
        # [色彩与材质] 色彩系统：严格限制色盘。整体为黑白线稿。
        # - 主色：黑色线条 ( 000000)。
        # - 填充：主体材质区域填充“水墨黑”。
        # - 高亮：仅在核心功能部件使用单一高亮色： 朱砂红。
        # - 背景：复古绘图纸纹理，带有轻微的纸张颗粒噪点，纯净无杂物。
        #
        # 负向约束
        # 严禁照片级渲染，严禁复杂光影，严禁渐变色，严禁混乱背景，保持绝对的平面化与图表化。
        #
        # 核心变量
        # - 语言类型：仅限中文文本，文字部分仅使用10笔画以内的简单汉字，确保文字清晰可读，避免繁体字和生僻字。
        # - 绘制主体与内容：如下列Content所示
        # """
        # parts.append(gang_prompt)
        parts.append(f"---\nContent:\n{sections_md}")
        
        return "\n\n".join(parts)
    
    def _build_slide_prompt(self, style_name, processed_style: Optional[ProcessedStyle], sections_md, layout_rule, slide_info, context_md) -> str:
        """Build prompt for slide with layout rules and consistency."""
        parts = [FORMAT_SLIDE]
        
        if style_name == "custom" and processed_style:
            parts.append(f"Style: {self._format_custom_style_for_slide(processed_style)}")
        else:
            parts.append(SLIDE_STYLE_HINTS.get(style_name, SLIDE_STYLE_HINTS["academic"]))
        
        # Add layout rule, then decorations if custom style
        parts.append(layout_rule)
        if style_name == "custom" and processed_style and processed_style.decorations:
            parts.append(f"Decorations: {processed_style.decorations}")
        
        parts.append(VISUALIZATION_HINTS)
        parts.append(CONSISTENCY_HINT)
        parts.append(SLIDE_FIGURE_HINT)
        
        parts.append(slide_info)
        parts.append(f"---\nFull presentation context:\n{context_md}")
        parts.append(f"---\nThis slide content:\n{sections_md}")
        
        return "\n\n".join(parts)
    
    def _format_sections_markdown(self, plan: ContentPlan) -> str:
        """Format all sections as markdown."""
        parts = []
        for section in plan.sections:
            parts.append(self._format_single_section_markdown(section, plan))
        return "\n\n---\n\n".join(parts)
    
    def _format_single_section_markdown(self, section: Section, plan: ContentPlan) -> str:
        """Format a single section as markdown."""
        lines = [f"## {section.title}", "", section.content]
        
        for ref in section.tables:
            table = plan.tables_index.get(ref.table_id)
            if table:
                focus_str = f" (focus: {ref.focus})" if ref.focus else ""
                lines.append("")
                lines.append(f"**{ref.table_id}**{focus_str}:")
                lines.append(ref.extract if ref.extract else table.html_content)
        
        for ref in section.figures:
            fig = plan.figures_index.get(ref.figure_id)
            if fig:
                focus_str = f" (focus: {ref.focus})" if ref.focus else ""
                caption = f": {fig.caption}" if fig.caption else ""
                lines.append("")
                lines.append(f"**{ref.figure_id}**{focus_str}{caption}")
                lines.append("[Image attached]")
        
        return "\n".join(lines)
    
    def _load_figure_images(self, plan: ContentPlan, base_path: str) -> List[dict]:
        """Load figure images as base64."""
        images = []
        mime_map = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"
        }
        
        for fig_id, fig in plan.figures_index.items():
            if base_path:
                img_path = Path(base_path) / fig.image_path
            else:
                img_path = Path(fig.image_path)
            
            if not img_path.exists():
                continue
            
            mime_type = mime_map.get(img_path.suffix.lower(), "image/jpeg")
            
            try:
                with open(img_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode("utf-8")
                images.append({
                    "figure_id": fig_id,
                    "caption": fig.caption,
                    "base64": img_data,
                    "mime_type": mime_type,
                })
            except Exception:
                continue
        
        return images
    
    def _filter_images(self, sections: List[Section], figure_images: List[dict]) -> List[dict]:
        """Filter images used in given sections."""
        used_ids = set()
        for section in sections:
            for ref in section.figures:
                used_ids.add(ref.figure_id)
        return [img for img in figure_images if img.get("figure_id") in used_ids]
    
    def _call_model(self, prompt: str, reference_images: List[dict]) -> tuple:
        """Call image generation provider based on configuration."""
        if self.provider == "google":
            return self._call_model_google(prompt, reference_images)
        elif self.provider == "dmxapi":
            return self._call_model_dmxapi(prompt, reference_images)
        elif self.provider == "doubao":
            return self._call_model_doubao(prompt, reference_images)
        return self._call_model_openrouter(prompt, reference_images)
    
    def _call_model_openrouter(self, prompt: str, reference_images: List[dict]) -> tuple:
        """Call the image generation model with retry logic."""
        logger = logging.getLogger(__name__)
        content = [{"type": "text", "text": prompt}]
        
        # Add each image with figure_id and caption label
        for img in reference_images:
            if img.get("base64") and img.get("mime_type"):
                fig_id = img.get("figure_id", "Figure")
                caption = img.get("caption", "")
                label = f"[{fig_id}]: {caption}" if caption else f"[{fig_id}]"
                content.append({"type": "text", "text": label})
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{img['mime_type']};base64,{img['base64']}"}
                })
        
        # Retry logic for API calls
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Calling image generation API (attempt {attempt + 1}/{max_retries})...")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": content}],
                    extra_body={"modalities": ["image", "text"]}
                )
                
                # Check if response is valid
                if response is None:
                    error_msg = "API returned None response - possible rate limit or API error"
                    logger.warning(f"{error_msg} (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    raise RuntimeError(error_msg)
                
                if not hasattr(response, 'choices') or not response.choices:
                    error_msg = f"API response has no choices: {response}"
                    logger.warning(f"{error_msg} (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    raise RuntimeError(error_msg)
                
                message = response.choices[0].message
                if hasattr(message, 'images') and message.images:
                    image_url = message.images[0]['image_url']['url']
                    if image_url.startswith('data:'):
                        header, base64_data = image_url.split(',', 1)
                        mime_type = header.split(':')[1].split(';')[0]
                        logger.info("Image generation successful")
                        return base64.b64decode(base64_data), mime_type
                
                error_msg = "Image generation failed - no images in response"
                logger.warning(f"{error_msg} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError(error_msg)
                
            except Exception as e:
                logger.error(f"Error in API call (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise
        
        raise RuntimeError("Image generation failed after all retry attempts")
    
    def _call_model_dmxapi(self, prompt: str, reference_images: List[dict]) -> tuple:
        """Call DMXAPI for image generation (nano-banana-2 model).
        
        Note: DMXAPI's /v1/images/generations endpoint does not support direct image input.
        Reference images' metadata (figure_id, caption) are incorporated into the prompt
        to preserve context information.
        """
        # print(f"Prompt ================> {prompt}")
        # exit()

        logger = logging.getLogger(__name__)
        max_retries = 3
        retry_delay = 2
        
        # DMXAPI endpoint
        api_url = self.base_url if self.base_url and "dmxapi" in self.base_url else "https://www.dmxapi.cn/v1/images/generations"
        
        # Build enhanced prompt with reference image descriptions
        # This preserves context from reference_images even though DMXAPI doesn't accept image input
        enhanced_prompt_parts = [prompt]
        
        if reference_images:
            ref_descriptions = []
            for img in reference_images:
                fig_id = img.get("figure_id", "Figure")
                caption = img.get("caption", "")
                if caption:
                    ref_descriptions.append(f"[{fig_id}]: {caption}")
                else:
                    ref_descriptions.append(f"[{fig_id}]")
            
            if ref_descriptions:
                enhanced_prompt_parts.append("\n\nReference context:")
                enhanced_prompt_parts.extend(ref_descriptions)
                logger.info(f"  Including {len(ref_descriptions)} reference image descriptions in prompt")

        enhanced_prompt_parts.append("所有文字使用清晰易读的字体，确保所有中文字体印刷级清晰。")

        final_prompt = "\n".join(enhanced_prompt_parts)

        # Build payload according to DMXAPI format
        payload = {
            "prompt": final_prompt,
            "n": 1,
            "model": self.model,
            "aspect_ratio": os.environ.get("IMAGE_RESOLUTION", "16:9"),  # 1376x768 resolution
            "size": os.environ.get("IMAGE_SIZE", "2K"),
            "response_format": "b64_json",  # Get base64 directly for consistency with other providers
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Calling DMXAPI image generation (attempt {attempt + 1}/{max_retries})...")
                logger.info(f"  Model: {self.model}, Aspect: {os.environ.get('IMAGE_RESOLUTION', '16:9')}, Size: {os.environ.get('IMAGE_SIZE', '2K')}")
                logger.info(f"  Prompt length: {len(final_prompt)} chars")
                
                response = requests.post(
                    api_url,
                    json=payload,
                    headers=headers,
                    timeout=600,  # Image generation can take time
                )
                
                if response.status_code >= 400:
                    logger.warning(f"DMXAPI error {response.status_code}: {response.text[:300]}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    response.raise_for_status()
                
                result = response.json()
                
                # Check for data in response
                if 'data' not in result or len(result['data']) == 0:
                    error_msg = f"DMXAPI response has no data: {result}"
                    logger.warning(f"{error_msg} (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    raise RuntimeError(error_msg)
                
                image_data = result['data'][0]
                
                # Format A: Base64 encoded image (preferred, matches other providers' return format)
                if 'b64_json' in image_data:
                    base64_data = image_data['b64_json']
                    image_bytes = base64.b64decode(base64_data)
                    logger.info(f"Image generation successful (DMXAPI, base64, {len(image_bytes)} bytes)")
                    return image_bytes, "image/png"
                
                # Format B: URL (need to download)
                elif 'url' in image_data:
                    image_url = image_data['url']
                    logger.info(f"Downloading image from URL: {image_url[:80]}...")
                    img_response = requests.get(image_url, timeout=60)
                    img_response.raise_for_status()
                    logger.info(f"Image generation successful (DMXAPI, URL, {len(img_response.content)} bytes)")
                    return img_response.content, "image/png"
                
                error_msg = "DMXAPI response has no image data (b64_json or url)"
                logger.warning(f"{error_msg} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError(error_msg)
                
            except Exception as e:
                logger.error(f"Error in DMXAPI call (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise
        
        raise RuntimeError("Image generation failed after all retry attempts")
    
    def _call_model_doubao(self, prompt: str, reference_images: List[dict]) -> tuple:
        """Call Doubao (豆包) image generation API via OpenAI SDK.
        
        Uses the images.generate endpoint with doubao-seedream model.
        Reference images' metadata are incorporated into the prompt.
        """
        logger = logging.getLogger(__name__)
        max_retries = 3
        retry_delay = 2
        
        # Build enhanced prompt with reference image descriptions
        # Add Chinese language instruction at the beginning
        language_hint = "【重要】生成的图片中所有文字内容必须使用简体中文！"
        enhanced_prompt_parts = [language_hint, prompt]
        
        if reference_images:
            ref_descriptions = []
            for img in reference_images:
                fig_id = img.get("figure_id", "Figure")
                caption = img.get("caption", "")
                if caption:
                    ref_descriptions.append(f"[{fig_id}]: {caption}")
                else:
                    ref_descriptions.append(f"[{fig_id}]")
            
            if ref_descriptions:
                enhanced_prompt_parts.append("\n\nReference context:")
                enhanced_prompt_parts.extend(ref_descriptions)
                logger.info(f"  Including {len(ref_descriptions)} reference image descriptions in prompt")

        enhanced_prompt_parts.append("生成图片中所有文字使用清晰易读的字体，确保所有中文字体印刷级清晰。")
        final_prompt = "\n".join(enhanced_prompt_parts)

        # logger.info(f"Prompt============================>{final_prompt}...")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Calling Doubao image generation (attempt {attempt + 1}/{max_retries})...")
                logger.info(f"  Model: {self.model}, Size: {os.environ.get('IMAGE_SIZE', '2K')}")
                logger.info(f"  Prompt length: {len(final_prompt)} chars")
                
                # Use OpenAI SDK's images.generate endpoint
                response = self.client.images.generate(
                    model=self.model,
                    prompt=final_prompt,
                    size=os.environ.get("IMAGE_SIZE", "2K"),  # Doubao supports: 1K, 2K
                    response_format="url",
                    extra_body={
                        "watermark": False,  # Disable watermark for production use
                    },
                )
                
                if not response or not response.data:
                    error_msg = "Doubao API response has no data"
                    logger.warning(f"{error_msg} (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    raise RuntimeError(error_msg)
                
                image_data = response.data[0]
                
                # Format: URL (need to download)
                if hasattr(image_data, 'url') and image_data.url:
                    image_url = image_data.url
                    logger.info(f"Downloading image from URL: {image_url[:80]}...")
                    img_response = requests.get(image_url, timeout=60)
                    img_response.raise_for_status()
                    logger.info(f"Image generation successful (Doubao, URL, {len(img_response.content)} bytes)")
                    return img_response.content, "image/png"
                
                # Format: Base64
                if hasattr(image_data, 'b64_json') and image_data.b64_json:
                    image_bytes = base64.b64decode(image_data.b64_json)
                    logger.info(f"Image generation successful (Doubao, base64, {len(image_bytes)} bytes)")
                    return image_bytes, "image/png"
                
                error_msg = "Doubao response has no image data (url or b64_json)"
                logger.warning(f"{error_msg} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError(error_msg)
                
            except Exception as e:
                logger.error(f"Error in Doubao API call (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise
        
        raise RuntimeError("Image generation failed after all retry attempts")
    
    def _call_model_google(self, prompt: str, reference_images: List[dict]) -> tuple:
        """Call the official Google Gemini API for image generation."""
        logger = logging.getLogger(__name__)
        max_retries = 3
        retry_delay = 2  # seconds

        model_name = self.model if self.model.startswith("models/") else f"models/{self.model}"
        url = f"{self.google_api_base_url}/{model_name}:generateContent"

        wants_image = self.response_mime_type.lower().startswith("image/")
        model_key = model_name.split("/", 1)[-1]
        image_capable_prefixes = (
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash-8b",
            "gemini-2.0-flash",
        )
        if wants_image and not model_key.startswith(image_capable_prefixes):
            raise ValueError(
                f"Model '{model_name}' does not support image responses with the Google Gemini API. "
                "Use an image-capable model such as 'models/gemini-1.5-flash' (or -8b/pro/2.0-flash) "
                "or change IMAGE_GEN_RESPONSE_MIME_TYPE to a text type."
            )

        # Compose prompt parts with optional inline reference images
        parts = [{"text": prompt}]
        for img in reference_images:
            if img.get("base64") and img.get("mime_type"):
                fig_id = img.get("figure_id", "Figure")
                caption = img.get("caption", "")
                label = f"[{fig_id}]: {caption}" if caption else f"[{fig_id}]"
                parts.append({"text": label})
                parts.append({
                    "inlineData": {
                        "mimeType": img["mime_type"],
                        "data": img["base64"],
                    }
                })

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": self.response_mime_type},
        }

        for attempt in range(max_retries):
            try:
                logger.info(f"Calling Google Gemini image API (attempt {attempt + 1}/{max_retries})...")
                response = requests.post(
                    url,
                    params={"key": self.api_key},
                    json=payload,
                    timeout=60,
                )

                if response.status_code >= 400:
                    logger.warning(f"Google API error {response.status_code}: {response.text[:200]}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    response.raise_for_status()

                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    error_msg = "Google API response has no candidates"
                    logger.warning(f"{error_msg} (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    raise RuntimeError(error_msg)

                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    inline = part.get("inlineData")
                    if inline and inline.get("data"):
                        mime_type = inline.get("mimeType") or self.response_mime_type
                        logger.info("Image generation successful (Google Gemini)")
                        return base64.b64decode(inline["data"]), mime_type

                    text_data = part.get("text")
                    if text_data:
                        try:
                            decoded = base64.b64decode(text_data, validate=True)
                            logger.info("Image generation successful (Google Gemini, text base64 payload)")
                            return decoded, self.response_mime_type
                        except Exception:
                            continue

                error_msg = "Image generation failed - no image payload in response"
                logger.warning(f"{error_msg} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError(error_msg)

            except Exception as e:
                logger.error(f"Error in Google API call (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise

        raise RuntimeError("Image generation failed after all retry attempts")


def save_images_as_pdf(images: List[GeneratedImage], output_path: str):
    """
    Save generated images as a single PDF file.
    
    Args:
        images: List of GeneratedImage from ImageGenerator.generate()
        output_path: Output PDF file path
    """
    from PIL import Image
    import io
    
    pdf_images = []
    
    for img in images:
        # Load image from bytes
        pil_img = Image.open(io.BytesIO(img.image_data))
        
        # Convert RGBA to RGB (PDF doesn't support alpha)
        if pil_img.mode == 'RGBA':
            pil_img = pil_img.convert('RGB')
        elif pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        
        pdf_images.append(pil_img)
    
    if pdf_images:
        # Save first image and append the rest
        pdf_images[0].save(
            output_path,
            save_all=True,
            append_images=pdf_images[1:] if len(pdf_images) > 1 else [],
            resolution=100.0,
        )
        print(f"PDF saved: {output_path}")
