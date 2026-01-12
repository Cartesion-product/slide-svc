"""
LLM prompts for content planning (slides and posters)
"""
from typing import Dict

# 纸质幻灯片规划提示
PAPER_SLIDES_PLANNING_PROMPT = """通过在下方分配内容，将文档组织成{min_pages}-{max_pages}幻灯片。

## 文档摘要
{summary}
{assets_section}
## 输出场
- **id**：幻灯片标识符
- **标题**：适合此幻灯片的简明标题，如论文标题、方法名称或主题名称
- **内容**：本幻灯片的主文本。这是最重要的领域。要求：
  - **详细方法描述**：对于方法幻灯片，请详细描述每个步骤/组件。如果有多个步骤，解释每个步骤（它的作用、工作原理、输入/输出是什么）。不要把话压缩成一句模糊的话。
  - **保留关键公式**：如果源有公式，在LaTeX中包含1-2个相关公式（\\（ ... \\） 或 \\[ ... \\]），含义可变。
  - **保留特定数字**：关键百分比、指标、数据集大小和比较值。
  - **内容丰富**：每张幻灯片应包含足够细节以完整解释其主题。
  - **从源码复制**：从摘要中提取并调整文本。不要把它简化成模糊的一句话。
  - 仅使用上述信息。不要捏造细节，语言使用简体中文。
- **表格**：你想在本幻灯片上展示的表格
  - table_id：例如，“表1”、“文档表1”
  - 提取：（可选）HTML格式的部分表格。请包含原始表中的实际数据值，而非占位符
  - 重点：（可选）强调哪个方面
- **数字**：你想在这张幻灯片上展示的数据
  - figure_id：例如，“图1”、“文档图1”
  - 焦点：（可选）突出什么
- 注意：如果表格和图表相互补充，幻灯片可以同时呈现。

## 内容指南

内容分布在涵盖以下领域的{min_pages}-{max_pages}幻灯片中：

1. **标题/封面**：论文标题或方法名，所有作者姓名，隶属关系

2. **背景/问题**：
   - 研究问题的全上下文
   - 现有方法的具体局限性（逐项列出）
   - 为什么这些限制很重要

3. **方法/方法**（可跨多页幻灯片）：
   - 包含组件名称及其角色的框架概述
   - 如果方法有多个阶段，则为每个阶段分配内容
   - 包含1-2个带有可变解释的关键公式
   - 技术细节：算法、参数、实现细节
   - 匹配数据，显示架构或管道

4. **结果/实验**（可跨多个幻灯片）：
   - 数据集详情：名称、大小、拆分、带有精确编号的类别
   - 主要评估指标及其衡量对象
   - 带有精确数值和比较的性能数据
   - 具有具体影响数值的消融发现
   - 比赛结果表

5. **结论**：
   - 明确列出每个主要贡献
   - 带有具体数字的关键发现

## Output Format (JSON)
```json
{{
  "slides": [
    {{
      "id": "slide_01",
      "title": "[Paper/Method name]",
      "content": "[All authors with affiliations]",
      "tables": [],
      "figures": []
    }},
    {{
      "id": "slide_02",
      "title": "[Method/Framework name]",
      "content": "[Detailed description: The framework consists of X components. Component A does... Component B handles... The process flow is...]",
      "tables": [],
      "figures": [{{"figure_id": "Figure X", "focus": "[architecture/pipeline]"}}]
    }},
    {{
      "id": "slide_03",
      "title": "[Results/Evaluation]",
      "content": "[Full results: Evaluated on Dataset (size, categories). Metrics include X, Y, Z. Main results show... Compared to baselines...]",
      "tables": [{{"table_id": "Table X", "extract": "<table><tr><th>Method</th><th>Metric</th></tr><tr><td>Ours</td><td>XX.X</td></tr><tr><td>Baseline</td><td>XX.X</td></tr></table>", "focus": "[comparison]"}}],
      "figures": []
    }}
  ]
}}
```

## 关键要求
1. **数学公式**：如果源代码包含公式，方法幻灯片中至少包含1-2个关键/代表性公式，使用LaTeX符号。在 JSON 中，反斜杠逃脱为 \\\\（例如 \\\\（ \\\\mathcal{{X}} \\\\））。
2. **最小内容长度**：每张幻灯片内容应至少150-200字（标题除外）。避免过于简短的总结。
3. **具体数字**：使用来源的精确数值。
4. **表数据**：从原始表中提取实际数值表。
"""

