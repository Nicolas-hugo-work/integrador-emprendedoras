FROM node:22-alpine

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY app ./app
COPY public ./public
COPY next.config.ts postcss.config.mjs tsconfig.json ./
ARG NEXT_PUBLIC_API_URL=/api
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build \
    && addgroup -g 10001 kawsay \
    && adduser -S -u 10001 -G kawsay kawsay \
    && chown -R kawsay:kawsay /app

USER kawsay
ENV NODE_ENV=production
ENV API_PROXY_URL=http://backend:8000
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:3000/').then((r)=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["npm", "run", "start", "--", "-H", "0.0.0.0"]
