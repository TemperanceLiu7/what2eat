import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles/global.css'
import { usingMock } from './api'
import { warmup } from './api/client'

createApp(App).use(router).mount('#app')

// 真接口模式下顺手把后端叫醒（mock 模式不发请求）
if (!usingMock) warmup()
