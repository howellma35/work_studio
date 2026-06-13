// 小程序入口
App({
  globalData: {
    serverUrl: '', // 部署后填入后端地址，如 https://yourdomain.com
    userInfo: null,
  },
  onLaunch() {
    console.log('[App] 猜词大挑战启动');
  },
});
