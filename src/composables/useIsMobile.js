import { ref } from 'vue'

// 断点策略：≤ 820px 视为手机（含竖屏平板），> 820px 视为桌面。
// 用 matchMedia 而不是 UA：旋转屏幕、缩小窗口、iPad 分屏都能实时切换。
const mql = window.matchMedia('(max-width: 820px)')
const isMobile = ref(mql.matches)

mql.addEventListener('change', (e) => {
  isMobile.value = e.matches
})

export function useIsMobile() {
  return isMobile
}
