"""
Prompts and style configurations for image generation
"""
from typing import Dict

# 用于处理自定义样式的提示模板
STYLE_PROCESS_PROMPT = """用户希望这种样式用于演示幻灯片：{user_style}

重要规则：
1. 默认使用 MORANDI 色彩调色板（柔和、柔和、低饱和度、灰色底色）和浅色背景，除非用户另有说明。
2. 保持简洁和干净——不要花哨或浮夸的元素。每一个视觉元素都必须有意义。
3. 色彩调色板有限（最多3-4种颜色）。

输出 JSON：
{{
    “style_name”：“风格名称及简短描述（例如，赛博朋克科幻风格兼具高科技美学）”
    “color_tone”：“色彩描述——偏好Morandi调色板配白色背景（例如浅奶油色背景配柔和鼠尾草绿和尘玫瑰点缀）”
    “special_elements”：“任何特殊的视觉元素，如角色、吉祥物、图案——必须是有意义的，而非随机装饰。”
    “decorations”：“背景/边框效果——保持简单干净（或空字符串）”
    “valid”：为真，
    “error”：空
}}

示例：
- “赛博朋克”：“{{”style_name“：”赛博朋克科幻风格兼高科技美学“，”color_tone“：”暗色背景配霓虹青和品红点缀“，”special_elements“：”“装饰”：“细腻网格图案，边框霓虹光芒”，“有效”：真实，“错误”：null}}
- “吉卜力工作室”：{{“style_name”：“吉卜力工作室动漫风格，带有异想天开的美学”，“color_tone”：“浅奶油色背景，柔和的莫兰迪水彩色调——柔和鼠尾草色、尘粉色、柔和灰蓝色”，“special_elements”：“龙猫或煤灰精灵可以作为友好的引导者出现——必须与内容相关”，“装饰”：“柔和的云朵或自然元素作为边界”，“有效”：真实，“错误”：无}}
- “极简主义”：“{{”style_name“：”干净极简风格“，”color_tone“：”浅暖灰色背景配Morandi调色板——炭笔文字，柔和金色点缀“，”special_elements“：”“，”装饰“：”“，”有效“：true，”错误“：null}}

如果不合适，设置valid=false并带有错误。"""


# 前缀格式
FORMAT_POSTER = "宽幅横向海报布局（16：9宽高比）。就一张海报。保持信息密度适中，留白以便阅读。"
FORMAT_SLIDE = "宽阔的横向幻灯片布局（16：9宽高比）。"

# 海报风格提示
POSTER_STYLE_HINTS: Dict[str, str] = {
    "academic": "学术会议海报风格，采用正式、严谨、学术的语调，偏重于研究报告，背景光线洁净。仅限中文文本，专业术语或缩写可保留英文作为辅助说明，但不能一张图全是英文，文字部分仅使用10笔画以内的简单汉字，确保文字清晰可读，避免繁体字和生僻字。使用专业、清晰的色调，搭配良好的对比度和学术字体。使用三列布局，展示故事进展。保留内容细节。顶部的标题部分可以用彩色背景条来突出。数据：保留原始科学数据——保持其准确性、风格和完整性。如有，请附上机构标志。信息需正规严谨，学术领域，面向科研人员和知识工作者等用户。",
    "academic_en": "学术会议海报风格，采用正式、严谨、学术的语调，偏重于研究报告，背景光线洁净。仅限英文文本，确保文字清晰可读，。使用专业、清晰的色调，搭配良好的对比度和学术字体。使用三列布局，展示故事进展。保留内容细节。顶部的标题部分可以用彩色背景条来突出。数据：保留原始科学数据——保持其准确性、风格和完整性。如有，请附上机构标志。信息需正规严谨，学术领域，面向科研人员和知识工作者等用户。",
    "doraemon": "经典的哆啦A梦动漫风格，明亮友好。仅限中文文本，专业术语或缩写可保留英文作为辅助说明，但不能一张图全是英文。使用温暖、优雅、柔和的色调。所有文本使用圆润无衬线字体（禁止艺术/华丽/装饰性字体）。大而易读的文字。使用三列布局，展示故事进展。每列可以有场景背景（例如，问题用云背景，方法用 clearing背景，结果用 sunny背景）。保持简单，不要太花哨。哆啦A梦角色只是向导（1-2个小人物），不是主要焦点。",
}

