import { reactive } from 'vue'

// 极简 toast：不依赖任一组件库的函数式调用，PC / 手机表现一致。
const toastList = reactive([])
let seq = 0

export function toast(msg, duration = 2000) {
  const id = ++seq
  toastList.push({ id, msg })
  // 最多同时显示 2 条，避免连续操作时糊满屏幕
  while (toastList.length > 2) toastList.shift()
  setTimeout(() => {
    const i = toastList.findIndex((t) => t.id === id)
    if (i > -1) toastList.splice(i, 1)
  }, duration)
}

export { toastList }
