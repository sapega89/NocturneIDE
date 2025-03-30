# 🚀 Eric7 IDE with Integrated AI Assistant

A convenient setup of Eric7 IDE combined with a built-in AI coding assistant, provided via Docker for easy and quick deployment.

---

## ✨ Features

- Eric7 IDE in Docker with GUI support
- Built-in AI Assistant powered by Falcon (llama-cpp-python)
- Future support for installation via `pip` and standalone setup

---

## Quick Start with Docker

### Build
```bash
make build
```

### Rebuild (no cache)
```bash
make rebuild
```

### ▶️ Launch Eric7 IDE
```bash
make run
```

### ⏹️ Stop Container
```bash
make stop
```

### 🧹 Cleanup (Remove container + image)
```bash
make clean
```

---

## Requirements

- Linux with X11 or Windows with an X-server (VcXsrv recommended)
- Docker & Docker Compose

---
## 📋 Project Management

Track our development progress and upcoming tasks on our [Kanban Project Board](https://github.com/users/sapega89/projects/1/views/1).


## 📌 Future Plans

- [ ] Installation via `pip` with `setup.py`
- [ ] Comprehensive user documentation
- [ ] Plugin support for easier integration with Eric7

---

## 🤝 Contributing

Contributions and ideas are welcome! Feel free to open an issue or submit a PR.

---

## 📜 Code of Conduct

Please review our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 📄 License

This project is licensed under the GNU General Public License v3.0 — see the [LICENSE](LICENSE) file for details.
