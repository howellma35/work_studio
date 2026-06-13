/**
 * 游戏页 - 猜词输入 + 排行榜
 */
const app = getApp();

Page({
  data: {
    status: 'idle',        // idle / active / finished
    hint: '',
    roundId: null,
    remainingSeconds: 0,
    guessText: '',
    guessResult: null,     // { similarity, isCorrect, rank, message }
    leaderboard: [],
    totalParticipants: 0,
    lastAnswer: '',
    submitting: false,
  },

  socket: null,
  countdownTimer: null,

  onLoad() {
    this.connectSocket();
  },

  onUnload() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }
  },

  // 连接 WebSocket
  connectSocket() {
    const serverUrl = app.globalData.serverUrl;
    if (!serverUrl) {
      tt.showToast({ title: '服务地址未配置', icon: 'none' });
      return;
    }

    const wsUrl = serverUrl.replace('https://', 'wss://').replace('http://', 'ws://');
    const userInfo = app.globalData.userInfo || tt.getStorageSync('userInfo') || {};

    this.socket = tt.connectSocket({
      url: `${wsUrl}/socket.io/?EIO=4&transport=websocket`,
      success: () => {},
    });

    const socket = this.socket;

    socket.onOpen(() => {
      console.log('[WS] 连接成功');
      // Socket.IO 握手后注册
      setTimeout(() => {
        this.sendSocketMessage('42' + JSON.stringify(['register', {
          userId: userInfo.openId || 'guest_' + Date.now(),
          username: userInfo.nickName || '匿名观众',
          avatar: userInfo.avatarUrl || '',
          role: 'viewer',
        }]));
      }, 500);
    });

    socket.onMessage((res) => {
      this.handleSocketMessage(res.data);
    });

    socket.onClose(() => {
      console.log('[WS] 连接关闭');
    });

    socket.onError((err) => {
      console.error('[WS] 连接错误:', err);
    });
  },

  // 发送 Socket.IO 格式消息
  sendSocketMessage(data) {
    if (this.socket) {
      this.socket.send({ data });
    }
  },

  // 处理 Socket.IO 消息
  handleSocketMessage(raw) {
    if (typeof raw !== 'string') return;

    // Socket.IO 协议: 42["event", data]
    if (!raw.startsWith('42')) return;
    try {
      const parsed = JSON.parse(raw.substring(2));
      if (parsed[0] !== 'message') return;
      const msg = parsed[1];

      switch (msg.type) {
        case 'new_round':
          this.onNewRound(msg.data);
          break;
        case 'leaderboard':
          this.setData({
            leaderboard: msg.data.entries,
            totalParticipants: msg.data.totalParticipants,
          });
          break;
        case 'guess_result':
          this.setData({
            guessResult: msg.data,
            submitting: false,
          });
          break;
        case 'round_end':
          this.onRoundEnd(msg.data);
          break;
      }
    } catch (e) {
      // ignore parse errors for ping/pong frames
    }
  },

  // 新一轮开始
  onNewRound(data) {
    this.setData({
      status: 'active',
      roundId: data.roundId,
      hint: data.hint,
      remainingSeconds: data.duration,
      guessText: '',
      guessResult: null,
      leaderboard: [],
    });

    // 倒计时
    if (this.countdownTimer) clearInterval(this.countdownTimer);
    this.countdownTimer = setInterval(() => {
      const remaining = this.data.remainingSeconds;
      if (remaining <= 1) {
        clearInterval(this.countdownTimer);
        return;
      }
      this.setData({ remainingSeconds: remaining - 1 });
    }, 1000);
  },

  // 轮次结束
  onRoundEnd(data) {
    if (this.countdownTimer) clearInterval(this.countdownTimer);
    this.setData({
      status: 'finished',
      lastAnswer: data.answer,
      leaderboard: data.leaderboard || [],
      totalParticipants: data.totalParticipants || 0,
      remainingSeconds: 0,
    });
  },

  // 输入变化
  onInputChange(e) {
    this.setData({ guessText: e.detail.value });
  },

  // 提交猜测
  submitGuess() {
    const text = this.data.guessText.trim();
    if (!text) {
      tt.showToast({ title: '请输入你的猜测', icon: 'none' });
      return;
    }
    if (!this.data.roundId || this.data.status !== 'active') {
      tt.showToast({ title: '当前没有进行中的游戏', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });
    this.sendSocketMessage('42' + JSON.stringify(['message', {
      type: 'guess',
      data: {
        roundId: this.data.roundId,
        text: text,
      },
    }]));
  },

  // 格式化时间
  formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  },
});
