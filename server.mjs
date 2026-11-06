/**
 * 零依赖静态服务器：托管 dist/，并做 SPA 回退（/checkin 这种深层链接刷新也能打开）。
 * 用法：node server.mjs  /  PORT=8080 node server.mjs
 */
import http from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { extname, join, resolve, sep } from 'node:path'
import { networkInterfaces } from 'node:os'

const ROOT = resolve(process.cwd(), 'dist')
const PORT = Number(process.env.PORT || 5180)

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.map': 'application/json; charset=utf-8',
}

const server = http.createServer(async (req, res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname)
    let file = join(ROOT, pathname)

    // 阻止 ../ 越界访问
    if (!file.startsWith(ROOT + sep) && file !== ROOT) {
      res.writeHead(403).end('403')
      return
    }

    let info = await stat(file).catch(() => null)
    if (info?.isDirectory()) {
      file = join(file, 'index.html')
      info = await stat(file).catch(() => null)
    }
    if (!info) {
      // SPA 回退
      file = join(ROOT, 'index.html')
      info = await stat(file)
    }

    const body = await readFile(file)
    res.writeHead(200, {
      'Content-Type': MIME[extname(file).toLowerCase()] || 'application/octet-stream',
      'Cache-Control': 'no-cache',
    })
    res.end(body)
  } catch {
    res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' }).end('server error')
  }
})

server.listen(PORT, '0.0.0.0', () => {
  const nets = networkInterfaces()
  const lan = Object.values(nets)
    .flat()
    .filter((n) => n && n.family === 'IPv4' && !n.internal)
    .map((n) => n.address)

  console.log(`\n  今天吃什么 · 演示站已启动`)
  console.log(`  电脑访问：http://localhost:${PORT}`)
  for (const ip of lan) console.log(`  手机访问：http://${ip}:${PORT}   （需与电脑同一 Wi-Fi）`)
  console.log(`\n  按 Ctrl+C 停止\n`)
})
