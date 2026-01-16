# 1min-Gateway 🚀
### *By BillelAttafi*

**Relay 1min.ai API to OpenAI-compatible structure in seconds.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Compatible-blue?logo=docker)](https://www.docker.com/)

Don't forget to **star** ⭐ this repository if you like it!

Details about **1min-Gateway** and its hosted version can be found here: [kokodev.cc/1minrelay](https://www.kokodev.cc/1minrelay)

---

## ✨ Features

* **bolt.diy Support**: Fully compatible for seamless AI-assisted development.
* **OpenAI Standard**: Works with most clients supporting OpenAI Custom Endpoints (`TypingMind`, `ChatBox`, etc.).
* **Smart Model Control**: Expose the full 1min.ai catalog or a predefined subset.
* **Multimodal Support**:
    * **Vision**: Upload and analyze images.
    * **Documents**: Support for `.pdf`, `.docx`, `.txt`, `.yaml`, and more.
    * **Generation**: Create images using Flux, SDXL, and other 1min.ai models.
* **Advanced Performance**:
    * **Streaming**: Real-time interactions for a faster feel.
    * **Rate Limiting**: Integrated Memcached support to manage traffic.
    * **Precision Tokenization**: Accurate token counting using Tiktoken and Mistral-Tokenizer.
* **Cross-Platform**: Optimized for both **ARM64** and **AMD64** architectures.

---

## 🚀 Quick Usage

To use this gateway in your favorite AI client (TypingMind, etc.):

- **Base URL**: `http://YOUR_SERVER_IP:5001/v1`
- **API Key**: Use your **1min.ai API Key**.

---

## 🛠 Installation

### 🐳 Using Docker Compose (Recommended)

```bash
git clone [https://github.com/billelattafi/1min-gateway.git](https://github.com/billelattafi/1min-gateway.git)
cd 1min-gateway
# Edit your .env file
docker compose up -d

```

### 📦 Using Pre-Built Docker Images

```bash
docker run -d --name 1min-gateway-container \
  -p 5001:5001 \
  -e PERMIT_MODELS_FROM_SUBSET_ONLY=False \
  -v $(pwd)/logs:/app/logs \
  billelattafi/1min-gateway:latest

```

---

## ⚙️ Environment Variables

| Variable | Description | Default |
| --- | --- | --- |
| `SUBSET_OF_ONE_MIN_PERMITTED_MODELS` | Comma-separated list of allowed models. | `mistral-nemo,gpt-4o,deepseek-chat` |
| `PERMIT_MODELS_FROM_SUBSET_ONLY` | Set to `True` to restrict usage, `False` for full access. | `False` |

---

## 💎 Paid Perks (Hosted Version)

Support the project by [donating here](https://donate.stripe.com/00w4gB1NbdI60afcKPgMw00) or purchasing the [Hosted Version](https://shop.kokodev.cc/products).

* **Turnkey Hosting**: No server setup required.
* **Beta Access**: Get the latest features before anyone else.
* **Priority Support**: Direct assistance on our Discord.

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.

**Copyright (c) 2026 Billel Attafi**

---

**Need help?** Join our Discord community: [discord.gg/GQd3DrxXyj](https://discord.gg/GQd3DrxXyj)

```