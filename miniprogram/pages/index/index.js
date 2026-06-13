/**
 * 首页 - 加入游戏
 */
const app = getApp();

Page({
  data: {
    userInfo: null,
    hasAuth: false,
    connecting: false,
  },

  onLoad() {
    this.checkLogin();
  },

  // 检查登录状态
  checkLogin() {
    const userInfo = tt.getStorageSync('userInfo');
    if (userInfo) {
      this.setData({ userInfo, hasAuth: true });
    }
  },

  // 抖音授权登录
  handleLogin() {
    const that = this;
    tt.getUserProfile({
      desc: '用于显示排行榜头像和昵称',
      success(res) {
        const userInfo = res.userInfo;
        tt.setStorageSync('userInfo', userInfo);
        that.setData({ userInfo, hasAuth: true });
        app.globalData.userInfo = userInfo;
      },
      fail(err) {
        tt.showToast({ title: '需要授权才能参与游戏', icon: 'none' });
        console.error('[Login] 授权失败:', err);
      },
    });
  },

  // 进入游戏
  handleEnterGame() {
    if (!this.data.hasAuth) {
      this.handleLogin();
      return;
    }
    tt.navigateTo({ url: '/pages/game/game' });
  },
});
