# Stock Trading Telegram Bot

直接透過 Telegram 呼叫股票交易 AI API 的機器人。

## 功能

- `/run` - 獲取 AI 交易建議並執行交易
- `/stock` - 同 /run
- `/health` - 檢查 API 狀態
- `/start` - 顯示幫助信息

## 環境變數配置

### 必須設置
- `TELEGRAM_BOT_TOKEN` - Telegram Bot Token (從 @BotFather 獲取)

### 可選設置
- `STOCK_API_URL` - Stock API 地址
  - 預設: `https://stockagentapi-production.up.railway.app/suggest`
  - 本地測試: `http://localhost:8001/suggest`

## 本地運行

```bash
# 安裝依賴
pip install -r requirements.txt

# 設置環境變數（Linux/Mac）
export TELEGRAM_BOT_TOKEN="your_token_here"
export STOCK_API_URL="http://localhost:8001/suggest"  # 可選

# 設置環境變數（Windows PowerShell）
$env:TELEGRAM_BOT_TOKEN = "your_token_here"
$env:STOCK_API_URL = "http://localhost:8001/suggest"

# 運行 bot
python telegram_bot.py
```

## Railway 部署

### 1. 連接 GitHub Repository
- Railway 連接到 stock_agent_api 倉庫

### 2. 環境變數設置 (Railway Dashboard)
```
TELEGRAM_BOT_TOKEN=your_token_here
STOCK_API_URL=https://stockagentapi-production.up.railway.app/suggest
```

### 3. 啟動命令
```
python telegram_bot.py
```

### 4. Railway 配置建議

在 railway.json 中添加（如果需要）：
```json
{
  "build": {
    "builder": "dockerfile"
  },
  "deploy": {
    "startCommand": "python telegram_bot.py"
  }
}
```

或直接在 Railway Dashboard 中：
- **Start Command**: `python telegram_bot.py`
- **Working Directory**: (預設/root)

## API 調用格式

Bot 發送到 `/suggest` 的請求：

```json
{
  "mode": "paper",
  "execute": true
}
```

API 回傳示例：

```json
{
  "mode": "paper",
  "cash": 30000.0,
  "executed": true,
  "balance_after": 25000.0,
  "portfolio_value": 30000.0,
  "holdings": {...},
  "suggestions": {...},
  "current_prices": {...},
  "telegram_text": "==== AI Stock Suggestion ... ===="
}
```

## 消息分段

- Telegram 消息限制：4096 字符
- Bot 自動分段發送超長消息
- 每段之間有 0.5 秒延遲

## 超時設置

- API 調用超時：120 秒
- 健康檢查超時：10 秒

## 日誌

Bot 會輸出詳細日誌：

```
2026-05-01 10:00:00,000 - telegram.ext.Application - INFO - Bot is polling for updates...
2026-05-01 10:00:05,123 - telegram_bot - INFO - User 12345 called /run
2026-05-01 10:00:06,456 - telegram_bot - INFO - Calling https://stockagentapi-production.up.railway.app/suggest
```

## 故障排除

### 環境變數未設置
```
ValueError: TELEGRAM_BOT_TOKEN environment variable is required
```
解決：設置 TELEGRAM_BOT_TOKEN 環境變數

### API 連接失敗
```
❌ Connection error: Cannot reach stock API
```
檢查：
1. STOCK_API_URL 是否正確
2. Stock API 服務是否運行

### Bot 沒有回應
- 檢查 TELEGRAM_BOT_TOKEN 是否有效
- 檢查 Railway/本地日誌

## 依賴套件

- python-telegram-bot (v21.0+)
- requests
- 其他見 requirements.txt

## 技術詳情

- 使用 AsyncIO 架構
- 支援 Telegram Bot API 最新版本
- 自動重連機制
- 詳細的錯誤日誌
