FROM rust:1-alpine AS builder
ARG RUSTFLAGS="-C strip=symbols"

RUN apk add musl-dev tzdata

WORKDIR /app
COPY . .
RUN cargo build --release

FROM scratch AS runtime
ENV RUST_LOG=info

# Copy timezone database for local calendar alerts
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo

# TLS certs for HTTPS (copy from builder)
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy the statically linked binary
WORKDIR /app
COPY --from=builder /app/target/release/iopac ./

# Define healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "./iopac", "-H" ]

# Run as non-root
USER 10001:10001
ENTRYPOINT [ "./iopac" ]