# 纸质海报密度指南
PAPER_POSTER_DENSITY_GUIDELINES: Dict[str, str] = {
    "sparse": """电流密度水平是**稀疏**的。内容应简洁但信息丰富。
保留：主要研究问题、方法名称及核心思想、最佳性能数据、关键贡献。
使用提取（部分表）展示表，仅显示具有实际值的最重要行。
写出清晰的句子，捕捉每个部分的核心观点。
如果关键的数学公式是方法的核心，仍应包含它们。""",

    "medium": """电流密度水平为**中**。内容应涵盖主要观点并附带细节。
保留：研究问题及其背景、方法组成及其工作原理、主要结果及对比、贡献。
**包含定义方法并附带符号解释的数学公式**。
包含包含关键列/行和实际数据值的相关表。
写出完整的解释，让读者有扎实的理解。""",

    "dense": """电流密度水平是**密度**。内容应全面且具备完整的技术细节。
保留：完整的问题背景和局限性，所有方法组件及技术描述，完整的实验结果包括消融，所有贡献和发现。
**包含关键数学公式**并附有符号解释。
包含完整的表格或详细摘录，展示实际数据。
撰写详尽的解释，涵盖方法论、实施细节和分析。
直接从源头复制具体数字、百分比和指标。""",
}

# 纸质海报策划提示
PAPER_POSTER_PLANNING_PROMPT = """通过在下方分发内容，将文档组织成海报部分。

## 文档摘要
{summary}
{assets_section}
## 内容密度
{density_guidelines}

## 输出场
- **id**：分段标识符
- **标题**：本节简明标题，如论文标题、方法名称或主题
- **内容**：本节的主文。这是最重要的领域。要求：
  - **详细方法描述**：方法部分请详细描述每个步骤/组件。如果有多个步骤，请分别解释每个步骤。
  - **保留关键公式**：如果源有公式，在LaTeX中包含1-2个相关公式（\\（ ... \\）），含义可变。
  - **保留特定数字**：关键百分比、指标、数据集大小、比较值。
  - **内容丰富**：每个章节应包含足够的细节，以充分解释其主题。
  - **从源码复制**：从摘要中提取并调整文本。不要把事情简化成模糊的总结。
  - 根据上述密度调整细节等级。仅使用提供的信息。不要捏造细节。
- **表格**：本节显示表格
  - table_id：例如，“表1”、“文档表1”
  - 提取：（可选）HTML格式的部分表格。请包含原始表中的实际数据值，而非占位符
  - 重点：（可选）强调哪个方面
- **数字**：本节展示的数字
  - figure_id：例如，“图1”、“文档图1”
  - 焦点：（可选）突出什么
- 注意：如果表格和图表相辅相成，则可以同时使用。

## 章节指南

1. **标题/标题**：论文标题或方法名、所有作者、隶属关系

2. **背景/动机**：研究问题及其上下文，现有方法的具体局限性

3. **方法（核心部分）：
   - 包含组件名称及其角色的框架概述
   - 如果方法有多个阶段，则为每个阶段分配内容
   - 包含1-2个带有可变解释的关键公式
   - 技术细节：算法、参数、实现细节
   - 与数字配对

4. **结果**：
   - 带有精确数字的数据集详细信息（大小、分割、类别）
   - 主要指标及其衡量对象
   - 来自表中具有精确数值的性能数据
   - 关键比较与消融发现

5. **结论**：主要贡献明确列出

## Output Format (JSON)
```json
{{
  "sections": [
    {{
      "id": "poster_title",
      "title": "[Paper/Method name]",
      "content": "[All authors with affiliations]",
      "tables": [],
      "figures": []
    }},
    {{
      "id": "poster_method",
      "title": "[Method/Framework name]",
      "content": "[Detailed description: The framework consists of X components. Component A does... Component B handles... The process flow is...]",
      "tables": [],
      "figures": [{{"figure_id": "Figure X", "focus": "[architecture]"}}]
    }},
    {{
      "id": "poster_results",
      "title": "[Results/Evaluation]",
      "content": "[Full results: Evaluated on Dataset (size, categories). Metrics include X, Y, Z. Main results show... Compared to baselines...]",
      "tables": [{{"table_id": "Table X", "extract": "<table><tr><th>Method</th><th>Metric</th></tr><tr><td>Ours</td><td>XX.X</td></tr><tr><td>Baseline</td><td>XX.X</td></tr></table>", "focus": "[comparison]"}}],
      "figures": []
    }}
  ]
}}
```

## 关键要求
1. **数学公式**：如果源代码包含公式，方法部分至少包含1-2个关键/代表性公式，使用LaTeX。在 JSON 中，反斜杠逃脱为 \\\\（例如 \\\\（ \\\\mathcal{{X}} \\\\））。
2. **最低内容长度**：每个章节内容应至少100-150字（标题除外）。避免过于简短的总结。
3. **具体数字**：使用来源的精确数值。
4. **表数据**：从原始表中提取实际数值表。
"""