# 幻灯片风格提示
SLIDE_STYLE_HINTS: Dict[str, str] = {
    "academic": "专业标准学术风格，采用正式、严谨、学术的语调，偏重于研究报告。仅限中文文本，专业术语或缩写可保留英文作为辅助说明，但不能一张图全是英文，文字部分仅使用10笔画以内的简单汉字，确保文字清晰可读，避免繁体字和生僻字。所有文本都使用圆角无衬线字体。使用MORANDI色彩调色板（柔和、柔和、低饱和度的颜色），背景为白色。干净利落的线条。重要提示：人物和表格至关重要——重新绘制以符合视觉风格，使其与背景和色彩方案无缝融合。用图表（条形图、线条图、圆饼图、雷达图）可视化数据——重新绘制图表以匹配风格，使其大且有意义。布局应宽敞优雅——避免拥挤，留有呼吸空间。整体感觉：极简、学术、专业、精致，信息内容需正规严谨，学术领域，面向科研人员和知识工作者等用户。",
    "academic_en": "专业标准学术风格，采用正式、严谨、学术的语调，偏重于研究报告。仅限英文文本，确保文字清晰可读。所有文本都使用圆角无衬线字体。使用MORANDI色彩调色板（柔和、柔和、低饱和度的颜色），背景为白色。干净利落的线条。重要提示：人物和表格至关重要——重新绘制以符合视觉风格，使其与背景和色彩方案无缝融合。用图表（条形图、线条图、圆饼图、雷达图）可视化数据——重新绘制图表以匹配风格，使其大且有意义。布局应宽敞优雅——避免拥挤，留有呼吸空间。整体感觉：极简、学术、专业、精致，信息内容需正规严谨，学术领域，面向科研人员和知识工作者等用户。",
    "doraemon": "经典的哆啦A梦动漫风格，明亮友好。哆啦A梦风格，配以精致、精致的色彩搭配（不是孩子气的鲜艳色彩）。仅限中文文本，专业术语或缩写可保留英文作为辅助说明，但不能一张图全是英文。保留内容中的每一个细节。所有文本使用圆润无衬线字体（禁止艺术/华丽/装饰性字体）。项目符号标题应为加粗。色彩有限（最多3-4种颜色）：使用温暖、优雅、柔和的色调——成熟且雅致，贯穿所有幻灯片。如果幻灯片有图表：重点放在它们作为主要视觉内容，有帮助时放大。如果没有图表：为每个段落添加插图或图标，填满整页。桌子应该有纯边框（边框上不允许有图案或装饰）。用颜色突出关键数字。角色应该有意义地出现（而不是随意的装饰）——他们应该对内容做出反应或互动，并以合适的姿势/动作和体型。",
}

# 按样式和章节类型分类的幻灯片布局规则
SLIDE_LAYOUTS_ACADEMIC: Dict[str, str] = {
    "opening": """开场幻灯片布局：
- 标题：顶部中央大字体
- 作者/隶属：底部小字体
- 主视觉：中心上只有一个元素
- 背景：白色""",

    "content": """内容幻灯片布局：
- 标题：幻灯片左上角
- 内容：中等字体大小，布局宽敞
- 人物/桌面应与背景颜色和风格融合——精致且精致
- 用图表（条形图、线图、圆图图、雷达图）可视化数据——让图表大且有意义
- 所有图表/图形应使用统一风格（相同的点缀颜色，相同的线条粗细）
- IF 图形/表格出现：将它们作为主要视觉内容放大展示
- 为每个段落添加大型简线图标
- 背景：白色，与上一张幻灯片相同
- 整体感觉：极简、学术、专业、正式、研究""",

    "ending": """结尾幻灯片布局：
- 标题/标题：在滑梯顶部中心
- 主要内容：《CENTER》中的关键要点
- 背景：白色，与上一张幻灯片相同""",
}

