/**
 * CDP 审计：精确视口下测量布局 + 端到端跑一遍主要交互。
 * 用法：先启动浏览器
 *   msedge --headless --remote-debugging-port=9222 --user-data-dir=<tmp> about:blank
 * 再执行
 *   node scripts/audit.mjs http://127.0.0.1:5180
 */
import { writeFile } from 'node:fs/promises'

const BASE = process.argv[2] || 'http://127.0.0.1:5180'
const CDP = process.env.CDP || 'http://127.0.0.1:9222'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function getPageTarget() {
  for (let i = 0; i < 40; i++) {
    try {
      const list = await (await fetch(`${CDP}/json/list`)).json()
      const page = list.find((t) => t.type === 'page')
      if (page) return page
    } catch {
      /* 浏览器还没起来 */
    }
    await sleep(300)
  }
  throw new Error('找不到调试目标')
}

function connect(url) {
  const ws = new WebSocket(url)
  let id = 0
  const pending = new Map()

  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data)
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id)
      pending.delete(msg.id)
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result)
    }
  })

  const ready = new Promise((res, rej) => {
    ws.addEventListener('open', res)
    ws.addEventListener('error', rej)
  })

  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const mid = ++id
      pending.set(mid, { resolve, reject })
      ws.send(JSON.stringify({ id: mid, method, params }))
    })

  return { ready, send, close: () => ws.close() }
}

async function main() {
  const target = await getPageTarget()
  const { ready, send, close } = connect(target.webSocketDebuggerUrl)
  await ready
  await send('Page.enable')
  await send('Runtime.enable')

  const viewport = (width, height, mobile) =>
    send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile })

  const goto = async (path) => {
    await send('Page.navigate', { url: BASE + path })
    await sleep(1600)
  }

  const evaluate = async (expression) => {
    const { result, exceptionDetails } = await send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true,
    })
    if (exceptionDetails) throw new Error(exceptionDetails.exception?.description || 'eval error')
    return result.value
  }

  const shot = async (name) => {
    const { data } = await send('Page.captureScreenshot', { format: 'png' })
    await writeFile(`shots/${name}.png`, Buffer.from(data, 'base64'))
  }

  const report = {}

  // ---------- 1. 布局测量 ----------
  await viewport(1440, 960, false)
  await goto('/')
  report.pc = await evaluate(`({
    innerW: innerWidth,
    docW: document.documentElement.scrollWidth,
    pageRight: Math.round(document.querySelector('.page').getBoundingClientRect().right),
    shell: document.querySelector('.el-menu') ? 'pc-shell' : 'mobile-shell',
    mobileOnly: !!document.querySelector('.van-tabbar')
  })`)
  await shot('pc-home')

  await viewport(390, 844, true)
  await goto('/')
  report.mobile = await evaluate(`({
    innerW: innerWidth,
    docW: document.documentElement.scrollWidth,
    drawRight: Math.round(document.querySelector('.draw').getBoundingClientRect().right),
    shell: document.querySelector('.van-tabbar') ? 'mobile-shell' : 'pc-shell',
    pcOnly: !!document.querySelector('.el-menu'),
    tabbarItems: document.querySelectorAll('.van-tabbar-item').length
  })`)
  await shot('m-home')

  // ---------- 2. 摇一摇 ----------
  await evaluate(`document.querySelector('.shake-btn').click(); true`)
  await sleep(1200)
  report.draw = await evaluate(`({
    dish: document.querySelector('.slot-name')?.textContent.trim(),
    hasMeta: !!document.querySelector('.price'),
    actions: [...document.querySelectorAll('.result-actions button')].map(b => b.textContent.trim())
  })`)
  await shot('m-result')

  // ---------- 3. 登录 + 学号核验（现在需要先登录才能核验） ----------
  await goto('/login')
  await evaluate(`document.querySelector('.demo-fill, .link') && [...document.querySelectorAll('button')].find(b => b.textContent.includes('填入演示账号'))?.click(); true`)
  await sleep(300)
  await evaluate(`[...document.querySelectorAll('.panel .van-button')].find(b => b.textContent.trim() === '登录')?.click(); true`)
  await sleep(2200)
  report.login = await evaluate(`({
    loggedIn: !!JSON.parse(localStorage.getItem('what2eat:user') || 'null'),
    verified: JSON.parse(localStorage.getItem('what2eat:user') || '{}').verified || false
  })`)

  await goto('/me')
  await sleep(2500)
  report.verify = await evaluate(`({
    badge: document.querySelector('.v-badge')?.textContent.trim() || null,
    idShown: document.querySelector('.v-id')?.textContent.trim() || null
  })`)
  await shot('m-me-verified')

  // ---------- 4. 打卡 ----------
  await goto('/checkin')
  report.checkinBefore = await evaluate(`document.querySelectorAll('.checkin-card').length`)
  await evaluate(`(() => {
    const t = document.querySelector('textarea.van-field__control')
    const set = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set
    set.call(t, '食堂三楼的麻辣香锅，微辣刚好')
    t.dispatchEvent(new Event('input', { bubbles: true }))
    return true
  })()`)
  await sleep(300)
  await evaluate(`[...document.querySelectorAll('button')].find(b => b.textContent.trim() === '发布打卡').click(); true`)
  await sleep(700)
  report.checkinAfter = await evaluate(`document.querySelectorAll('.checkin-card').length`)
  await shot('m-checkin-post')

  // ---------- 5. 投票 ----------
  await goto('/vote')
  await evaluate(`document.querySelector('.create-toggle').click(); true`)
  await sleep(300)
  await evaluate(`(() => {
    const input = document.querySelector('.create-body .van-field__control')
    const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
    set.call(input, '今晚去吃鸡公煲？')
    input.dispatchEvent(new Event('input', { bubbles: true }))
    return true
  })()`)
  await sleep(200)
  await evaluate(`[...document.querySelectorAll('button')].find(b => b.textContent.trim() === '发布投票').click(); true`)
  await sleep(700)
  report.voteCreated = await evaluate(`document.querySelectorAll('.vote-card').length`)
  await evaluate(`[...document.querySelectorAll('.vote-card button')].find(b => b.textContent.trim() === '去吃').click(); true`)
  await sleep(400)
  await evaluate(`[...document.querySelectorAll('.vote-card button')].find(b => b.textContent.trim() === '模拟同学').click(); true`)
  await sleep(400)
  await evaluate(`[...document.querySelectorAll('.vote-card button')].find(b => b.textContent.trim() === '模拟同学').click(); true`)
  await sleep(600)
  report.voteState = await evaluate(`({
    badge: document.querySelector('.badge')?.textContent.trim(),
    nums: document.querySelector('.vote-nums')?.textContent.replace(/\\s+/g, ' ').trim()
  })`)
  await shot('m-vote-active')

  console.log(JSON.stringify(report, null, 2))
  close()
}

main().catch((e) => {
  console.error('FAILED:', e.message)
  process.exit(1)
})