# 通用文档提示（无固定学术结构）
GENERAL_SLIDES_PLANNING_PROMPT = """通过在下方分配内容，将文档组织成{min_pages}-{max_pages}幻灯片。

## 文档内容
{summary}
{assets_section}
## 输出场
- **id**：幻灯片标识符
- **标题**：该幻灯片的简明标题，如文档标题或主题名称
- **内容**：本幻灯片的主文本。这是最重要的领域。要求：
  - **详细描述**：如果有多个点/步骤，请描述每一个。不要把它压缩成模糊的总结。
  - **保留关键公式**：如有，包含相关的数学或技术公式。
  - **保留特定数字**：关键百分比、统计数据、日期、数量和比较值。
  - **内容丰富**：每张幻灯片应包含足够细节以完整解释其主题。
  - **从源码复制**：从内容中提取并调整文本。不要把它简化成模糊的一句话。
  - 仅使用上述信息。不要捏造细节。
- **表格**：你想在本幻灯片上展示的表格
  - table_id：例如，“表1”、“文档表1”
  - 提取：（可选）HTML格式的部分表格。请包含原始表中的实际数据值，而非占位符
  - 重点：（可选）强调哪个方面
- **数字**：你想在这张幻灯片上展示的数据
  - figure_id：例如，“图1”、“文档图1”
  - 焦点：（可选）突出什么
- 注意：如果表格和图表相互补充，幻灯片可以同时呈现。

## 内容指南

内容分布在 {min_pages}-{max_pages} 幻灯片中。识别文档自身结构并遵循：

1. **标题/封面**：文档标题、作者/来源（如有）

2. **主内容**（可跨多个幻灯片）：
   - 根据文档的自然结构组织为逻辑幻灯片
   - 每张幻灯片应聚焦于一个主题，细节详尽
   - 如果内容有多个阶段/步骤，则为每个阶段专门分配内容
   - 包含具体数字、数据点和示例
   - 将相关表格/图表与其解释相匹配

3. **总结/结论**：关键要点及具体数字（如适用）

## Output Format (JSON)
```json
{{
  "slides": [
    {{
      "id": "slide_01",
      "title": "[Document title]",
      "content": "[Authors/source if available]",
      "tables": [],
      "figures": []
    }},
    {{
      "id": "slide_02",
      "title": "[Topic name]",
      "content": "[Detailed description: This section covers X, Y, Z. The key aspects include... Specific data shows...]",
      "tables": [],
      "figures": [{{"figure_id": "Figure X", "focus": "[what to highlight]"}}]
    }},
    {{
      "id": "slide_03",
      "title": "[Key Data/Statistics]",
      "content": "[Full details with specific numbers, statistics, and comparisons...]",
      "tables": [{{"table_id": "Table X", "extract": "<table><tr><th>Item</th><th>Value</th></tr><tr><td>A</td><td>XX.X</td></tr></table>", "focus": "[key point]"}}],
      "figures": []
    }}
  ]
}}
```

## 关键要求
1. **公式**：如有，包含任何公式或技术表达，完全照实际出现。
2. **最小内容长度**：每张幻灯片内容应至少150-200字（标题除外）。避免过于简短的总结。
3. **具体数字**：使用来源的精确数值。
4. **表数据**：从原始表中提取实际数值表。
"""

