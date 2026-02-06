FROM oven/bun:1.3.4-alpine

WORKDIR /app

COPY web/package.json web/bun.lock /app/
RUN bun install --frozen-lockfile

COPY web /app
RUN bun run build

EXPOSE 3000

CMD ["bun", "run", "start", "--", "-p", "3000"]
