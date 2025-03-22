# Eric7 IDE in Docker

This project sets up the Eric7 Python IDE inside a Docker container with GUI support.

## 🚀 Usage

### Build the container
```bash
make build
```

### Rebuild without cache
```bash
make rebuild
```

### Run Eric7
```bash
make run
```

### Stop the container
```bash
make stop
```

### Remove container + image
```bash
make clean
```

## 🧱 Requirements

- Linux with X11 or Windows with X-server (like VcXsrv)
- Docker & Docker Compose