# 海报密度一般指南
GENERAL_POSTER_DENSITY_GUIDELINES: Dict[str, str] = {
    "sparse": """电流密度水平是**稀疏**的。内容应简洁但信息丰富。
保持：主题、核心信息、要点、重要收获。
叙事内容方面：关键情节、主要角色、核心主题。
数据内容：最重要的数字和与实际数值的比较。
采用提取（部分表）展示仅显示具有实数据的最重要的行的表格。
写出清晰的句子，捕捉每个部分的核心观点。
如果关键公式对内容至关重要，仍应包含它们。""",
    
    "medium": """电流密度水平为**中**。内容应涵盖主要观点并附带细节。
保持：主题带背景、关键概念解释、支持例证、主要结论。
叙事内容方面：情节发展、人物关系、因果关系。
数据内容：关键统计数据，带有上下文和使用精确数字进行比较。
**包含对解释很重要的公式/方程**。
包含包含关键列/行和实际数据值的相关表。
写出完整的解释，让读者有扎实的理解。""",
    
    "dense": """电流密度水平是**密度**。内容应全面且细节详尽。
保留：完整的背景和背景，所有关键概念，附有完整解释，详细示例和分析。
叙事内容：完整剧情带支线，所有角色细节，完整的因果链。
数据内容：关键统计数据，精确值，详细分解，详尽比较。
**包含关键公式/方程**并附有解释。
包含完整的表格或详细摘录，展示实际数据。
写出涵盖所有重要方面的详尽解释。
直接从来源复制具体数字和技术细节。""",
}

# 通用海报策划提示
GENERAL_POSTER_PLANNING_PROMPT = """通过在下方分发内容，将文档组织成海报部分。

## 文档内容
{summary}
{assets_section}
## 内容密度
{density_guidelines}

## 输出场
- **id**：分段标识符
- **标题**：本节简明标题，如文档标题或主题名称
- **内容**：本节的主文。这是最重要的领域。要求：
  - **详细描述**：如果有多个点/步骤，请描述每一个。不要把它压缩成模糊的总结。
  - **保留关键公式**：如有，包含相关的数学或技术公式。
  - **保留特定数字**：关键百分比、统计数据、日期、数量和比较值。
  - **内容丰富**：每个章节应包含足够的细节，以充分解释其主题。
  - **从源码复制**：从内容中提取并调整文本。不要把事情简化成模糊的总结。
  - 根据上述密度调整细节等级。仅使用提供的信息。不要捏造细节。
- **表格**：本节显示表格
  - table_id：例如，“表1”、“文档表1”
  - 提取：（可选）HTML格式的部分表格。请包含原始表中的实际数据值，而非占位符
  - 重点：（可选）强调哪个方面
- **数字**：本节展示的数字
  - figure_id：例如，“图1”、“文档图1”
  - 焦点：（可选）突出什么
- 注意：如果表格和图表相辅相成，则可以同时使用。

## 章节指南

根据文档的自然结构，将内容组织成逻辑部分：

1. **标题/标题**：文档标题、作者/来源（如有）

2. **主要内容**：关键话题及完整细节，若有多个阶段/步骤，则专门为每个主题提供内容

3. **关键数据**：重要数字、统计数据或来自具有精确值的表中的数据

4. **摘要**：主要要点及具体数字

## Output Format (JSON)
```json
{{
  "sections": [
    {{
      "id": "poster_title",
      "title": "[Document title]",
      "content": "[Authors/source if available]",
      "tables": [],
      "figures": []
    }},
    {{
      "id": "poster_content",
      "title": "[Topic name]",
      "content": "[Detailed description: This topic covers X, Y, Z. The key aspects include... Specific data shows...]",
      "tables": [],
      "figures": [{{"figure_id": "Figure X", "focus": "[key concept]"}}]
    }},
    {{
      "id": "poster_data",
      "title": "[Key Data/Statistics]",
      "content": "[Important data with specific numbers and comparisons...]",
      "tables": [{{"table_id": "Table X", "extract": "<table><tr><th>Item</th><th>Value</th></tr><tr><td>A</td><td>XX.X</td></tr></table>"}}],
      "figures": []
    }}
  ]
}}
```

## 关键要求
1. **公式**：如有，包含任何公式或技术表达，完全照实际出现。
2. **最低内容长度**：每个章节内容应至少100-150字（标题除外）。避免过于简短的总结。
3. **具体数字**：使用来源的精确数值。
4. **表数据**：从原始表中提取实际数值表。
"""

