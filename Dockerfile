FROM python:3.11

RUN apt-get update && apt-get install -y \
    python3-pyqt5 \
    python3-pyqt5.qtwebkit \
    python3-pyqt5.qtsvg \
    python3-pip \
    git \
    x11-apps \
    libgl1 \
    libxcb-cursor0 \
    && rm -rf /var/lib/apt/lists/*

# Додаткові бібліотеки (опційно, для попередження з requests)
RUN pip install --upgrade urllib3 chardet requests

# Встановлюємо eric7 і додаємо ~/.local/bin до PATH
ENV PATH=/root/.local/bin:$PATH

RUN pip install --upgrade pip \
    && pip install --prefer-binary eric-ide \
    && eric7_post_install

WORKDIR /workspace

# ✅ ВАЖЛИВО: без \" — просто як масив
CMD ["python3", "-m", "eric7_ide"]