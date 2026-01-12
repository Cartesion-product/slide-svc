# 演示文稿Agent服务

全景信息图Agent与Slides生成Agent，基于FastAPI + Celery构建服务。

## 引言

​	借鉴notebooklm的演示文稿功能，基于修改封装Paper2Slides开源框架，构建一个智能体服务，基于现有minio对象存储中已经解析过的论文，携带外网地址图像的MD文件，来进行全景信息图生成与导读PPT，因论文已被解析过，所以选择跳过Paper2Slides的RAG构建，加快生成速度，后续服务默认文生图方式为Fast。



## 需求描述

​	构建智能体服务，用户请求时会传递动态参数用于重构Prompt，通过选定指定论文后，将解析后的MD文件下载地址作为参数调用接口，用户选择生成全景信息图或者是Slides导读PPT，会去创建一个任务来执行，任务需要有状态，支持删除停止任务，任务需要记录生成结果的文件下载地址。论文文件分为两类，一类是系统自带的，一类是用户自己上传的，对于这些论文，生成的全景信息图或者是Slides导读PPT，用户去第一次生成的结果需要保存为系统的默认结果，等后续别的用户再查看论文去生成时第一次就直接展示默认结果（对于系统论文），不满意则进行再次生成。



## 接口设计

任务管理：

1、任务创建（异步，任务队列、状态管理）；

创建任务，将任务添加至队列当中，可执行任务的数量上限为2，控制资源，超过则添加到等待队列当中，等待队列上限为5，队列满则拒绝，不用支持优先级。任务有一个标题，poster任务类型标题为 全景信息图，slides任务类型标题为 演示文稿。文件生成之后，将文件上传至minio，存储文件下载地址，并相应更新系统论文信息表的数据。

2、任务删除；

删除任务，若是在进行中，则对任务进行停止，数据删除，删除不会影响系统论文的默认值。

3、任务详情（Poster和Slides返回结果不一样）；

查询任务为poster时，返回任务标题，文件下载地址；任务为slides时，返回任务标题，文件下载地址，图像下载地址数组；

4、任务结果下载；

通过下载接口获取生成任务的文件下载地址；

5、任务分页查看；

根据用户ID和paperID分页查询相关的任务，单条记录包含标题和类型，时间；





## bucket 名称

slide类型

system：kb-slide-system

user：kb-slide-user

poster类型

system：kb-poster-system

user：kb-poster-user



minio存储路径

system：根据source分级，名称用paper_id

user：根据userId分级，文件ID



## 表结构设计 Mongo

### 系统论文信息存储表  system_paper_agent_result

#### 字段设计

| 字段         | 名称         | 类型  | 说明                                                     |
| ------------ | ------------ | ----- | -------------------------------------------------------- |
| paper_id     | 论文ID       | str   | 论文ID（不唯一）                                         |
| source       | 论文数据源   | str   | 论文来源                                                 |
| agent_type   | 任务类型     | str   | 任务智能体类型【poster，全景信息图；slides，演示文稿；】 |
| file_path    | 结果（地址） | str   | 任务结果（地址）                                         |
| images       | 图像地址     | array | slides图像地址                                           |
| result_id    | 任务ID       | str   | 任务ID（唯一）                                           |
| created_time | 创建时间     | date  | 创建时间                                                 |

#### 索引设计

| 索引字段                                                | 描述                                        |
| ------------------------------------------------------- | ------------------------------------------- |
| UNIQUE KEY uk_paper_agent (paper_id, agent_type,source) | 同一篇论文同一种任务只能存一条（主键/唯一） |
| UNIQUE KEY uk_taskid (result_id)                        | 任务ID全局唯一                              |



### 个人论文任务结果信息存储 user_paper_agent_result

#### 字段设计

| 字段         | 名称         | 类型  | 备注                                                         |
| ------------ | ------------ | ----- | ------------------------------------------------------------ |
| result_id    | 主键         | str   | 主键ID（唯一）                                               |
| title        | 标题         | str   | 标题【默认：全景信息图  或  演示文稿；】                     |
| agent_type   | 任务类型     | str   | 任务智能体类型【poster，全景信息图；slides，演示文稿；】     |
| status       | 任务状态     | str   | 任务状态【waiting，等待中；running，运行中；success，成功；failed，失败；】 |
| error_reason | 失败原因     | str   | 失败原因                                                     |
| paper_id     | 论文ID       | str   | 论文ID（不唯一）                                             |
| source       | 论文数据源   | str   | 论文来源                                                     |
| paper_type   | 论文类型     | str   | 论文类型【system，系统；user，个人】                         |
| style        | 风格偏好     | str   | 风格偏好【用户提示词】                                       |
| language     | 语言         | str   | 语言 (ZH/EN)                                                 |
| density      | 内容密度     | str   | 内容密度(sparse/medium/dense)                                |
| file_path    | 结果（地址） | str   | 任务结果（地址）                                             |
| images       | 图像地址     | array | slides图像地址                                               |
| start_time   | 开始时间     | date  | 开始时间                                                     |
| end_time     | 结束时间     | date  | 结束时间                                                     |
| user_id      | 用户ID       | str   | 用户ID                                                       |
| created_time | 创建时间     | date  | 创建时间                                                     |

#### 索引设计

| 索引字段                                      | 描述                      |
| --------------------------------------------- | ------------------------- |
| UNIQUE KEY uk_taskid (result_id)              | 任务ID全局唯一            |
| KEY idx_user_paper (user_id, paper_id,source) | 用户论文列表页            |
| KEY idx_user_status (user_id, status)         | 用户查看“进行中/失败”任务 |