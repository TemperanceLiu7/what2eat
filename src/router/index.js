import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'home', component: () => import('@/pages/Home.vue'), meta: { title: '随机推荐' } },
  { path: '/checkin', name: 'checkin', component: () => import('@/pages/Checkin.vue'), meta: { title: '备餐打卡' } },
  { path: '/vote', name: 'vote', component: () => import('@/pages/Vote.vue'), meta: { title: '吃不吃投票' } },
  { path: '/me', name: 'me', component: () => import('@/pages/Me.vue'), meta: { title: '我的' } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  // 部署在根路径，BASE_URL 就是 '/'；用这个变量是为了以后换路径不用改代码
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 今天吃什么` : '今天吃什么 · 校园随机推荐'
})

export default router