SLIDE_LAYOUTS_DORAEMON: Dict[str, str] = {
    "opening": """开场幻灯片布局（精致的动漫风格，经典哆啦A梦风格）：
- 标题：顶部中央的大号简洁无衬线字体（无艺术/装饰性字体）
- 作者/隶属：底部中央小字体
- 主视觉：CENTER中的哆啦A梦角色，可以出现在暗示主题的场景/场景中
- 背景：可以使用SCENE插图作为边框（例如门口、窗户、风景）代替纯边框
- 颜色：精致、温暖、柔和的色调（非儿童化的鲜艳色彩）
- 整体感觉：成熟、优雅、精致""",

    "content": """内容幻灯片布局（精致动漫风格，经典哆啦A梦风格）：
- 标题：简洁无衬线字体，位于幻灯片左上角（禁止艺术/装饰性字体）
- 可选：上半部分可包含反映内容氛围/主题的宽幅场景插图
- 内容区：置于细长、素色、柔和的圆角边框内（边框上无图案/装饰）
- 背景：干净、温暖的色调（保持简洁和不杂乱）
- 色彩：精致、温暖、柔和的色调——贯穿所有幻灯片（非儿童化的鲜艳色彩）
- IF图形/表格：突出展示它们作为主要视觉内容
- 如果没有图表/图表：为每个段落添加插图或图标以填充空间
- 角色：应有意义地出现，配合情境合适的动作/姿势（非随机装饰），大小可根据重要性变化
- 保留所提供内容中的每一个细节
- 用丰富的视觉内容填充幻灯片，避免留空""",

    "ending": """结尾幻灯片布局（复杂的动漫风格，经典哆啦A梦风格）：
- 标题/标题：简洁无衬线字体置于幻灯片顶部中央（禁止艺术/装饰性字体）
- 主要内容：关键要点或 CENTER 结尾信息
- 背景：全屏插图，背景包含所有主要角色（哆啦A梦、大雄、朋友们），覆盖整个幻灯片
- 角色应拥有有意义的姿势，反映旅程的结束
- 颜色：精致、温暖、柔和的色调（非儿童化的鲜艳色彩）
- 整体感觉：成熟、优雅、精致""",
}

# 自定义样式的默认布局
SLIDE_LAYOUTS_DEFAULT: Dict[str, str] = {
    "opening": """开场幻灯片布局：
- 标题：顶部中央的大粗体字体
- 作者/隶属：底部小字体
- 主视觉：一个中心元素（图标、插图或抽象形状）
- 背景：纯色或细微渐变匹配风格主题""",

    "content": """内容幻灯片布局：
- 标题：幻灯片左上角
- 内容：结构良好，字体大小适中，间距良好
- IF图形/表格：突出展示它们作为主要视觉内容
- 如果没有图表/图表：为每段添加图标或插图以填充空间
- 布局：可以是垂直（从上到下）或水平（列）""",

    "ending": """结尾幻灯片布局：
- 标题/标题：在滑梯顶部中心
- 主要内容：关键要点或 CENTER 结尾信息""",
}

# 幻灯片常用规则（附加于自定义style_hints）
SLIDE_COMMON_STYLE_RULES = """如果幻灯片有图表：重点放在它们作为主要视觉内容，打磨以符合风格。如果没有图表：为每个段落添加图标或插图，填满整页。桌子的边框应该是纯色的（不允许图案或装饰）。要把页面填满，避免留空。"""

# 海报常见规则（附加于自定义style_hints）
POSTER_COMMON_STYLE_RULES = """如果海报有图形/表格：重点以它们为主要视觉内容，打磨以符合风格。"""

# 一般提示
VISUALIZATION_HINTS = """可视化：
- 使用图表和图标来表示概念
- 将数据/数字可视化为图表
- 使用项目符号，突出关键指标
- 保持背景干净简洁"""

CONSISTENCY_HINT = "重要提示：使用参考幻灯片时保持颜色和风格一致。"

SLIDE_FIGURE_HINT = "参考图：重新绘制以匹配视觉风格和配色方案。保留原始结构和关键信息，但让它们与幻灯片设计无缝融合。"

POSTER_FIGURE_HINT = "参考图：重新绘制以匹配视觉风格和配色方案。保留原始结构和关键信息，但让它们与海报设计无缝融合。"



# STYLE_PROCESS_PROMPT = """User wants this style for presentation slides: {user_style}
#
# IMPORTANT RULES:
# 1. Default to MORANDI COLOR PALETTE (soft, muted, low-saturation colors with gray undertones) and LIGHT background unless user specifies otherwise.
# 2. Keep it CLEAN and SIMPLE - NO flashy/gaudy elements. Every visual element must be MEANINGFUL.
# 3. LIMITED COLOR PALETTE (3-4 colors max).
#
# Output JSON:
# {{
#     "style_name": "Style name with brief description (e.g., Cyberpunk sci-fi style with high-tech aesthetic)",
#     "color_tone": "Color tone description - prefer Morandi palette with light background (e.g., light cream background with muted sage green and dusty rose accents)",
#     "special_elements": "Any special visual elements like characters, mascots, motifs - must be MEANINGFUL, not random decoration",
#     "decorations": "Background/border effects - keep SIMPLE and CLEAN (or empty string)",
#     "valid": true,
#     "error": null
# }}
#
# Examples:
# - "cyberpunk": {{"style_name": "Cyberpunk sci-fi style with high-tech aesthetic", "color_tone": "dark background with neon cyan and magenta accents", "special_elements": "", "decorations": "subtle grid pattern, neon glow on borders", "valid": true, "error": null}}
# - "Studio Ghibli": {{"style_name": "Studio Ghibli anime style with whimsical aesthetic", "color_tone": "light cream background with soft Morandi watercolor tones - muted sage, dusty pink, soft gray-blue", "special_elements": "Totoro or soot sprites can appear as friendly guides - must relate to content", "decorations": "soft clouds or nature elements as borders", "valid": true, "error": null}}
# - "minimalist": {{"style_name": "Clean minimalist style", "color_tone": "light warm gray background with Morandi palette - charcoal text, muted gold accent", "special_elements": "", "decorations": "", "valid": true, "error": null}}
#
# If inappropriate, set valid=false with error."""

