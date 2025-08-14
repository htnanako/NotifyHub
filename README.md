# NotifyHub

![GitHub repo size](https://img.shields.io/github/repo-size/htnanako/NotifyHub)
![Docker Image Size (tag)](https://img.shields.io/docker/image-size/htnanako/notifyhub/latest)
![Docker Pulls](https://img.shields.io/docker/pulls/htnanako/notifyhub)
[![GitHub Repo stars](https://img.shields.io/github/stars/htnanako/NotifyHub?style=social)](https://github.com/htnanako/NotifyHub/stargazers)


> 智能通知调度中心 —— 多渠道消息推送统一管理平台

## 软件简介

NotifyHub 是一款支持多种主流推送渠道的智能通知调度平台，适用于个人和团队的消息统一分发、自动化推送和渠道管理等场景。

通过直观的 Web 界面，您可以灵活配置「通知渠道」（如 Telegram、Bark、企业微信等）与「通知通道」（消息路由），并借助「通知模板」功能，使用内置的 Emby、PVE、Watchtower 等模板，基于 Jinja2 模板语言构建个性化通知内容。

此外，NotifyHub 提供开放接口，支持开发者自行开发第三方插件，从而扩展并丰富平台功能。

---

## 支持的通知渠道

| 渠道类型   | 说明                   | 主要参数（配置时需填写）         |
| ---------- | ---------------------- | -------------------------------- |
| Telegram   | 通过 Telegram Bot 推送 | Bot Token、Chat ID               |
| Bark       | iOS 推送工具           | Bark 推送地址（push_url）        |
| 企业微信   | 企业微信应用消息       | 企业ID、应用Secret、AgentID 等   |
| Pushdeer  | Pushdeer 消息           | 推送密钥（push_key）            |
| 钉钉       | 钉钉应用消息           | AccessToken   |
| Discord    | Discord 消息           | Webhook URL                     |
| 飞书       | 飞书应用消息           | AppID、AppSecret、receive_id   |
| Server酱3  |  server酱3 app消息   |  Send Key       |
| Email     |   邮件通知消息       |  smtp信息、发件人邮箱信息、收件人邮箱  |

> **说明：**  
> 后续版本将持续增加更多通知渠道支持，敬请期待！

---

## 部署方式

本项目**仅支持 Docker 部署**，无需繁琐环境配置，开箱即用。

### 一键部署命令

```bash
docker run -d --name notifyhub \
  -p 5400:5400 \
  -v $(pwd)/data:/data \
  -e LICENSE_KEY=你的授权码 \
  -e NH_USER=admin \
  -e NH_PASSWORD=123456 \
  htnanako/notifyhub:latest
```

或使用 `docker-compose.yml`：

```yaml
services:
  notifyhub:
    container_name: notifyhub
    image: htnanako/notifyhub
    ports:
      - 5400:5400
    volumes:
      - ./data:/data
    environment:
      LICENSE_KEY: 你的授权码
      NH_USER: admin
      NH_PASSWORD: 123456
    restart: always
```

---

## 必需环境变量

| 变量名         | 说明         | 示例                |
| -------------- | ------------ | ------------------- |
| LICENSE_KEY    | 授权码       | （必填/试用可为空） |
| NH_USER        | 登录用户名   | admin               |
| NH_PASSWORD    | 登录密码     | 123456              |

---

如需添加新渠道或有特殊需求，欢迎在社区或 Issue 区留言反馈！ 

---

## 插件系统

NotifyHub 提供“插件系统”，支持内置插件与第三方插件，便于扩展新能力：

- 插件目录：默认扫描并加载 `/data/plugins` 目录中的插件；每个插件需包含 `manifest.json`。
- 路由挂载：插件内的 `APIRouter` 会被自动挂载到统一前缀 `/api/plugins` 下，例如 `APIRouter(prefix="/plugin_test")` → `/api/plugins/plugin_test/...`。
- 能力复用：插件可通过后端提供的工具函数读取系统配置、获取渠道/通道列表，并复用统一的发送通知能力。

详细规范与示例请参阅《[插件开发指南](https://github.com/htnanako/NotifyHub/blob/main/plugins/%E6%8F%92%E4%BB%B6%E5%BC%80%E5%8F%91%E6%8C%87%E5%8D%97.md)》。

---

## 使用说明

### 通知通道 API 调用方式

NotifyHub 支持通过多种方式调用 API 进行消息推送。

#### 1. 通用 JSON API

- **接口地址**：`http://<你的站点地址>/api/service/notify`
- **请求方式**：POST
- **Content-Type**：application/json

**请求体示例：**

```json
{
  "route_id": "你的通道ID",
  "title": "测试标题",
  "content": "这是一条测试内容",
  "push_img_url": "https://example.com/test.jpg",
  "push_link_url": "https://example.com"
}
```

**参数说明：**

| 参数名         | 说明                 | 必填 |
| -------------- | -------------------- | ---- |
| route_id       | 通道ID，指定推送通道 | 是   |
| title          | 通知标题             | 是   |
| content        | 通知内容             | 是   |
| push_img_url   | 图片URL（可选）      | 否   |
| push_link_url  | 跳转链接（可选）     | 否   |

---

#### 2. cURL 调用示例

```bash
curl -X POST 'http://<你的站点地址>/api/service/notify' \
  -H 'Content-Type: application/json' \
  -d '{
    "route_id": "你的通道ID",
    "title": "测试标题",
    "content": "这是一条测试内容",
    "push_img_url": "https://example.com/test.jpg",
    "push_link_url": "https://example.com"
  }'
```

---

#### 3. Python 调用示例

```python
import requests

url = "http://<你的站点地址>/api/service/notify"
data = {
    "route_id": "你的通道ID",
    "title": "测试标题",
    "content": "这是一条测试内容",
    "push_img_url": "https://example.com/test.jpg",
    "push_link_url": "https://example.com"
}
headers = {"Content-Type": "application/json"}

response = requests.post(url, json=data, headers=headers)
print(response.status_code)
print(response.text)
```

---

#### 4. Bark 兼容接口

- **接口地址**：`http://<你的站点地址>/api/service/notify/<route_id>/<title>/<content>`
- **请求方式**：GET 或 POST
- **Content-Type**：application/json（POST 时）

**POST 请求体（可选）：**

```json
{
  "push_img_url": "https://example.com/test.jpg",
  "push_link_url": "https://example.com"
}
```

---

## 通知模板

NotifyHub 支持自定义“通知模板”，用于灵活配置不同场景下的消息格式。通过模板功能，你可以为不同的通知通道、不同类型的事件，设置专属的标题和内容格式，实现消息的个性化和自动化。

### 功能说明

- **模板类型**：支持普通通知模板和 Emby 专用模板（如媒体添加、播放开始、播放停止等）。
- **模板变量**：模板内容支持[Jinja2](https://docs.jinkan.org/docs/jinja2/)模板语言，使用变量占位，推送时会自动替换为实际数据。例如：`{{user}}`、`{{item_name}}`、`{{time}}` 等。
- **适用范围**：每个通知通道可绑定一个或多个模板，推送时自动匹配对应模板。

---

### 模板样例

#### Emby 消息通知模板举例

- Emby开始播放
```jinja2
{{user}}开始播放 {{title}}{%if year%}({{year}}){%endif%}
```
```jinja2
{%if progress_text%}{{progress_text}}
{%endif%}{{container}} · {{video_stream_title}}
⤷{{transcoding_info}} {{bitrate}}Mbps{%if current_cpu%}
⤷CPU消耗：{{current_cpu}}%{%endif%}
来自：{{server_name}}
大小：{{size}}
设备：{{client}} · {{device_name}}{%if genres%}
风格：{{genres}}{%endif%}{%if intro%}
简介：{{intro}}{%endif%}
```

- Emby停止播放
```jinja2
{{user}}停止播放 {{title}}{%if year%}({{year}}){%endif%}
```
```jinja2
{%if progress_text%}{{progress_text}}
{%endif%}{{container}} · {{video_stream_title}}
⤷{{transcoding_info}} {{bitrate}}Mbps{%if current_cpu%}
⤷CPU消耗：{{current_cpu}}%{%endif%}
来自：{{server_name}}
大小：{{size}}
设备：{{client}} · {{device_name}}{%if genres%}
风格：{{genres}}{%endif%}{%if intro%}
简介：{{intro}}{%endif%}
```

- Emby电影新增
```jinja2
🍟 新片入库： {{title}} {%if release_year%}({{release_year}}){%endif%}
```
```jinja2
🍟 {{server_name}}
入库时间: {{created_at}}{%if genres%}

风格：{{genres}}{%endif%}
大小：{{size}}{%if intro%}
简介：{{intro}}{%endif%}
```

- Emby剧集新增
```jinja2
📺 新片入库： {{title}}
```
```jinja2
📺 {{server_name}}
入库时间: {{created_at}}
{%if episode_title%}
单集标题：{{episode_title}}{%endif%}{%if series_genres%}
风格：{{series_genres}}{%endif%}
大小：{{size}}{%if intro%}
简介：{{intro}}{%endif%}
```

#### PVE 消息通知模板举例

- PVE 备份任务
```jinja2
{{ machine_name }} {{ task_type }} - {{ task_status }}
```
```jinja2
{% for vmid, name, statu, time, size in details %}- ID {{ vmid }} - {{ name }}：{{ size }}，耗时 {{ time }}, 状态 {{ statu }}
{% endfor %}
总耗时: {{ total_time }}
总大小: {{ total_size }}
```

- PVE 精简任务
```jinja2
{{ machine_name }} {{ task_type }} - {{ task_status }}
```
```jinja2
数据存储库：{{ datastore_name }}
任务编号：{{ job_id }}
```

- PVE 垃圾回收任务
```jinja2
{{ machine_name }} {{ task_type }} - {{ task_status }}
```
```jinja2
数据存储库：{{ datastore_name }}
索引文件数量：{{ index_file_count }}
清理垃圾数据量：{{ removed_garbage }}

原始数据体积：{{ original_data_usage }}
实际占用磁盘空间：{{ on_disk_usage }}
去重因子：{{ deduplication_factor }}
```

---


## 其他说明

- **数据持久化**：请务必挂载 `/data` 目录，避免数据丢失。
- **API 文档**：每个通知通道页面有“使用说明”按钮，自动生成推送 API 文档。
- **社区支持**：遇到问题可前往 [Telegram 社区](https://t.me/notifyhub_chat) 交流。

  
### 许可说明
- 本项目需要授权码才能使用。
- 授权码支持7天试用期。
- 获取license_key请联系作者，发送邮件到service@nanako.cyou提供邮箱，或者试用TG群组的机器人自助申请。
- 不接受任何理由申请退款，不接受任何理由申请退款，不接受任何理由申请退款。

### 永久授权购买
永久授权价格¥30.00。软件已内置购买授权功能，申请试用码安装容器之后可在 `系统设置` -> `授权信息` 中查看授权信息和购买永久授权。目前仅支持支付宝支付。
