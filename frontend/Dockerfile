# --- build ---------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Vite inlines env vars at BUILD time, so the API URL must be present here,
# not at runtime. Railway passes it through as a build arg.
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# --- serve ---------------------------------------------------------
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# nginx substitutes the template at container start, so the API origin has to
# be present at runtime as well as at build time -- the CSP's connect-src
# needs it. Redeclared here because ARGs do not cross build stages.
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

ENV PORT=8080
EXPOSE 8080