# FORMAT_POSTER = "Wide landscape poster layout (16:9 aspect ratio). Just ONE poster. Keep information density moderate, leave whitespace for readability."
# FORMAT_SLIDE = "Wide landscape slide layout (16:9 aspect ratio)."

# POSTER_STYLE_HINTS: Dict[str, str] = {
#     "academic": "Academic conference poster style with LIGHT CLEAN background. English text only. Use PROFESSIONAL, CLEAR tones with good contrast and academic fonts. Use 3-column layout showing story progression. Preserve details from the content. Title section at the top can have a colored background bar to make it stand out. FIGURES: Preserve original scientific figures - maintain their accuracy, style, and integrity. Include institution logo if present.",
#     "doraemon": "Classic Doraemon anime style, bright and friendly. English text only. Use WARM, ELEGANT, MUTED tones. Use ROUNDED sans-serif fonts for ALL text (NO artistic/fancy/decorative fonts). Large readable text. Use 3-column layout showing story progression. Each column can have scene-appropriate background (e.g., cloudy for problem, clearing for method, sunny for result). Keep it simple, not too fancy. Doraemon character as guide only (1-2 small figures), not the main focus.",
# }

# SLIDE_STYLE_HINTS: Dict[str, str] = {
#     "academic": "Professional STANDARD ACADEMIC style. English text only. Use ROUNDED sans-serif fonts for ALL text. Use MORANDI COLOR PALETTE (soft, muted, low-saturation colors) with LIGHT background. Clean simple lines. IMPORTANT: Figures and tables are CRUCIAL - REDRAW them to match the visual style, make them BLEND seamlessly with the background and color scheme. Visualize data with CHARTS (bar, line, pie, radar) - REDRAW charts to match the style, make them LARGE and meaningful. Layout should be SPACIOUS and ELEGANT - avoid crowding, leave breathing room. Overall feel: minimal, scholarly, professional, sophisticated.",
#     "doraemon": "Classic Doraemon anime style, bright and friendly. Doraemon anime style with SOPHISTICATED, REFINED color palette (NOT childish bright colors). English text only. PRESERVE EVERY DETAIL from the content. Use ROUNDED sans-serif fonts for ALL text (NO artistic/fancy/decorative fonts). Bullet point headings should be BOLD. LIMITED COLOR PALETTE (3-4 colors max): Use WARM, ELEGANT, MUTED tones - mature and tasteful, consistent throughout all slides. IF the slide has figures/tables: focus on them as the main visual content, enlarge when helpful. IF NO figures/tables: add illustrations or icons for each paragraph to fill the page. Tables should have PLAIN borders (NO patterns/decorations on borders). Highlight key numbers with colors. Characters should appear MEANINGFULLY (not random decoration) - they should react to or interact with the content, with appropriate poses/actions and sizes.",
# }

# SLIDE_LAYOUTS_ACADEMIC: Dict[str, str] = {
#     "opening": """Opening Slide Layout:
# - Title: Large font at TOP CENTER
# - Authors/Affiliations: Small font at BOTTOM
# - Main Visual: ONE element on CENTER
# - Background: LIGHT color (white or very light gray)""",
#
#     "content": """Content Slide Layout:
# - Title: At TOP LEFT of slide
# - Content: Moderate font size, SPACIOUS layout
# - Figures/tables should BLEND with background color and style - polished and refined
# - Visualize data with CHARTS (bar, line, pie, radar) - make them LARGE and meaningful
# - All charts/figures should use UNIFIED style (same accent color, same line weights)
# - IF figures/tables present: Feature them LARGE as main visual content
# - Add LARGE simple-line icons for each paragraph
# - Background: LIGHT color, SAME as previous slide
# - Overall feel: minimal, scholarly, professional""",
#
#     "ending": """Ending Slide Layout:
# - Title/Heading: At TOP CENTER of slide
# - Main Content: Key takeaways in CENTER
# - Background: LIGHT color, SAME as previous slide""",
# }

