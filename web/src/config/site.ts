/**
 * 站点全局可配置变量
 * 修改此处即可自定义站点信息、模型列表等
 */

export const siteConfig = {
  /** 网站标题 */
  site_title: import.meta.env.VITE_SITE_TITLE || 'Mahongwei Studio',

  /** 运营组织名称 */
  organization_name: import.meta.env.VITE_ORG_NAME || 'Mahongwei Studio',

  /** ICP 备案编号 */
  icp_number: import.meta.env.VITE_ICP_NUMBER || '京ICP备XXXXXXXX号-X',

  /** 联系邮箱 */
  contact_email: import.meta.env.VITE_CONTACT_EMAIL || 'contact@mahongwei.com.cn',

  /** 可选大模型列表（AI 前沿探索模块使用） */
  model_options: [
    { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI' },
    { id: 'gpt-4o-mini', name: 'GPT-4o Mini', provider: 'OpenAI' },
    { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', provider: 'Anthropic' },
    { id: 'qwen-plus', name: '通义千问 Plus', provider: 'Alibaba' },
    { id: 'deepseek-chat', name: 'DeepSeek Chat', provider: 'DeepSeek' },
  ],

  /** AI 后端 API 基础地址（Docker 环境用相对路径，本地开发可设置环境变量） */
  aiServerUrl: import.meta.env.VITE_AI_SERVER_URL || '',

  /** 游戏后端地址（猜词游戏 Socket.IO） */
  serverUrl: import.meta.env.VITE_SERVER_URL || '/',
};

export type SiteConfig = typeof siteConfig;
export type ModelOption = (typeof siteConfig.model_options)[number];