# # Paper slides planning prompt
# PAPER_SLIDES_PLANNING_PROMPT = """Organize the document into {min_pages}-{max_pages} slides by distributing the content below.
#
# ## Document Summary
# {summary}
# {assets_section}
# ## Output Fields
# - **id**: Slide identifier
# - **title**: A concise title suitable for this slide, such as paper title, method name, or topic name
# - **content**: The main text for this slide. This is the MOST IMPORTANT field. Requirements:
#   - **DETAILED METHOD DESCRIPTION**: For method slides, describe each step/component in detail. If there are multiple steps, explain each one (what it does, how it works, what's the input/outputs). Don't compress into one vague sentence.
#   - **PRESERVE KEY FORMULAS**: If the source has formulas, include 1-2 relevant ones in LaTeX (\\( ... \\) or \\[ ... \\]) with variable meanings.
#   - **PRESERVE SPECIFIC NUMBERS**: Key percentages, metrics, dataset sizes, and comparison values.
#   - **SUBSTANTIAL CONTENT**: Each slide should contain enough detail to fully explain its topic.
#   - **COPY FROM SOURCE**: Extract and adapt text from the summary. Do not over-simplify into vague one-liners.
#   - Only use information provided above. Do not invent details.
# - **tables**: Tables you want to show on this slide
#   - table_id: e.g., "Table 1", "Doc Table 1"
#   - extract: (optional) Partial table in HTML format. INCLUDE ACTUAL DATA VALUES from the original table, not placeholders
#   - focus: (optional) What aspect to emphasize
# - **figures**: Figures you want to show on this slide
#   - figure_id: e.g., "Figure 1", "Doc Figure 1"
#   - focus: (optional) What to highlight
# - Note: A slide can have both tables and figures together if they complement each other.
#
# ## Content Guidelines
#
# Distribute content across {min_pages}-{max_pages} slides covering these areas:
#
# 1. **Title/Cover**: Paper title or method name, all author names, affiliations
#
# 2. **Background/Problem**:
#    - The research problem with full context
#    - Specific limitations of existing approaches (list each one)
#    - Why these limitations matter
#
# 3. **Method/Approach** (can span multiple slides):
#    - Framework overview with component names and their roles
#    - If the method has multiple stages, dedicate content to each stage
#    - Include 1-2 key formulas with variable explanations
#    - Technical details: algorithms, parameters, implementation specifics
#    - Match figures showing architecture or pipeline
#
# 4. **Results/Experiments** (can span multiple slides):
#    - Dataset details: name, size, splits, categories with EXACT numbers
#    - Main evaluation metrics and what they measure
#    - Performance numbers with EXACT values and comparisons
#    - Ablation findings with specific impact numbers
#    - Match tables showing results
#
# 5. **Conclusion**:
#    - Each main contribution listed explicitly
#    - Key findings with specific numbers
#
# ## Output Format (JSON)
# ```json
# {{
#   "slides": [
#     {{
#       "id": "slide_01",
#       "title": "[Paper/Method name]",
#       "content": "[All authors with affiliations]",
#       "tables": [],
#       "figures": []
#     }},
#     {{
#       "id": "slide_02",
#       "title": "[Method/Framework name]",
#       "content": "[Detailed description: The framework consists of X components. Component A does... Component B handles... The process flow is...]",
#       "tables": [],
#       "figures": [{{"figure_id": "Figure X", "focus": "[architecture/pipeline]"}}]
#     }},
#     {{
#       "id": "slide_03",
#       "title": "[Results/Evaluation]",
#       "content": "[Full results: Evaluated on Dataset (size, categories). Metrics include X, Y, Z. Main results show... Compared to baselines...]",
#       "tables": [{{"table_id": "Table X", "extract": "<table><tr><th>Method</th><th>Metric</th></tr><tr><td>Ours</td><td>XX.X</td></tr><tr><td>Baseline</td><td>XX.X</td></tr></table>", "focus": "[comparison]"}}],
#       "figures": []
#     }}
#   ]
# }}
# ```
#
# ## CRITICAL REQUIREMENTS
# 1. **MATHEMATICAL FORMULAS**: If the source contains formulas, include at least 1-2 key/representative formulas in Method slides using LaTeX notation. In JSON, escape backslashes as \\\\ (e.g., \\\\( \\\\mathcal{{X}} \\\\)).
# 2. **MINIMUM CONTENT LENGTH**: Each slide content should be at least 150-200 words (except title). Avoid overly brief summaries.
# 3. **SPECIFIC NUMBERS**: Use precise values from source.
# 4. **TABLE DATA**: Extract tables with actual numerical values from the original.
# """
#
# # Paper poster density guidelines
# PAPER_POSTER_DENSITY_GUIDELINES: Dict[str, str] = {
#     "sparse": """Current density level is **sparse**. Content should be concise but still informative.
# Keep: main research problem, method name and core idea, best performance numbers, key contribution.
# Present tables using extract (partial table) showing only the most important rows with ACTUAL values.
# Write clear sentences that capture the essential point of each section.
# Still include key mathematical formulas if they are central to the method.""",
#
#     "medium": """Current density level is **medium**. Content should cover main points with supporting details.
# Keep: research problem with context, method components and how they work, main results with comparisons, contributions.
# **INCLUDE mathematical formulas** that define the method with notation explanations.
# Include relevant tables with key columns/rows and ACTUAL data values.
# Write complete explanations that give readers a solid understanding.""",
#
#     "dense": """Current density level is **dense**. Content should be comprehensive with full technical details.
# Keep: complete problem context and limitations, all method components with technical descriptions, full experimental results including ablations, all contributions and findings.
# **INCLUDE key mathematical formulas** with notation explanations.
# Include complete tables or detailed extracts showing relevant data with actual values.
# Write thorough explanations covering methodology, implementation details, and analysis.
# Copy specific numbers, percentages, and metrics directly from the source.""",
# }
#
# # Paper poster planning prompt
# PAPER_POSTER_PLANNING_PROMPT = """Organize the document into poster sections by distributing the content below.
#
# ## Document Summary
# {summary}
# {assets_section}
# ## Content Density
# {density_guidelines}
#
# ## Output Fields
# - **id**: Section identifier
# - **title**: A concise title for this section, such as paper title, method name, or topic
# - **content**: The main text for this section. This is the MOST IMPORTANT field. Requirements:
#   - **DETAILED METHOD DESCRIPTION**: For method section, describe each step/component in detail. If there are multiple steps, explain each one separately.
#   - **PRESERVE KEY FORMULAS**: If the source has formulas, include 1-2 relevant ones in LaTeX (\\( ... \\)) with variable meanings.
#   - **PRESERVE SPECIFIC NUMBERS**: Key percentages, metrics, dataset sizes, comparison values.
#   - **SUBSTANTIAL CONTENT**: Each section should contain enough detail to fully explain its topic.
#   - **COPY FROM SOURCE**: Extract and adapt text from summary. Do not over-simplify into vague summaries.
#   - Adjust detail level based on density above. Only use information provided. Do not invent details.
# - **tables**: Tables to show in this section
#   - table_id: e.g., "Table 1", "Doc Table 1"
#   - extract: (optional) Partial table in HTML format. INCLUDE ACTUAL DATA VALUES from the original table, not placeholders
#   - focus: (optional) What aspect to emphasize
# - **figures**: Figures to show in this section
#   - figure_id: e.g., "Figure 1", "Doc Figure 1"
#   - focus: (optional) What to highlight
# - Note: A section can have both tables and figures together if they complement each other.
#
# ## Section Guidelines
#
# 1. **Title/Header**: Paper title or method name, all authors, affiliations
#
# 2. **Background/Motivation**: Research problem with context, specific limitations of existing methods
#
# 3. **Method** (core section):
#    - Framework overview with component names and their roles
#    - If the method has multiple stages, dedicate content to each stage
#    - Include 1-2 key formulas with variable explanations
#    - Technical details: algorithms, parameters, implementation specifics
#    - Pair with figures
#
# 4. **Results**:
#    - Dataset details with EXACT numbers (size, splits, categories)
#    - Main metrics and what they measure
#    - Performance numbers with EXACT values from tables
#    - Key comparisons and ablation findings
#
# 5. **Conclusion**: Main contributions listed explicitly
#
# ## Output Format (JSON)
# ```json
# {{
#   "sections": [
#     {{
#       "id": "poster_title",
#       "title": "[Paper/Method name]",
#       "content": "[All authors with affiliations]",
#       "tables": [],
#       "figures": []
#     }},
#     {{
#       "id": "poster_method",
#       "title": "[Method/Framework name]",
#       "content": "[Detailed description: The framework consists of X components. Component A does... Component B handles... The process flow is...]",
#       "tables": [],
#       "figures": [{{"figure_id": "Figure X", "focus": "[architecture]"}}]
#     }},
#     {{
#       "id": "poster_results",
#       "title": "[Results/Evaluation]",
#       "content": "[Full results: Evaluated on Dataset (size, categories). Metrics include X, Y, Z. Main results show... Compared to baselines...]",
#       "tables": [{{"table_id": "Table X", "extract": "<table><tr><th>Method</th><th>Metric</th></tr><tr><td>Ours</td><td>XX.X</td></tr><tr><td>Baseline</td><td>XX.X</td></tr></table>", "focus": "[comparison]"}}],
#       "figures": []
#     }}
#   ]
# }}
# ```
#
# ## CRITICAL REQUIREMENTS
# 1. **MATHEMATICAL FORMULAS**: If the source contains formulas, include at least 1-2 key/representative formulas in Method section using LaTeX. In JSON, escape backslashes as \\\\ (e.g., \\\\( \\\\mathcal{{X}} \\\\)).
# 2. **MINIMUM CONTENT LENGTH**: Each section content should be at least 100-150 words (except title). Avoid overly brief summaries.
# 3. **SPECIFIC NUMBERS**: Use precise values from source.
# 4. **TABLE DATA**: Extract tables with actual numerical values from the original.
# """
#
# # General document prompts (no fixed academic structure)
# GENERAL_SLIDES_PLANNING_PROMPT = """Organize the document into {min_pages}-{max_pages} slides by distributing the content below.
#
# ## Document Content
# {summary}
# {assets_section}
# ## Output Fields
# - **id**: Slide identifier
# - **title**: A concise title for this slide, such as document title or topic name
# - **content**: The main text for this slide. This is the MOST IMPORTANT field. Requirements:
#   - **DETAILED DESCRIPTIONS**: If there are multiple points/steps, describe each one. Don't compress into vague summaries.
#   - **PRESERVE KEY FORMULAS**: If present, include relevant mathematical or technical formulas.
#   - **PRESERVE SPECIFIC NUMBERS**: Key percentages, statistics, dates, quantities, and comparison values.
#   - **SUBSTANTIAL CONTENT**: Each slide should contain enough detail to fully explain its topic.
#   - **COPY FROM SOURCE**: Extract and adapt text from the content. Do not over-simplify into vague one-liners.
#   - Only use information provided above. Do not invent details.
# - **tables**: Tables you want to show on this slide
#   - table_id: e.g., "Table 1", "Doc Table 1"
#   - extract: (optional) Partial table in HTML format. INCLUDE ACTUAL DATA VALUES from the original table, not placeholders
#   - focus: (optional) What aspect to emphasize
# - **figures**: Figures you want to show on this slide
#   - figure_id: e.g., "Figure 1", "Doc Figure 1"
#   - focus: (optional) What to highlight
# - Note: A slide can have both tables and figures together if they complement each other.
#
# ## Content Guidelines
#
# Distribute content across {min_pages}-{max_pages} slides. Identify the document's own structure and follow it:
#
# 1. **Title/Cover**: Document title, authors/source if available
#
# 2. **Main Content** (can span multiple slides):
#    - Organize into logical slides based on the document's natural structure
#    - Each slide should focus on one topic with full details
#    - If the content has multiple stages/steps, dedicate content to each
#    - Include specific numbers, data points, and examples
#    - Match relevant tables/figures with their explanations
#
# 3. **Summary/Conclusion**: Key takeaways with specific numbers if applicable
#
# ## Output Format (JSON)
# ```json
# {{
#   "slides": [
#     {{
#       "id": "slide_01",
#       "title": "[Document title]",
#       "content": "[Authors/source if available]",
#       "tables": [],
#       "figures": []
#     }},
#     {{
#       "id": "slide_02",
#       "title": "[Topic name]",
#       "content": "[Detailed description: This section covers X, Y, Z. The key aspects include... Specific data shows...]",
#       "tables": [],
#       "figures": [{{"figure_id": "Figure X", "focus": "[what to highlight]"}}]
#     }},
#     {{
#       "id": "slide_03",
#       "title": "[Key Data/Statistics]",
#       "content": "[Full details with specific numbers, statistics, and comparisons...]",
#       "tables": [{{"table_id": "Table X", "extract": "<table><tr><th>Item</th><th>Value</th></tr><tr><td>A</td><td>XX.X</td></tr></table>", "focus": "[key point]"}}],
#       "figures": []
#     }}
#   ]
# }}
# ```
#
# ## CRITICAL REQUIREMENTS
# 1. **FORMULAS**: If present, include any formulas or technical expressions exactly as they appear.
# 2. **MINIMUM CONTENT LENGTH**: Each slide content should be at least 150-200 words (except title). Avoid overly brief summaries.
# 3. **SPECIFIC NUMBERS**: Use precise values from source.
# 4. **TABLE DATA**: Extract tables with actual numerical values from the original.
# """
#
# # General poster density guidelines
# GENERAL_POSTER_DENSITY_GUIDELINES: Dict[str, str] = {
#     "sparse": """Current density level is **sparse**. Content should be concise but still informative.
# Keep: main topic, core message, key points, important takeaways.
# For narrative content: key plot points, main characters, central theme.
# For data content: most important numbers and comparisons with ACTUAL values.
# Present tables using extract (partial table) showing only the most important rows with REAL data.
# Write clear sentences that capture the essential point of each section.
# Still include key formulas if they are central to the content.""",
#
#     "medium": """Current density level is **medium**. Content should cover main points with supporting details.
# Keep: topic with context, key concepts explained, supporting examples, main conclusions.
# For narrative content: plot development, character relationships, cause and effect.
# For data content: key statistics with context and comparisons using EXACT numbers.
# **INCLUDE formulas/equations** that are important with explanations.
# Include relevant tables with key columns/rows and ACTUAL data values.
# Write complete explanations that give readers a solid understanding.""",
#
#     "dense": """Current density level is **dense**. Content should be comprehensive with full details.
# Keep: complete context and background, all key concepts with full explanations, detailed examples and analysis.
# For narrative content: full plot with subplots, all character details, complete cause-effect chains.
# For data content: key statistics with EXACT values, detailed breakdowns, thorough comparisons.
# **INCLUDE key formulas/equations** with explanations.
# Include complete tables or detailed extracts showing relevant data with actual values.
# Write thorough explanations covering all important aspects.
# Copy specific numbers and technical details directly from the source.""",
# }
#
# # General poster planning prompt
# GENERAL_POSTER_PLANNING_PROMPT = """Organize the document into poster sections by distributing the content below.
#
# ## Document Content
# {summary}
# {assets_section}
# ## Content Density
# {density_guidelines}
#
# ## Output Fields
# - **id**: Section identifier
# - **title**: A concise title for this section, such as document title or topic name
# - **content**: The main text for this section. This is the MOST IMPORTANT field. Requirements:
#   - **DETAILED DESCRIPTIONS**: If there are multiple points/steps, describe each one. Don't compress into vague summaries.
#   - **PRESERVE KEY FORMULAS**: If present, include relevant mathematical or technical formulas.
#   - **PRESERVE SPECIFIC NUMBERS**: Key percentages, statistics, dates, quantities, and comparison values.
#   - **SUBSTANTIAL CONTENT**: Each section should contain enough detail to fully explain its topic.
#   - **COPY FROM SOURCE**: Extract and adapt text from the content. Do not over-simplify into vague summaries.
#   - Adjust detail level based on density above. Only use information provided. Do not invent details.
# - **tables**: Tables to show in this section
#   - table_id: e.g., "Table 1", "Doc Table 1"
#   - extract: (optional) Partial table in HTML format. INCLUDE ACTUAL DATA VALUES from the original table, not placeholders
#   - focus: (optional) What aspect to emphasize
# - **figures**: Figures to show in this section
#   - figure_id: e.g., "Figure 1", "Doc Figure 1"
#   - focus: (optional) What to highlight
# - Note: A section can have both tables and figures together if they complement each other.
#
# ## Section Guidelines
#
# Organize content into logical sections based on the document's natural structure:
#
# 1. **Title/Header**: Document title, authors/source if available
#
# 2. **Main Content**: Key topics with full details, if there are multiple stages/steps dedicate content to each
#
# 3. **Key Data**: Important numbers, statistics, or data from tables with EXACT values
#
# 4. **Summary**: Main takeaways listed with specific numbers
#
# ## Output Format (JSON)
# ```json
# {{
#   "sections": [
#     {{
#       "id": "poster_title",
#       "title": "[Document title]",
#       "content": "[Authors/source if available]",
#       "tables": [],
#       "figures": []
#     }},
#     {{
#       "id": "poster_content",
#       "title": "[Topic name]",
#       "content": "[Detailed description: This topic covers X, Y, Z. The key aspects include... Specific data shows...]",
#       "tables": [],
#       "figures": [{{"figure_id": "Figure X", "focus": "[key concept]"}}]
#     }},
#     {{
#       "id": "poster_data",
#       "title": "[Key Data/Statistics]",
#       "content": "[Important data with specific numbers and comparisons...]",
#       "tables": [{{"table_id": "Table X", "extract": "<table><tr><th>Item</th><th>Value</th></tr><tr><td>A</td><td>XX.X</td></tr></table>"}}],
#       "figures": []
#     }}
#   ]
# }}
# ```
#
# ## CRITICAL REQUIREMENTS
# 1. **FORMULAS**: If present, include any formulas or technical expressions exactly as they appear.
# 2. **MINIMUM CONTENT LENGTH**: Each section content should be at least 100-150 words (except title). Avoid overly brief summaries.
# 3. **SPECIFIC NUMBERS**: Use precise values from source.
# 4. **TABLE DATA**: Extract tables with actual numerical values from the original.
# """
