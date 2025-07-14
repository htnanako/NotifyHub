# NotifyHub

![GitHub repo size](https://img.shields.io/github/repo-size/htnanako/NotifyHub)
![Docker Image Size (tag)](https://img.shields.io/docker/image-size/htnanako/notifyhub/latest)
![Docker Pulls](https://img.shields.io/docker/pulls/htnanako/notifyhub)
[![GitHub Repo stars](https://img.shields.io/github/stars/htnanako/NotifyHub?style=social)](https://github.com/htnanako/NotifyHub/stargazers)


> 智能通知调度中心 —— 多渠道消息推送统一管理平台

## 软件简介

NotifyHub 是一款支持多种主流推送渠道的智能通知调度平台，适用于个人和团队的消息统一分发、自动化推送、渠道管理等场景。支持通过 Web 界面灵活配置“通知渠道”（如 Telegram、Bark、企业微信）和“通知通道”（消息路由），实现一条消息多平台同步推送。

---

## 支持的通知渠道

| 渠道类型   | 说明                   | 主要参数（配置时需填写）         |
| ---------- | ---------------------- | -------------------------------- |
| Telegram   | 通过 Telegram Bot 推送 | Bot Token、Chat ID               |
| Bark       | iOS 推送工具           | Bark 推送地址（push_url）        |
| 企业微信   | 企业微信应用消息       | 企业ID、应用Secret、AgentID 等   |

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

## 其他说明

- **数据持久化**：请务必挂载 `data/` 目录，避免数据丢失。
- **API 文档**：每个通知通道页面有“使用说明”按钮，自动生成推送 API 文档。
- **社区支持**：遇到问题可前往 [Telegram 社区](https://t.me/notifyhub_chat) 交流。

  
### 许可说明
- 本项目需要授权码才能使用。
- 授权码支持7天试用期。
- 获取license_key请联系作者，发送邮件到service@nanako.cyou提供邮箱，或者试用TG群组的机器人自助申请。
- 不接受任何理由申请退款，不接受任何理由申请退款，不接受任何理由申请退款。

### 永久授权购买
永久授权价格¥30.00。软件已内置购买授权功能，申请试用码安装容器之后可在 `系统设置` -> `授权信息` 中查看授权信息和购买永久授权。目前仅支持支付宝支付。
