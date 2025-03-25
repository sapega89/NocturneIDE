FROM python:3.11

RUN apt-get update && apt-get install -y \
    python3-pyqt5 \
    python3-pyqt5.qtwebkit \
    python3-pyqt5.qtsvg \
    git \
    x11-apps \
    libgl1 \
    libxcb-cursor0 \
    libnss3 \
    libnss3-dev \
    libxcomposite1 \
    libxrandr2 \
    libxcursor1 \
    libasound2 \
    libxdamage1 \
    libxfixes3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libx11-xcb1 \
    mesa-utils \
    libglu1-mesa \
    mesa-va-drivers \
    mesa-vulkan-drivers \
    libgl1-mesa-dri\
    libgl1-mesa-glx \
    libglx-mesa0 \
    libosmesa6\
    && rm -rf /var/lib/apt/lists/*

ENV PATH=/root/.local/bin:$PATH
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV PYTHONPATH="${PYTHONPATH:-}:/workspace"

# ❗ Опціонально встановити із requirements.txt
COPY requirements.txt /tmp/

RUN pip install --upgrade pip \
    && pip install llama-cpp-python\
    && pip install -r /tmp/requirements.txt\
    && eric7_post_install


# ❗ Робоча директорія
WORKDIR /workspace

# ❗ Команда за замовчуванням — запуск Eric7
CMD ["python3", "eric7_ide.py"]
