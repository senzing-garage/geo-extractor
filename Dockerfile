# -----------------------------------------------------------------------------
# Stages
# -----------------------------------------------------------------------------

ARG IMAGE_FINAL=debian:11.9-slim

# -----------------------------------------------------------------------------
# Stage: builder
# -----------------------------------------------------------------------------

FROM ${IMAGE_FINAL} AS builder
ENV REFRESHED_AT=2024-07-01
LABEL Name="senzing/python-builder" \
      Maintainer="support@senzing.com" \
      Version="0.1.0"

# Run as "root" for system installation.

USER root

# Install packages via apt-get.

RUN apt-get update \
 && apt-get -y install \
      python3 \
      python3-dev \
      python3-pip \
      python3-venv \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment.

RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install packages via PIP.

COPY requirements.txt ./
RUN python3 -m pip install --upgrade pip \
 && python3 -m pip install -r requirements.txt \
 && python3 -m pip install build \
 && rm requirements.txt

# Build Python wheel file.

COPY . /git-repository
WORKDIR /git-repository
RUN cp geo-extractor.py src/geo_extractor/main_entry.py \
 && python3 -m build \
 && python3 -m pip install dist/*.whl

# -----------------------------------------------------------------------------
# Stage: final
# -----------------------------------------------------------------------------

FROM ${IMAGE_FINAL} AS final
ENV REFRESHED_AT=2024-07-01
LABEL Name="senzing/geo-extractor" \
      Maintainer="support@senzing.com" \
      Version="1.2.6"
HEALTHCHECK CMD ["/app/healthcheck.sh"]
USER root

# Install packages via apt-get.

RUN apt-get update \
 && apt-get -y install \
      python3 \
      python3-pip \
      python3-venv \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Copy files from repository.

COPY ./rootfs /

# Copy files from prior stage.

COPY --from=builder /app/venv /app/venv

# Run as non-root container

USER 1001

# Runtime environment variables.

ENV VIRTUAL_ENV=/app/venv
ENV PATH="/app/venv/bin:${PATH}"
ENV LD_LIBRARY_PATH=/opt/senzing/g2/lib/

# Runtime execution.

ENTRYPOINT ["geo_extractor"]