# SLIDE_LAYOUTS_DORAEMON: Dict[str, str] = {
#     "opening": """Opening Slide Layout (Sophisticated Anime Style, Classic Doraemon Style):
# - Title: Large simple sans-serif font at TOP CENTER (NO artistic/decorative fonts)
# - Authors/Affiliations: Small font at BOTTOM center
# - Main Visual: Doraemon character in CENTER, can be within a scene/setting that hints at the topic
# - Background: Can use a SCENE illustration as border/frame (e.g., doorway, window, landscape) instead of plain border
# - Color: SOPHISTICATED, WARM, MUTED tones (NOT childish bright colors)
# - Overall feel: Mature, elegant, refined""",
#
#     "content": """Content Slide Layout (Sophisticated Anime Style, Classic Doraemon Style):
# - Title: Simple sans-serif font at TOP LEFT of slide (NO artistic/decorative fonts)
# - Optional: TOP HALF can feature a WIDE scene illustration that reflects the content's mood/theme
# - Content Area: Inside a THIN, PLAIN, SOFT-COLORED rounded border/frame (NO patterns/decorations on border)
# - Background: CLEAN, WARM tones (keep it simple and uncluttered)
# - Color: SOPHISTICATED, WARM, MUTED tones - consistent throughout all slides (NOT childish bright colors)
# - IF figures/tables present: Feature them prominently as main visual content
# - IF NO figures/tables: Add illustrations or icons for each paragraph to fill space
# - Characters: Should appear MEANINGFULLY with context-appropriate actions/poses (not random decoration), size can vary based on importance
# - PRESERVE EVERY DETAIL from the content provided
# - Fill the slide with rich visual content, avoid empty space""",
#
#     "ending": """Ending Slide Layout (Sophisticated Anime Style, Classic Doraemon Style):
# - Title/Heading: Simple sans-serif font at TOP CENTER of slide (NO artistic/decorative fonts)
# - Main Content: Key takeaways or closing message in CENTER
# - Background: FULL-SCREEN illustration featuring ALL main characters (Doraemon, Nobita, friends) as the background, covering the entire slide
# - Characters should have meaningful poses reflecting the journey's conclusion
# - Color: SOPHISTICATED, WARM, MUTED tones (NOT childish bright colors)
# - Overall feel: Mature, elegant, refined""",
# }

# SLIDE_LAYOUTS_DEFAULT: Dict[str, str] = {
#     "opening": """Opening Slide Layout:
# - Title: Large bold font at TOP CENTER
# - Authors/Affiliations: Small font at BOTTOM
# - Main Visual: ONE central element (icon, illustration, or abstract shape)
# - Background: Solid color or subtle gradient matching style theme""",
#
#     "content": """Content Slide Layout:
# - Title: At TOP LEFT of slide
# - Content: Well-organized with moderate font size, good spacing
# - IF figures/tables present: Feature them prominently as main visual content
# - IF NO figures/tables: Add icons or illustrations for each paragraph to fill space
# - Layout: Can be vertical (top-to-bottom) OR horizontal (columns)""",
#
#     "ending": """Ending Slide Layout:
# - Title/Heading: At TOP CENTER of slide
# - Main Content: Key takeaways or closing message in CENTER""",
# }

# SLIDE_COMMON_STYLE_RULES = """IF the slide has figures/tables: focus on them as the main visual content, polish them to fit the style. IF NO figures/tables: add icons or illustrations for each paragraph to fill the page. Tables should have PLAIN borders (NO patterns/decorations). Fill the page well, avoid empty space."""

# POSTER_COMMON_STYLE_RULES = """IF the poster has figures/tables: focus on them as the main visual content, polish them to fit the style."""

# VISUALIZATION_HINTS = """Visualization:
# - Use diagrams and icons to represent concepts
# - Visualize data/numbers as charts
# - Use bullet points, highlight key metrics
# - Keep background CLEAN and simple"""
#
# CONSISTENCY_HINT = "IMPORTANT: Maintain consistent colors and style with the reference slide."
#
# SLIDE_FIGURE_HINT = "For reference figures: REDRAW them to match the visual style and color scheme. Preserve the original structure and key information, but make them BLEND seamlessly with the slide design."
#
# POSTER_FIGURE_HINT = "For reference figures: REDRAW them to match the visual style and color scheme. Preserve the original structure and key information, but make them BLEND seamlessly with the poster design."
