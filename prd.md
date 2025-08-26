## 新增功能简介
项目进行二次开发，主要包括以下几个功能：
1. 在系统管理菜单下加以下几个菜单项：  
- 模型管理: 包含子菜单
  - 添加模型
  - 模型列表
  - 删除模型
  - 默认模型
- 知识库管理: 包含子菜单
  - 添加知识库
  - 修改知识库：修改配置，名字、描述；嵌入模型不允许修改。需要ruoyi对ragflow的API的payload进行裁剪定制。
  - 删除知识库
  - 知识库列表
  - 添加文档
  - 删除文档
  - 文档列表
**NOTE**: 聊天过程中可以上传文档，不依赖于前面的文档管理权限。上传时，隐含的建立一个隐藏的知识库（绑定真是用户ID，会话ID）。在删除会话时自动删除。上传后，自动完成向量化，在查询时，需要把隐藏知识库ID和用户自己的显式知识库ID，都作为查询的范围。
- 智能体管理：包含子菜单
  - 智能体列表
  - 智能体详情  
- 智能助手管理：包含子菜单
  - 添加智能助手
  - 修改智能助手
  - 删除智能助手
  - 智能助手列表
  - 智能助手详情、执行
- 回话管理：包含子菜单
  - 会话列表/历史
  - 新建会话、执行会话
  - 会话删除

澄清几个概念：
1. 智能体：对应与Langgraph-api里面的graph，一个智能体对应一个graph，一个智能体可以对应多个智能助手。系统发布时有几个智能体是确定的，这些智能体在系统发布后不能被修改。智能体不可改变。智能体的列表、详情也是受权限控制的。智能体列表、详情，需要在Ruoyi系统中，通过数据库静态配置，并保持和Langgraph-api server里面的graph配置保持一致。
2. 智能助手：对应与Langgraph-api里面的assistant，一个智能助手创建自智能体，一个智能体可以对应多个智能助手。智能助手可以由具有特定权限的角色来创建、删除、修改。智能助手的创建、删除、修改都需要在系统中进行授权。一个人创建的智能助手，可以被其他多个具有权限的人共享使用。创建智能助手时，需要保存创建者的信息(id/dept_id)，系统据此利用Ruoyi的”数据权限“功能，实现智能助手的权限控制。也就是说：
- 创建智能助手时，需要完成2个任务：
  - 调用langgraph-api restful api, 创建assistant
  - 保存assistant的id, 其他信息(如名称、描述)到Ruoyi的数据库（需要新建表来存储，特别是需要记录creator的信息）
- 删除智能助手时，需要完成2个任务：
  - 调用langgraph-api restful api, 删除assistant
  - 删除Ruoyi数据库中对应的记录
- 列表智能助手时，需要从Ruoyi数据库中查询智能助手的信息，利用Ruoyi的”数据权限“功能，实现智能助手的权限控制。

## Ruoyi、Ragflow、Langgraph-api的关系
因为知识库、智能助手都需要利用Ruoyi的”数据权限“功能，所以，这些资源的创建、删除、修改，都需要经过ruoyi的参与（主要是记录资源的创建者，为后续权限审核提供依据），而这些资源的真正创建则分别需要Ruoyi通过调用ragflow、langgraph-api提供的RESTful API来实际完成。举两个例子：
- 创建知识库时：
  - Ruoyi调用ragflow的RESTful API, 创建知识库
  - Ruoyi保存知识库的id, 其他信息(如名称、描述)，以及当前用户的id到Ruoyi的数据库（需要新建表来存储，特别是需要记录creator的信息）
- 创建智能助手时，需要完成2个任务：
  - 调用langgraph-api restful api, 创建assistant
  - 保存assistant的id, 其他信息(如名称、描述)，以及当前用户的id到Ruoyi的数据库（需要新建表来存储，特别是需要记录creator的信息）

### Ruoyi对于ragflow的调用
1. ragflow的API
ragflow有两种API：
- ragflow的RESTful API，用于知识库、文档的创建、删除、修改、查询，以及其他一些操作：比如模型的配置等。这些API的使用，都被@LoginRequired修饰，都需要通过Login，得到authorization header，然后在API调用中使用这个authorization header，才能被ragflow所接受。
- ragflow的SDK API，这些API都被@TokenRequired或者@apikey_required修饰，都需要在API调用中使用ragflow的API密钥（key），才能被ragflow所接受。

2. ruoyi对于ragflow的调用
由于ragflow的知识库、文档都是按照tenant来组织的，一个注册的用户就是一个tenant（的owner）；另一方面，ragflow有自己的用户管理系统，用户需要在ragflow系统中注册，才能使用ragflow的功能；最后，ragflow有自己的权限管理。所以，为了让Ruoyi可以调用ragflow的API，需要在Ruoyi中添加一个用户(service_user)，这个用户需要在ragflow系统中注册，并且该用户将作为后续所有调用RESTful API的用户。这个用户的创建、登录都需要Ruoyi智能的自动完成。即：若发现系统中没有这样的用户，则自动通过ragflow注册这个用户，保存它的authorization header，供后续使用。这个authorization header，在ragflow内部没有max_age的保护，可以一直使用；但是，如果出于安全考虑，可以设置一个过期时间，超时后自动重新登录换取新的authorization header。

3. ruoyi对于ragflow api的封装和调用
- 模型管理：分别需要对应的模型添加、删除、设置默认模型的权限
- 知识库管理：分别需要对应的知识库添加、删除、修改、查询的权限，另外还需要知识库的”数据权限“。
- 文档管理：分别需要对应的文档添加、删除、修改、查询的权限，无”数据权限“要求，因为文档的创建、删除、修改、查询，都是在知识库的上下文中进行的，所以，文档的权限，主要是由知识库的权限来控制的。
**NOTE**：对某些（比例未知，需要具体分析）原来的API，如果需要进行”数据权限“管控，需要在Ruoyi中进行重新映射、封装，比如下面的API：
- ragflow中，/v1/document/upload，这个API用来在某个知识库中上传文档，但是知识库的kb_id是放在payload中的，payload如下：
```json
{
    "kb_id": "abcdefg",
    "files": [
        {
            "file_name": "ragflow.pdf",
            "file_content": "base64编码后的文件内容"
        }
    ]
}
```
现在要进行数据权限控制，需要基于kb_id，获取kb对应的depart_id, user_id，然后才能进行权限控制。则：
- 可能需要改成/v1/document/abcdefg/upload，从URL path中获取kb_id，或者
- 直接从payload中获取kb_id

### Ruoyi对于Langgraph-api的调用
1. langgraph-api的API
langgraph-api提供了多个API，分别对应不同的功能：
- create assistant: 创建智能助手
- create thread: 创建聊天线程，或者叫会话
- create run/query run: 执行智能助手、获取执行状态
- query thread/get run result：获取聊天结果
- query history: 查询聊天历史

2. ruoyi对于langgraph-api api的封装和调用
- create assistant: 需要”添加智能助手“权限
- create thread: 需要”智能助手详情、执行“权限
- create run/query run: 需要”智能助手详情、执行“权限
- query thread/get run result：需要”智能助手详情、执行“权限，同时需要”数据权限“，即：判断用户是否是该智能助手的创建者，是否是该聊天历史的创建者。
- query history: 参照query thread的权限，同时需要”数据权限“，即：判断用户是否是该智能助手的创建者，是否是该聊天历史的创建者。