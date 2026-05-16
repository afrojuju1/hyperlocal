FROM oven/bun:1.3.4-alpine

WORKDIR /app

COPY apps/web/package.json apps/web/bun.lock /app/
RUN bun install --frozen-lockfile

COPY apps/web /app
RUN bun run build

EXPOSE 3000

CMD ["bun", "run", "start", "--", "-p", "3000"]
